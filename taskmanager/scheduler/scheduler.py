from __future__ import annotations

import asyncio
import logging
import time

from taskmanager.config import settings
from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job
from taskmanager.scheduler.cron import Schedule, calculate_next_run

logger = logging.getLogger(__name__)


class Scheduler:
    """Dynamic Cron and Interval scheduler utilizing Redis for persistence and distributed locking."""

    def __init__(self, broker: RedisBroker):
        self.broker = broker
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._lock_id = f"scheduler-{time.time()}"

    # --- Schedule CRUD Operations ---
    async def add_schedule(self, schedule: Schedule) -> Schedule:
        """Registers a new schedule and computes initial next_run."""
        if schedule.next_run is None:
            schedule.next_run = calculate_next_run(schedule)
        key = self.broker._key_schedules()
        await self.broker.redis.hset(key, schedule.id, schedule.model_dump_json())
        await self.broker.publish_event("schedule:created", schedule.model_dump())
        return schedule

    async def get_schedule(self, schedule_id: str) -> Schedule | None:
        """Fetches a schedule by ID."""
        key = self.broker._key_schedules()
        raw = await self.broker.redis.hget(key, schedule_id)
        if not raw:
            return None
        return Schedule.model_validate_json(raw)

    async def list_schedules(self) -> list[Schedule]:
        """Lists all registered schedules."""
        key = self.broker._key_schedules()
        all_raw = await self.broker.redis.hgetall(key)
        schedules: list[Schedule] = []
        for raw in all_raw.values():
            try:
                schedules.append(Schedule.model_validate_json(raw))
            except Exception:
                pass
        return sorted(schedules, key=lambda s: s.created_at)

    async def update_schedule(self, schedule: Schedule) -> Schedule:
        """Updates an existing schedule."""
        if schedule.enabled:
            schedule.next_run = calculate_next_run(schedule)
        key = self.broker._key_schedules()
        await self.broker.redis.hset(key, schedule.id, schedule.model_dump_json())
        await self.broker.publish_event("schedule:updated", schedule.model_dump())
        return schedule

    async def delete_schedule(self, schedule_id: str) -> bool:
        """Deletes a schedule."""
        key = self.broker._key_schedules()
        res = await self.broker.redis.hdel(key, schedule_id)
        if res > 0:
            await self.broker.publish_event("schedule:deleted", {"schedule_id": schedule_id})
            return True
        return False

    async def toggle_schedule(self, schedule_id: str, enabled: bool) -> Schedule | None:
        """Enables or disables a schedule."""
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            return None
        schedule.enabled = enabled
        if enabled:
            schedule.next_run = calculate_next_run(schedule)
        else:
            schedule.next_run = None
        return await self.update_schedule(schedule)

    async def trigger_now(self, schedule_id: str) -> Job | None:
        """Manually triggers a schedule immediately."""
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            return None

        job = Job(
            task_name=schedule.task_name,
            queue=schedule.queue,
            args=schedule.args,
            kwargs=schedule.kwargs,
        )
        enqueued_job = await self.broker.enqueue(job)

        schedule.last_run = time.time()
        schedule.total_runs += 1
        key = self.broker._key_schedules()
        await self.broker.redis.hset(key, schedule.id, schedule.model_dump_json())
        await self.broker.publish_event(
            "schedule:triggered",
            {
                "schedule_id": schedule.id,
                "job_id": enqueued_job.id,
                "manual": True,
            },
        )
        return enqueued_job

    # --- Scheduler Daemon Loop ---
    async def start(self) -> None:
        """Starts the scheduler polling loop."""
        self._running = True
        logger.info("Scheduler daemon started.")
        try:
            while self._running:
                await self._tick()
                await asyncio.sleep(settings.scheduler_poll_interval)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            logger.info("Scheduler daemon stopped.")

    async def stop(self) -> None:
        self._running = False

    async def _tick(self) -> None:
        """Evaluates schedules and enqueues due jobs using distributed locking."""
        lock_key = self.broker._key_lock("scheduler")
        # Attempt to acquire leader lock with 3-second TTL
        acquired = await self.broker.redis.set(lock_key, self._lock_id, nx=True, ex=3)
        if not acquired:
            # Check if this instance already holds the lock
            current_holder = await self.broker.redis.get(lock_key)
            if current_holder != self._lock_id:
                return  # Another scheduler instance is the active leader
            # Refresh lock
            await self.broker.redis.expire(lock_key, 3)

        now = time.time()
        schedules = await self.list_schedules()

        for schedule in schedules:
            if not schedule.enabled or schedule.next_run is None:
                continue

            if now >= schedule.next_run:
                # Enqueue the job
                job = Job(
                    task_name=schedule.task_name,
                    queue=schedule.queue,
                    args=schedule.args,
                    kwargs=schedule.kwargs,
                )
                await self.broker.enqueue(job)

                # Advance next run
                schedule.last_run = now
                schedule.total_runs += 1
                try:
                    schedule.next_run = calculate_next_run(schedule, from_timestamp=now)
                except Exception as err:
                    logger.error(f"Error calculating next run for schedule {schedule.id}: {err}")
                    schedule.next_run = now + 60

                key = self.broker._key_schedules()
                await self.broker.redis.hset(key, schedule.id, schedule.model_dump_json())
                await self.broker.publish_event(
                    "schedule:triggered",
                    {
                        "schedule_id": schedule.id,
                        "job_id": job.id,
                        "manual": False,
                    },
                )
