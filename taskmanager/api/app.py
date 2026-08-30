from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from taskmanager.api.events import WebSocketEventManager
from taskmanager.config import settings
from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job
from taskmanager.core.task import TaskRegistry, registry
from taskmanager.scheduler.cron import Schedule
from taskmanager.scheduler.scheduler import Scheduler
from taskmanager.worker.heartbeat import HeartbeatManager


class CreateScheduleRequest(BaseModel):
    name: str
    task_name: str
    queue: str = "default"
    schedule_type: str = "cron"  # "cron" or "interval"
    cron_expression: str | None = None
    interval_seconds: float | None = None
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class EnqueueTaskRequest(BaseModel):
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    queue: str | None = None
    delay: float | None = None
    priority: int = 0
    max_retries: int | None = None
    timeout: float | None = None


def create_app(
    broker: RedisBroker | None = None,
    task_reg: TaskRegistry | None = None,
) -> FastAPI:
    """Factory creating configured FastAPI application."""
    if broker is None:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        broker = RedisBroker(client, prefix=settings.redis_prefix)
    if task_reg is None:
        task_reg = registry

    scheduler = Scheduler(broker)
    event_manager = WebSocketEventManager(broker)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await event_manager.start_listener()
        yield
        await event_manager.stop_listener()

    app = FastAPI(
        title="TaskManager API",
        description="Background task execution engine & real-time dashboard API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.broker = broker
    app.state.registry = task_reg
    app.state.scheduler = scheduler
    app.state.event_manager = event_manager

    # --- REST Endpoints ---

    @app.get("/api/overview")
    async def get_overview():
        """Returns consolidated metrics for dashboard counters."""
        queues = await broker.get_all_queues()
        queue_summaries = []
        total_pending = 0
        total_delayed = 0
        total_dlq = 0

        for q in queues:
            m = await broker.get_queue_metrics(q)
            queue_summaries.append(m)
            total_pending += m["pending"]
            total_delayed += m["delayed"]
            total_dlq += m["dlq"]

        workers = await HeartbeatManager.get_all_workers(broker)
        active_workers = [w for w in workers if w.status in ["idle", "busy"]]
        total_active_jobs = sum(w.active_jobs_count for w in active_workers)

        schedules = await scheduler.list_schedules()

        return {
            "workers_count": len(active_workers),
            "total_workers": len(workers),
            "active_jobs": total_active_jobs,
            "total_pending": total_pending,
            "total_delayed": total_delayed,
            "total_dlq": total_dlq,
            "schedules_count": len(schedules),
            "queues": queue_summaries,
        }

    @app.get("/api/queues")
    async def get_queues():
        queues = await broker.get_all_queues()
        results = []
        for q in queues:
            m = await broker.get_queue_metrics(q)
            results.append(m)
        return results

    @app.get("/api/workers")
    async def get_workers():
        return await HeartbeatManager.get_all_workers(broker)

    @app.get("/api/tasks")
    async def list_registered_tasks():
        tasks = []
        for name in task_reg.list_tasks():
            t = task_reg.get(name)
            if t:
                tasks.append(
                    {
                        "name": t.name,
                        "queue": t.queue,
                        "max_retries": t.max_retries,
                        "retry_backoff": t.retry_backoff,
                        "timeout": t.timeout,
                        "is_async": t.is_async,
                    }
                )
        return tasks

    @app.post("/api/tasks/{task_name}/enqueue")
    async def enqueue_task(task_name: str, req: EnqueueTaskRequest):
        t = task_reg.get(task_name)
        if not t:
            # Allow dynamic enqueue even if not registered locally
            job = Job(
                task_name=task_name,
                queue=req.queue or "default",
                args=req.args,
                kwargs=req.kwargs,
                priority=req.priority,
                max_retries=req.max_retries or 3,
                timeout=req.timeout,
            )
            if req.delay and req.delay > 0:
                enqueued = await broker.schedule_delayed(job, req.delay)
            else:
                enqueued = await broker.enqueue(job)
            return enqueued

        enqueued = await t.apply_async(
            args=req.args,
            kwargs=req.kwargs,
            queue=req.queue,
            delay=req.delay,
            priority=req.priority,
            max_retries=req.max_retries,
            timeout=req.timeout,
        )
        return enqueued

    @app.get("/api/jobs/{job_id}")
    async def get_job_by_id(job_id: str):
        job = await broker.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @app.post("/api/jobs/{job_id}/cancel")
    async def cancel_job_endpoint(job_id: str):
        success = await broker.cancel_job(job_id)
        if not success:
            raise HTTPException(
                status_code=400, detail="Job cannot be cancelled (not pending/delayed or not found)"
            )
        return {"status": "cancelled", "job_id": job_id}

    # --- Schedule Endpoints ---
    @app.get("/api/schedules")
    async def list_schedules():
        return await scheduler.list_schedules()

    @app.post("/api/schedules")
    async def create_schedule(req: CreateScheduleRequest):
        sched = Schedule(
            name=req.name,
            task_name=req.task_name,
            queue=req.queue,
            schedule_type=req.schedule_type,
            cron_expression=req.cron_expression,
            interval_seconds=req.interval_seconds,
            args=req.args,
            kwargs=req.kwargs,
            enabled=req.enabled,
        )
        created = await scheduler.add_schedule(sched)
        return created

    @app.get("/api/schedules/{schedule_id}")
    async def get_schedule(schedule_id: str):
        sched = await scheduler.get_schedule(schedule_id)
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return sched

    @app.put("/api/schedules/{schedule_id}")
    async def update_schedule(schedule_id: str, req: CreateScheduleRequest):
        existing = await scheduler.get_schedule(schedule_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Schedule not found")

        existing.name = req.name
        existing.task_name = req.task_name
        existing.queue = req.queue
        existing.schedule_type = req.schedule_type
        existing.cron_expression = req.cron_expression
        existing.interval_seconds = req.interval_seconds
        existing.args = req.args
        existing.kwargs = req.kwargs
        existing.enabled = req.enabled

        updated = await scheduler.update_schedule(existing)
        return updated

    @app.delete("/api/schedules/{schedule_id}")
    async def delete_schedule(schedule_id: str):
        deleted = await scheduler.delete_schedule(schedule_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return {"status": "deleted", "schedule_id": schedule_id}

    @app.post("/api/schedules/{schedule_id}/toggle")
    async def toggle_schedule(schedule_id: str, payload: dict[str, bool]):
        enabled = payload.get("enabled", True)
        sched = await scheduler.toggle_schedule(schedule_id, enabled)
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return sched

    @app.post("/api/schedules/{schedule_id}/trigger")
    async def trigger_schedule(schedule_id: str):
        job = await scheduler.trigger_now(schedule_id)
        if not job:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return {"status": "triggered", "job": job}

    # --- DLQ Endpoints ---
    @app.get("/api/dlq/{queue}")
    async def get_dlq(queue: str):
        return await broker.get_dlq_jobs(queue)

    @app.post("/api/dlq/{job_id}/replay")
    async def replay_dlq(job_id: str):
        replayed = await broker.replay_dlq_job(job_id)
        if not replayed:
            raise HTTPException(status_code=404, detail="Job not found in DLQ")
        return {"status": "replayed", "job": replayed}

    @app.post("/api/dlq/{queue}/purge")
    async def purge_dlq(queue: str):
        count = await broker.purge_dlq(queue)
        return {"status": "purged", "count": count}

    # --- WebSocket Real-Time Stream ---
    @app.websocket("/ws/events")
    async def websocket_endpoint(websocket: WebSocket):
        await event_manager.connect(websocket)
        try:
            while True:
                # Keepalive loop
                await websocket.receive_text()
        except WebSocketDisconnect:
            event_manager.disconnect(websocket)
        except Exception:
            event_manager.disconnect(websocket)

    # --- Static UI Mount ---
    ui_dir = Path(__file__).resolve().parent.parent / "ui"
    if ui_dir.exists():
        app.mount("/static", StaticFiles(directory=str(ui_dir)), name="static")

        @app.get("/")
        async def index():
            index_file = ui_dir / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return JSONResponse({"status": "ok", "message": "TaskManager API is running"})

    return app
