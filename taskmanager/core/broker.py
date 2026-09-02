from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis

from taskmanager.alerts.channel import AlertChannel
from taskmanager.alerts.dispatcher import AlertDispatcher
from taskmanager.core.job import Job, JobStatus

logger = logging.getLogger(__name__)


class RedisBroker:
    """Redis-backed broker managing queues, delayed jobs, state persistence, DLQ, and events."""

    def __init__(self, redis_client: redis.Redis, prefix: str = "tm"):
        self.redis = redis_client
        self.prefix = prefix
        self.alert_dispatcher = AlertDispatcher()

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

    async def update_job_progress(
        self, job_id: str, progress: float, message: str | None = None
    ) -> bool:
        """Updates real-time execution progress (0-100%) and status message for an active job."""
        job = await self.get_job(job_id)
        if not job:
            return False
        try:
            clamped_progress = max(0.0, min(100.0, float(progress)))
        except (ValueError, TypeError):
            clamped_progress = 0.0

        job.progress = round(clamped_progress, 1)
        if message is not None:
            job.progress_message = message
        await self.save_job(job)

        await self.publish_event(
            "job:progress",
            {
                "job_id": job.id,
                "progress": job.progress,
                "message": job.progress_message,
                "queue": job.queue,
                "task": job.task_name,
                "worker_id": job.worker_id,
            },
        )
        return True

    async def append_job_log(self, job_id: str, line: str) -> bool:
        """Appends a log line to job execution logs and broadcasts live log event."""
        job = await self.get_job(job_id)
        if not job:
            return False
        formatted_line = f"[{time.strftime('%H:%M:%S')}] {line}"
        job.logs.append(formatted_line)
        await self.save_job(job)

        await self.publish_event(
            "job:log",
            {
                "job_id": job.id,
                "line": formatted_line,
                "queue": job.queue,
                "task": job.task_name,
                "worker_id": job.worker_id,
            },
        )
        return True

    async def mark_completed(self, job: Job, result: Any) -> None:
        """Marks a job as completed and stores the execution result."""
        latest = await self.get_job(job.id)
        if latest:
            job.logs = latest.logs
            if latest.progress_message:
                job.progress_message = latest.progress_message

        job.status = JobStatus.COMPLETED
        job.progress = 100.0
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

    async def mark_failed(self, job: Job, error: str, traceback_str: str | None = None) -> None:
        """Handles job failure: retries with exponential backoff or routes to DLQ."""
        latest = await self.get_job(job.id)
        if latest:
            job.logs = latest.logs
            if latest.progress_message:
                job.progress_message = latest.progress_message

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
            await self.dispatch_alert(
                "job:failed",
                {
                    "job_id": job.id,
                    "task_name": job.task_name,
                    "queue": job.queue,
                    "error": error,
                    "retry_count": job.retry_count,
                    "max_retries": job.max_retries,
                    "worker_id": job.worker_id,
                },
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

    async def check_persistence_health(self) -> dict[str, Any]:
        """Inspects Redis server configuration for AOF durability and eviction safety."""
        health: dict[str, Any] = {
            "aof_enabled": False,
            "maxmemory_policy": "unknown",
            "is_durable": False,
            "warnings": [],
        }
        try:
            config = await self.redis.config_get("appendonly", "maxmemory-policy")
            aof = config.get("appendonly", "no").lower() == "yes"
            policy = config.get("maxmemory-policy", "noeviction")
            health["aof_enabled"] = aof
            health["maxmemory_policy"] = policy
            health["is_durable"] = aof and policy == "noeviction"

            if not aof:
                health["warnings"].append(
                    "AOF persistence is disabled. Crons/DLQ might not survive unexpected reboots."
                )
            if policy != "noeviction":
                health["warnings"].append(
                    f"Redis eviction policy is '{policy}'. Use 'noeviction' to prevent silent job deletion."
                )
        except Exception:
            # FakeRedis or managed Redis without CONFIG GET permission
            pass
        return health

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

    async def get_timeseries_metrics(
        self, window_minutes: int = 30, reference_time: float | None = None
    ) -> dict[str, Any]:
        """Calculates multi-series throughput, latency histogram, percentiles and task breakdown."""
        win_min = max(5, min(1440, int(window_minutes)))
        win_sec = win_min * 60
        now = reference_time if reference_time is not None else time.time()
        start_time = now - win_sec

        # Determine bucket size in seconds
        if win_min <= 15:
            bucket_sec = 60
        elif win_min <= 30:
            bucket_sec = 60
        elif win_min <= 60:
            bucket_sec = 120
        elif win_min <= 180:
            bucket_sec = 300
        else:
            bucket_sec = 1800

        num_buckets = max(1, int(win_sec / bucket_sec))
        buckets: list[dict[str, Any]] = []
        for i in range(num_buckets):
            b_start = start_time + (i * bucket_sec)
            try:
                time_label = time.strftime("%H:%M", time.localtime(max(0.0, b_start)))
            except Exception:
                time_label = "--:--"
            buckets.append(
                {
                    "timestamp": b_start,
                    "time_label": time_label,
                    "completed": 0,
                    "failed": 0,
                    "total": 0,
                }
            )

        # Retrieve job IDs in window from history zset
        history_key = self._key_history()
        job_ids = await self.redis.zrangebyscore(history_key, min=start_time, max=now)

        completed_count = 0
        failed_count = 0
        durations_ms: list[float] = []
        task_stats: dict[str, dict[str, Any]] = {}

        # Latency buckets
        histogram_defs = [
            {"label": "< 50ms", "min": 0, "max": 50, "count": 0},
            {"label": "50-200ms", "min": 50, "max": 200, "count": 0},
            {"label": "200-500ms", "min": 200, "max": 500, "count": 0},
            {"label": "500ms-1s", "min": 500, "max": 1000, "count": 0},
            {"label": "1s-5s", "min": 1000, "max": 5000, "count": 0},
            {"label": "> 5s", "min": 5000, "max": float("inf"), "count": 0},
        ]

        for j_id in job_ids:
            job = await self.get_job(j_id)
            if not job or not job.completed_at:
                continue

            # Bucket index
            b_idx = int((job.completed_at - start_time) / bucket_sec)
            if 0 <= b_idx < len(buckets):
                if job.status == JobStatus.COMPLETED:
                    buckets[b_idx]["completed"] += 1
                elif job.status == JobStatus.FAILED:
                    buckets[b_idx]["failed"] += 1
                buckets[b_idx]["total"] += 1

            if job.status == JobStatus.COMPLETED:
                completed_count += 1
            elif job.status == JobStatus.FAILED:
                failed_count += 1

            dur_ms = (job.duration * 1000) if job.duration is not None else 0.0
            if dur_ms >= 0:
                durations_ms.append(dur_ms)
                for h in histogram_defs:
                    if h["min"] <= dur_ms < h["max"]:
                        h["count"] += 1
                        break

            # Group task stats
            t_name = job.task_name or "unknown"
            if t_name not in task_stats:
                task_stats[t_name] = {
                    "task_name": t_name,
                    "total": 0,
                    "completed": 0,
                    "failed": 0,
                    "durations": [],
                }
            task_stats[t_name]["total"] += 1
            if job.status == JobStatus.COMPLETED:
                task_stats[t_name]["completed"] += 1
            elif job.status == JobStatus.FAILED:
                task_stats[t_name]["failed"] += 1
            if job.duration is not None:
                task_stats[t_name]["durations"].append(dur_ms)

        total_runs = completed_count + failed_count
        success_rate = round((completed_count / total_runs * 100), 1) if total_runs > 0 else 100.0

        # Percentiles
        if durations_ms:
            sorted_d = sorted(durations_ms)
            p50 = round(sorted_d[int(len(sorted_d) * 0.50)], 1)
            p75 = round(sorted_d[int(len(sorted_d) * 0.75)], 1)
            p90 = round(sorted_d[min(int(len(sorted_d) * 0.90), len(sorted_d) - 1)], 1)
            p95 = round(sorted_d[min(int(len(sorted_d) * 0.95), len(sorted_d) - 1)], 1)
            p99 = round(sorted_d[min(int(len(sorted_d) * 0.99), len(sorted_d) - 1)], 1)
            avg = round(sum(sorted_d) / len(sorted_d), 1)
        else:
            p50 = p75 = p90 = p95 = p99 = avg = 0.0

        # Format histogram
        total_dur_count = len(durations_ms) or 1
        histogram_result = [
            {
                "bucket": h["label"],
                "count": h["count"],
                "percentage": round((h["count"] / total_dur_count) * 100, 1),
            }
            for h in histogram_defs
        ]

        # Format task breakdown
        breakdown_result = []
        for t in task_stats.values():
            t_total = t["total"]
            t_succ = round((t["completed"] / t_total * 100), 1) if t_total > 0 else 100.0
            t_avg = round(sum(t["durations"]) / len(t["durations"]), 1) if t["durations"] else 0.0
            breakdown_result.append(
                {
                    "task_name": t["task_name"],
                    "total": t_total,
                    "completed": t["completed"],
                    "failed": t["failed"],
                    "success_rate_percent": t_succ,
                    "avg_duration_ms": t_avg,
                }
            )
        breakdown_result.sort(key=lambda x: x["total"], reverse=True)

        return {
            "window_minutes": win_min,
            "total_executions": total_runs,
            "completed_count": completed_count,
            "failed_count": failed_count,
            "success_rate_percent": success_rate,
            "throughput_series": buckets,
            "latency_histogram": histogram_result,
            "latency_percentiles": {
                "p50_ms": p50,
                "p75_ms": p75,
                "p90_ms": p90,
                "p95_ms": p95,
                "p99_ms": p99,
                "avg_ms": avg,
            },
            "task_breakdown": breakdown_result,
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

    # --- Multi-Platform Alert Channels ---
    def _key_alerts(self) -> str:
        return f"{self.prefix}:alerts:channels"

    async def save_alert_channel(self, channel: AlertChannel) -> None:
        """Saves an alert channel configuration in Redis."""
        await self.redis.hset(self._key_alerts(), channel.id, channel.model_dump_json())

    async def get_alert_channel(self, channel_id: str) -> AlertChannel | None:
        """Retrieves an alert channel by ID."""
        raw = await self.redis.hget(self._key_alerts(), channel_id)
        if not raw:
            return None
        return AlertChannel.model_validate_json(raw)

    async def list_alert_channels(self) -> list[AlertChannel]:
        """Lists all configured alert channels."""
        all_raw = await self.redis.hgetall(self._key_alerts())
        return [AlertChannel.model_validate_json(v) for v in all_raw.values()]

    async def delete_alert_channel(self, channel_id: str) -> bool:
        """Deletes an alert channel by ID."""
        deleted = await self.redis.hdel(self._key_alerts(), channel_id)
        return deleted > 0

    async def dispatch_alert(self, event_type: str, event_data: dict[str, Any]) -> None:
        """Dispatches an alert event to all matching enabled channels asynchronously."""
        try:
            channels = await self.list_alert_channels()
            for ch in channels:
                if ch.matches_event(event_type):
                    asyncio.create_task(self.alert_dispatcher.send_alert(ch, event_type, event_data))
        except Exception as err:
            logger.warning(f"Failed to process alert dispatch: {err}")


