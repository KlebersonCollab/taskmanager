from __future__ import annotations

import asyncio
import logging
import os
import time

import psutil
from pydantic import BaseModel, Field

from taskmanager.config import settings
from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import JobStatus

logger = logging.getLogger(__name__)


class WorkerInfo(BaseModel):
    id: str
    name: str
    queues: list[str]
    concurrency: int
    status: str = "idle"  # idle, busy, paused, stopped, dead
    started_at: float = Field(default_factory=time.time)
    last_heartbeat: float = Field(default_factory=time.time)
    active_jobs_count: int = 0
    completed_jobs_count: int = 0
    failed_jobs_count: int = 0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0


class HeartbeatManager:
    """Manages worker vitality heartbeats and orphaned job reaping."""

    def __init__(self, broker: RedisBroker, worker_info: WorkerInfo):
        self.broker = broker
        self.worker_info = worker_info
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Unregister worker on clean shutdown
        await self.unregister_worker()

    async def send_heartbeat(self) -> None:
        """Sends a single heartbeat ping updating Redis state with TTL."""
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            self.worker_info.memory_mb = round(mem_info.rss / (1024 * 1024), 2)
            self.worker_info.cpu_percent = psutil.cpu_percent(interval=None)
        except Exception:
            pass

        self.worker_info.last_heartbeat = time.time()
        key = self.broker._key_worker(self.worker_info.id)
        data = self.worker_info.model_dump_json()

        # Set worker info with TTL
        await self.broker.redis.set(key, data, ex=int(settings.worker_heartbeat_ttl))
        await self.broker.redis.sadd(self.broker._key_workers(), self.worker_info.id)
        await self.broker.publish_event("worker:heartbeat", self.worker_info.model_dump())

    async def unregister_worker(self) -> None:
        """Removes worker from registry upon shutdown."""
        self.worker_info.status = "stopped"
        key = self.broker._key_worker(self.worker_info.id)
        await self.broker.redis.delete(key)
        await self.broker.redis.srem(self.broker._key_workers(), self.worker_info.id)
        await self.broker.publish_event("worker:stopped", {"worker_id": self.worker_info.id})

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                await self.send_heartbeat()
                await asyncio.sleep(settings.worker_heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as err:
                logger.warning(f"Heartbeat failure for worker {self.worker_info.id}: {err}")
                await asyncio.sleep(settings.worker_heartbeat_interval)

    @classmethod
    async def get_all_workers(cls, broker: RedisBroker) -> list[WorkerInfo]:
        """Returns all currently registered workers and detects dead ones."""
        worker_ids = await broker.redis.smembers(broker._key_workers())
        workers: list[WorkerInfo] = []
        now = time.time()

        for wid in worker_ids:
            key = broker._key_worker(wid)
            data = await broker.redis.get(key)
            if data:
                info = WorkerInfo.model_validate_json(data)
                if (now - info.last_heartbeat) > settings.worker_heartbeat_ttl:
                    info.status = "dead"
                workers.append(info)
            else:
                # Expired from TTL -> marked as dead
                workers.append(
                    WorkerInfo(
                        id=wid,
                        name=f"Worker-{wid[:6]}",
                        queues=[],
                        concurrency=0,
                        status="dead",
                        last_heartbeat=0,
                    )
                )
        return workers

    @classmethod
    async def reap_orphans(cls, broker: RedisBroker) -> int:
        """Finds dead workers and recovers their un-acked active jobs back to pending."""
        worker_ids = await broker.redis.smembers(broker._key_workers())
        reaped_count = 0

        for wid in worker_ids:
            key = broker._key_worker(wid)
            data = await broker.redis.get(key)
            if not data:
                # Worker TTL expired -> Reap active jobs
                active_key = broker._key_active(wid)
                orphaned_job_ids = await broker.redis.smembers(active_key)
                for jid in orphaned_job_ids:
                    job = await broker.get_job(jid)
                    if job and job.status == JobStatus.ACTIVE:
                        logger.warning(f"Reaping orphaned job {jid} from dead worker {wid}")
                        job.status = JobStatus.PENDING
                        job.worker_id = None
                        await broker.save_job(job)
                        await broker.redis.rpush(broker._key_queue(job.queue), job.id)
                        await broker.publish_event(
                            "job:reaped", {"job_id": job.id, "worker_id": wid}
                        )
                        reaped_count += 1
                # Clean active set & remove dead worker from set
                await broker.redis.delete(active_key)
                await broker.redis.srem(broker._key_workers(), wid)
        return reaped_count
