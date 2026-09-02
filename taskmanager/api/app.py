from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import psutil
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
from taskmanager.worker.worker import Worker


class SpawnWorkerRequest(BaseModel):
    name: str | None = None
    queues: list[str] = Field(default_factory=lambda: ["default"])
    concurrency: int = 5
    max_memory_mb: float | None = None
    max_cpu_percent: float | None = None


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
    root_path: str = "",
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
        sched_task = asyncio.create_task(scheduler.start())
        try:
            yield
        finally:
            await scheduler.stop()
            sched_task.cancel()
            await event_manager.stop_listener()

    app = FastAPI(
        title="TaskManager API",
        description="Background task execution engine & real-time dashboard API",
        version="0.1.0",
        lifespan=lifespan,
        root_path=root_path,
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

    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    spawned_workers: dict[str, tuple[Worker, asyncio.Task[Any]]] = {}

    # --- REST Endpoints ---

    @app.get("/api/overview")
    async def get_overview():
        """Returns consolidated metrics for dashboard counters."""
        for t_name in task_reg.list_tasks():
            t = task_reg.get(t_name)
            if t and t.queue:
                await broker.redis.sadd(broker._key_queues(), t.queue)

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
        active_workers = [w for w in workers if w.status in ["idle", "busy", "paused", "throttled"]]
        total_active_jobs = sum(w.active_jobs_count for w in active_workers)

        schedules = await scheduler.list_schedules()

        # Worker Resource Telemetry (from heartbeats / worker process RSS)
        if active_workers:
            worker_cpu_percent = round(sum(w.cpu_percent for w in active_workers) / len(active_workers), 1)
            worker_memory_mb = round(sum(w.memory_mb for w in active_workers), 2)
            worker_memory_detail = f"{len(active_workers)} worker(s) ativo(s)"
        else:
            try:
                proc = psutil.Process()
                worker_cpu_percent = psutil.cpu_percent(interval=None)
                worker_memory_mb = round(proc.memory_info().rss / (1024 * 1024), 2)
                worker_memory_detail = "Processo local"
            except Exception:
                worker_cpu_percent = 0.0
                worker_memory_mb = 0.0
                worker_memory_detail = "--"

        persistence = await broker.check_persistence_health()

        return {
            "workers_count": len(active_workers),
            "total_workers": len(workers),
            "active_jobs": total_active_jobs,
            "total_pending": total_pending,
            "total_delayed": total_delayed,
            "total_dlq": total_dlq,
            "schedules_count": len(schedules),
            "worker_cpu_percent": worker_cpu_percent,
            "worker_memory_mb": worker_memory_mb,
            "worker_memory_detail": worker_memory_detail,
            "queues": queue_summaries,
            "persistence": persistence,
        }

    @app.get("/api/queues")
    async def get_queues():
        queues = await broker.get_all_queues()
        results = []
        for q in queues:
            m = await broker.get_queue_metrics(q)
            results.append(m)
        return results

    @app.post("/api/queues")
    async def create_queue_endpoint(payload: dict[str, str]):
        name = payload.get("name", "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Nome da fila é obrigatório.")
        created = await broker.create_queue(name)
        if not created:
            raise HTTPException(status_code=400, detail="Nome de fila inválido.")
        metrics = await broker.get_queue_metrics(name)
        return {"status": "created", "queue": name, "metrics": metrics}

    @app.delete("/api/queues/{queue}")
    async def delete_queue_endpoint(queue: str):
        if queue == "default":
            raise HTTPException(status_code=400, detail="A fila 'default' não pode ser excluída.")
        deleted = await broker.delete_queue(queue)
        if not deleted:
            raise HTTPException(status_code=404, detail="Fila não encontrada.")
        return {"status": "deleted", "queue": queue}

    @app.get("/api/workers")
    async def get_workers():
        return await HeartbeatManager.get_all_workers(broker)

    @app.post("/api/workers/spawn")
    async def spawn_worker_endpoint(req: SpawnWorkerRequest):
        """Dynamically creates and starts a new worker directly from the Dashboard/API."""
        worker = Worker(
            name=req.name,
            queues=req.queues,
            concurrency=req.concurrency,
            max_memory_mb=req.max_memory_mb,
            max_cpu_percent=req.max_cpu_percent,
            broker=broker,
            task_registry=task_reg,
        )
        task = asyncio.create_task(worker.start())
        spawned_workers[worker.id] = (worker, task)
        # Publish event so frontend updates instantly
        await broker.publish_event(
            "worker:spawned",
            {
                "id": worker.id,
                "name": worker.name,
                "queues": worker.queues,
                "concurrency": worker.concurrency,
            },
        )
        return {
            "status": "started",
            "id": worker.id,
            "name": worker.name,
            "queues": worker.queues,
            "concurrency": worker.concurrency,
        }

    @app.post("/api/workers/{worker_id}/pause")
    async def pause_worker_endpoint(worker_id: str):
        """Pauses job consumption on a worker."""
        if worker_id in spawned_workers:
            spawned_workers[worker_id][0].pause()
        await broker.publish_control("pause", worker_id=worker_id)
        return {"status": "paused", "worker_id": worker_id}

    @app.post("/api/workers/{worker_id}/resume")
    async def resume_worker_endpoint(worker_id: str):
        """Resumes job consumption on a worker."""
        if worker_id in spawned_workers:
            spawned_workers[worker_id][0].resume()
        await broker.publish_control("resume", worker_id=worker_id)
        return {"status": "resumed", "worker_id": worker_id}

    @app.post("/api/workers/{worker_id}/stop")
    async def stop_worker_endpoint(worker_id: str):
        """Gracefully terminates a worker."""
        if worker_id in spawned_workers:
            w, _ = spawned_workers[worker_id]
            await w.stop()
            del spawned_workers[worker_id]
        await broker.publish_control("stop", worker_id=worker_id)
        return {"status": "stopped", "worker_id": worker_id}

    @app.get("/api/tasks")
    async def list_registered_tasks():
        tasks = []
        for name in task_reg.list_tasks():
            t = task_reg.get(name)
            if t:
                sig_info = t.get_signature_info()
                tasks.append(
                    {
                        "name": t.name,
                        "queue": t.queue,
                        "max_retries": t.max_retries,
                        "retry_backoff": t.retry_backoff,
                        "timeout": t.timeout,
                        "is_async": t.is_async,
                        "parameters": sig_info["parameters"],
                        "sample_kwargs": sig_info["sample_kwargs"],
                        "docstring": sig_info["docstring"],
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

    @app.get("/api/jobs/history")
    async def get_job_history(
        limit: int = 50,
        status: str | None = None,
        task_name: str | None = None,
    ):
        """Returns recent job execution history with optional filtering."""
        return await broker.get_history(limit=limit, status=status, task_name=task_name)

    @app.get("/api/metrics/observability")
    async def get_observability_metrics():
        """Returns LGTM-style aggregated performance metrics (p95 latency, success rate, throughput)."""
        return await broker.get_observability_metrics()

    @app.get("/api/metrics/timeseries")
    async def get_timeseries_metrics_endpoint(window_minutes: int = 30):
        """Returns time-series throughput buckets, latency histogram, percentiles and task breakdown."""
        return await broker.get_timeseries_metrics(window_minutes=window_minutes)

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
        cron_expr = req.cron_expression.strip() if req.cron_expression else None
        if req.schedule_type == "cron" and not cron_expr:
            cron_expr = "0 * * * *"
        interval_sec = req.interval_seconds if req.interval_seconds and req.interval_seconds > 0 else (60.0 if req.schedule_type == "interval" else None)

        sched = Schedule(
            name=req.name,
            task_name=req.task_name,
            queue=req.queue,
            schedule_type=req.schedule_type,
            cron_expression=cron_expr,
            interval_seconds=interval_sec,
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

        cron_expr = req.cron_expression.strip() if req.cron_expression else None
        if req.schedule_type == "cron" and not cron_expr:
            cron_expr = "0 * * * *"
        interval_sec = req.interval_seconds if req.interval_seconds and req.interval_seconds > 0 else (60.0 if req.schedule_type == "interval" else None)

        existing.name = req.name
        existing.task_name = req.task_name
        existing.queue = req.queue
        existing.schedule_type = req.schedule_type
        existing.cron_expression = cron_expr
        existing.interval_seconds = interval_sec
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
    @app.get("/api/dlq")
    @app.get("/api/dlq/{queue}")
    async def get_dlq(queue: str = "all"):
        return await broker.get_dlq_jobs(queue)

    @app.post("/api/dlq/{job_id}/replay")
    async def replay_dlq(job_id: str):
        replayed = await broker.replay_dlq_job(job_id)
        if not replayed:
            raise HTTPException(status_code=404, detail="Job not found in DLQ")
        return {"status": "replayed", "job": replayed}

    @app.post("/api/dlq/purge")
    @app.post("/api/dlq/{queue}/purge")
    async def purge_dlq(queue: str = "all"):
        count = await broker.purge_dlq(queue)
        return {"status": "purged", "count": count, "queue": queue}

    # --- Maintenance & Flush Endpoints ---
    @app.post("/api/maintenance/flush")
    async def flush_maintenance(payload: dict[str, str]):
        target = payload.get("target", "queues")
        if target == "queues":
            res = await broker.flush_queues()
            return {"status": "ok", "target": "queues", "result": res}
        elif target == "history":
            res = await broker.flush_history()
            return {"status": "ok", "target": "history", "deleted_keys": res}
        elif target == "all":
            res = await broker.flush_all()
            return {"status": "ok", "target": "all", "deleted_keys": res}
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid target. Must be 'queues', 'history', or 'all'.",
            )

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
