from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis

from taskmanager.core.job import Job, JobStatus

logger = logging.getLogger(__name__)


class RedisBroker:
    """Redis-backed broker managing queues, delayed jobs, state persistence, DLQ, and events."""

    def __init__(self, redis_client: redis.Redis, prefix: str = "tm"):
        self.redis = redis_client
        self.prefix = prefix

    # --- Key Helper Functions ---
    def _key_queue(self, queue: str) -> str:
        return f"{self.prefix}:queue:{queue}"

    def _key_delayed(self, queue: str) -> str:
        return f"{self.prefix}:delayed:{queue}"

    def _key_job(self, job_id: str) -> str:
        return f"{self.prefix}:job:{job_id}"

    def _key_active(self, worker_id: str) -> str:
        return f"{self.prefix}:active:{worker_id}"

    def _key_worker(self, worker_id: str) -> str:
        return f"{self.prefix}:worker:{worker_id}"

    def _key_workers(self) -> str:
        return f"{self.prefix}:workers"

    def _key_queues(self) -> str:
        return f"{self.prefix}:queues"

    def _key_dlq(self, queue: str) -> str:
        return f"{self.prefix}:dlq:{queue}"

    def _key_events(self) -> str:
        return f"{self.prefix}:events"

    def _key_schedules(self) -> str:
        return f"{self.prefix}:schedules"

    def _key_lock(self, name: str) -> str:
        return f"{self.prefix}:lock:{name}"

    def _key_control(self) -> str:
        return f"{self.prefix}:control"

    def _key_history(self) -> str:
        return f"{self.prefix}:jobs:history"

    # --- Job Operations ---
    async def save_job(self, job: Job) -> None:
        """Persists or updates full Job state in Redis."""
        key = self._key_job(job.id)
        data = job.model_dump_json()
        await self.redis.set(key, data, ex=86400 * 7)  # 7-day TTL

    async def get_job(self, job_id: str) -> Job | None:
        """Retrieves a Job by ID from Redis."""
        key = self._key_job(job_id)
        data = await self.redis.get(key)
        if not data:
            return None
        return Job.model_validate_json(data)

    async def enqueue(self, job: Job) -> Job:
        """Pushes a job into the specified FIFO queue."""
        job.status = JobStatus.PENDING
        if not job.logs:
            job.logs.append(f"[{time.strftime('%H:%M:%S')}] Job enfileirado na fila '{job.queue}'.")
        await self.save_job(job)
        await self.redis.sadd(self._key_queues(), job.queue)
        await self.redis.rpush(self._key_queue(job.queue), job.id)
        await self.publish_event(
            "job:enqueued", {"job_id": job.id, "queue": job.queue, "task": job.task_name}
        )
        return job

    async def schedule_delayed(self, job: Job, delay_seconds: float) -> Job:
        """Places a job into the delayed sorted set with a target execution timestamp."""
        job.status = JobStatus.DELAYED
        target_timestamp = time.time() + delay_seconds
        await self.save_job(job)
        await self.redis.sadd(self._key_queues(), job.queue)
        await self.redis.zadd(self._key_delayed(job.queue), {job.id: target_timestamp})
        await self.publish_event(
            "job:delayed",
            {
                "job_id": job.id,
                "queue": job.queue,
                "task": job.task_name,
                "scheduled_at": target_timestamp,
            },
        )
        return job

    async def process_delayed_jobs(self, queue: str) -> int:
        """Moves ready jobs from the delayed sorted set to the active FIFO queue."""
        delayed_key = self._key_delayed(queue)
        queue_key = self._key_queue(queue)
        now = time.time()

        # Find jobs where score <= now
        job_ids = await self.redis.zrangebyscore(delayed_key, min=0, max=now)
        count = 0
        for job_id in job_ids:
            # Remove from delayed set
            removed = await self.redis.zrem(delayed_key, job_id)
            if removed:
                job = await self.get_job(job_id)
                if job and job.status == JobStatus.DELAYED:
                    job.status = JobStatus.PENDING
                    await self.save_job(job)
                    await self.redis.rpush(queue_key, job_id)
                    await self.publish_event(
                        "job:enqueued",
                        {"job_id": job.id, "queue": job.queue, "task": job.task_name},
                    )
                    count += 1
        return count

    async def fetch_next_job(
        self, queues: list[str], worker_id: str, timeout: int = 1
    ) -> Job | None:
        """Fetches the next available job across the provided queues."""
        # First, process delayed jobs on these queues
        for q in queues:
            await self.process_delayed_jobs(q)

        # Polling queues with LPOP / BLPOP
        for q in queues:
            queue_key = self._key_queue(q)
            job_id = await self.redis.lpop(queue_key)
            if job_id:
                job = await self.get_job(job_id)
                if job:
                    job.status = JobStatus.ACTIVE
                    job.started_at = time.time()
                    job.worker_id = worker_id
                    job.logs.append(
                        f"[{time.strftime('%H:%M:%S')}] Job atribuído ao worker '{worker_id}'."
                    )
                    await self.save_job(job)
                    # Add to worker's active set
                    await self.redis.sadd(self._key_active(worker_id), job.id)
                    await self.publish_event(
                        "job:active",
                        {
                            "job_id": job.id,
                            "worker_id": worker_id,
                            "queue": job.queue,
                            "task": job.task_name,
                        },
                    )
                    return job
        return None

    async def mark_completed(self, job: Job, result: Any) -> None:
        """Marks a job as completed and stores the execution result."""
        job.status = JobStatus.COMPLETED
        job.completed_at = time.time()
        job.duration = round((job.completed_at - (job.started_at or job.created_at)), 4)
        job.result = result
        job.logs.append(
            f"[{time.strftime('%H:%M:%S')}] Job concluído com sucesso em {job.duration:.3f}s."
        )
        await self.save_job(job)
        if job.worker_id:
            await self.redis.srem(self._key_active(job.worker_id), job.id)

        await self.redis.zadd(self._key_history(), {job.id: job.completed_at})
        await self.redis.zremrangebyrank(self._key_history(), 0, -1001)

        await self.publish_event(
            "job:completed",
            {
                "job_id": job.id,
                "worker_id": job.worker_id,
                "queue": job.queue,
                "duration": job.duration,
            },
        )

    async def mark_failed(self, job: Job, error: str, traceback_str: str) -> None:
        """Handles job failure: retries with exponential backoff or routes to DLQ."""
        if job.worker_id:
            await self.redis.srem(self._key_active(job.worker_id), job.id)

        job.error = error
        job.traceback = traceback_str

        if job.can_retry():
            job.retry_count += 1
            backoff_delay = job.calculate_next_backoff()
            job.status = JobStatus.RETRYING
            job.logs.append(
                f"[{time.strftime('%H:%M:%S')}] Tentativa {job.retry_count}/{job.max_retries} falhou: {error}. Agendando retry em {backoff_delay}s."
            )
            await self.save_job(job)
            await self.publish_event(
                "job:retrying",
                {
                    "job_id": job.id,
                    "retry_count": job.retry_count,
                    "max_retries": job.max_retries,
                    "backoff_delay": backoff_delay,
                },
            )
            await self.schedule_delayed(job, backoff_delay)
        else:
            # Exhausted retries -> Route to Dead Letter Queue (DLQ)
            job.status = JobStatus.FAILED
            job.completed_at = time.time()
            job.duration = round(((job.completed_at) - (job.started_at or job.created_at)), 4)
            job.logs.append(
                f"[{time.strftime('%H:%M:%S')}] Retentativas esgotadas ({job.retry_count}/{job.max_retries}). Movido para Dead Letter Queue (DLQ): {error}"
            )
            await self.save_job(job)
            await self.redis.rpush(self._key_dlq(job.queue), job.id)
            await self.redis.zadd(self._key_history(), {job.id: job.completed_at})
            await self.redis.zremrangebyrank(self._key_history(), 0, -1001)

            await self.publish_event(
                "job:failed", {"job_id": job.id, "queue": job.queue, "error": error, "dlq": True}
            )

    async def cancel_job(self, job_id: str) -> bool:
        """Cancels a pending or delayed job."""
        job = await self.get_job(job_id)
        if not job:
            return False
        if job.status in [JobStatus.PENDING, JobStatus.DELAYED]:
            job.status = JobStatus.CANCELLED
            job.completed_at = time.time()
            await self.save_job(job)
            await self.redis.lrem(self._key_queue(job.queue), 0, job.id)
            await self.redis.zrem(self._key_delayed(job.queue), job.id)
            await self.publish_event("job:cancelled", {"job_id": job.id, "queue": job.queue})
            return True
        return False

    # --- DLQ Operations ---
    async def get_dlq_jobs(self, queue: str | None = None, limit: int = 50) -> list[Job]:
        """Returns jobs in the Dead Letter Queue for a specific queue or all queues."""
        if queue and queue != "all":
            queues = [queue]
        else:
            queues = await self.get_all_queues()

        jobs: list[Job] = []
        for q in queues:
            job_ids = await self.redis.lrange(self._key_dlq(q), 0, limit - 1)
            for jid in job_ids:
                job = await self.get_job(jid)
                if job:
                    jobs.append(job)
                if len(jobs) >= limit:
                    break
            if len(jobs) >= limit:
                break
        return jobs

    async def replay_dlq_job(self, job_id: str) -> Job | None:
        """Re-enqueues a job from the DLQ for re-execution."""
        job = await self.get_job(job_id)
        if not job or job.status != JobStatus.FAILED:
            return None
        # Remove from DLQ list
        await self.redis.lrem(self._key_dlq(job.queue), 0, job.id)
        # Reset retry and error state
        job.retry_count = 0
        job.error = None
        job.traceback = None
        job.started_at = None
        job.completed_at = None
        job.status = JobStatus.PENDING
        await self.enqueue(job)
        await self.publish_event("job:replayed", {"job_id": job.id, "queue": job.queue})
        return job

    async def purge_dlq(self, queue: str = "all") -> int:
        """Removes all jobs from the DLQ of a specific queue or all queues."""
        if queue and queue != "all":
            queues = [queue]
        else:
            queues = await self.get_all_queues()

        total_count = 0
        for q in queues:
            dlq_key = self._key_dlq(q)
            job_ids = await self.redis.lrange(dlq_key, 0, -1)
            total_count += len(job_ids)
            await self.redis.delete(dlq_key)
        return total_count

    # --- Maintenance & Flush Operations ---
    async def flush_queues(self) -> dict[str, int]:
        """Cleans all pending queues, delayed sets, and DLQ lists across all queues."""
        queues = await self.get_all_queues()
        total_deleted = 0
        for q in queues:
            # Delete queue, delayed, and dlq keys
            deleted = await self.redis.delete(
                self._key_queue(q),
                self._key_delayed(q),
                self._key_dlq(q),
            )
            total_deleted += deleted
        await self.publish_event("maintenance:flushed", {"target": "queues"})
        return {"cleared_queues": len(queues), "keys_deleted": total_deleted}

    async def flush_history(self) -> int:
        """Clears job execution history logs and metrics."""
        history_key = self._key_history()
        deleted = await self.redis.delete(history_key)
        await self.publish_event("maintenance:flushed", {"target": "history"})
        return deleted

    async def flush_all(self) -> int:
        """Clears all TaskManager keys in Redis (queues, jobs, history, dlq, schedules)."""
        keys = []
        async for key in self.redis.scan_iter(f"{self.prefix}:*"):
            keys.append(key)
        deleted_count = 0
        if keys:
            deleted_count = await self.redis.delete(*keys)
        await self.publish_event("maintenance:flushed", {"target": "all"})
        return deleted_count

    # --- Telemetry & Metrics ---
    async def create_queue(self, queue: str) -> bool:
        """Explicitly registers a queue in Redis."""
        cleaned = queue.strip()
        if not cleaned:
            return False
        await self.redis.sadd(self._key_queues(), cleaned)
        await self.publish_event("queue:created", {"queue": cleaned})
        return True

    async def delete_queue(self, queue: str) -> bool:
        """Deletes a queue from registered queues and deletes remaining queue data."""
        cleaned = queue.strip()
        if not cleaned or cleaned == "default":
            return False
        res = await self.redis.srem(self._key_queues(), cleaned)
        await self.redis.delete(
            self._key_queue(cleaned),
            self._key_delayed(cleaned),
            self._key_dlq(cleaned),
        )
        if res > 0:
            await self.publish_event("queue:deleted", {"queue": cleaned})
            return True
        return False

    async def get_all_queues(self) -> list[str]:
        """Returns all registered queue names."""
        queues = await self.redis.smembers(self._key_queues())
        if not queues:
            return ["default"]
        return sorted(list(queues))

    async def get_queue_metrics(self, queue: str) -> dict[str, int]:
        """Returns counts for pending, delayed, and DLQ jobs in a queue."""
        pending_count = await self.redis.llen(self._key_queue(queue))
        delayed_count = await self.redis.zcard(self._key_delayed(queue))
        dlq_count = await self.redis.llen(self._key_dlq(queue))
        return {
            "queue": queue,
            "pending": pending_count,
            "delayed": delayed_count,
            "dlq": dlq_count,
        }

    async def get_history(
        self,
        limit: int = 50,
        status: str | None = None,
        task_name: str | None = None,
    ) -> list[Job]:
        """Retrieves recent job executions ordered from newest to oldest."""
        history_key = self._key_history()
        # Get recent job IDs by score descending
        job_ids = await self.redis.zrevrange(history_key, 0, limit * 3)
        jobs: list[Job] = []

        for j_id in job_ids:
            job = await self.get_job(j_id)
            if not job:
                continue
            if status and job.status != status:
                continue
            if task_name and task_name.lower() not in job.task_name.lower():
                continue
            jobs.append(job)
            if len(jobs) >= limit:
                break
        return jobs

    async def get_observability_metrics(self) -> dict[str, Any]:
        """Calculates LGTM-style aggregated performance metrics over recent executions."""
        history_key = self._key_history()
        job_ids = await self.redis.zrevrange(history_key, 0, 200)

        completed_count = 0
        failed_count = 0
        durations: list[float] = []
        now = time.time()
        last_minute_runs = 0

        for j_id in job_ids:
            job = await self.get_job(j_id)
            if not job:
                continue
            if job.status == JobStatus.COMPLETED:
                completed_count += 1
                if job.duration is not None:
                    durations.append(job.duration)
                if job.completed_at and (now - job.completed_at) <= 60:
                    last_minute_runs += 1
            elif job.status == JobStatus.FAILED:
                failed_count += 1
                if job.duration is not None:
                    durations.append(job.duration)

        total = completed_count + failed_count
        success_rate = round((completed_count / total * 100), 1) if total > 0 else 100.0

        if durations:
            sorted_durations = sorted(durations)
            avg_duration_ms = round((sum(durations) / len(durations)) * 1000, 1)
            p95_idx = int(len(sorted_durations) * 0.95)
            p95_duration_ms = round(sorted_durations[min(p95_idx, len(sorted_durations) - 1)] * 1000, 1)
        else:
            avg_duration_ms = 0.0
            p95_duration_ms = 0.0

        return {
            "total_executions": total,
            "completed_count": completed_count,
            "failed_count": failed_count,
            "success_rate_percent": success_rate,
            "avg_duration_ms": avg_duration_ms,
            "p95_duration_ms": p95_duration_ms,
            "throughput_per_minute": last_minute_runs,
        }

    # --- Real-Time Pub/Sub Events ---
    async def publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publishes an event to the Redis event channel."""
        payload = json.dumps(
            {
                "type": event_type,
                "timestamp": time.time(),
                "data": data,
            }
        )
        try:
            await self.redis.publish(self._key_events(), payload)
        except Exception as err:
            logger.debug(f"Failed to publish event {event_type}: {err}")

    async def subscribe_events(self) -> AsyncIterator[dict[str, Any]]:
        """Subscribes to live events channel, yielding parsed events."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._key_events())
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        yield json.loads(message["data"])
                    except Exception:
                        pass
        finally:
            await pubsub.unsubscribe(self._key_events())
            await pubsub.aclose()

    async def publish_control(self, action: str, worker_id: str | None = None) -> None:
        """Publishes a control action (pause, resume, stop) targeted to workers."""
        payload = json.dumps({"action": action, "worker_id": worker_id, "timestamp": time.time()})
        try:
            await self.redis.publish(self._key_control(), payload)
        except Exception as err:
            logger.debug(f"Failed to publish control command {action}: {err}")

    async def subscribe_control(self) -> AsyncIterator[dict[str, Any]]:
        """Subscribes to the worker control channel."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._key_control())
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        yield json.loads(message["data"])
                    except Exception:
                        pass
        finally:
            await pubsub.unsubscribe(self._key_control())
            await pubsub.aclose()

