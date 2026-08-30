from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from typing import Any

from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job
from taskmanager.core.task import TaskRegistry, registry
from taskmanager.worker.heartbeat import HeartbeatManager, WorkerInfo

logger = logging.getLogger(__name__)


class Worker:
    """Asyncio background worker daemon capable of concurrent job execution."""

    def __init__(
        self,
        queues: list[str] | None = None,
        concurrency: int = 5,
        name: str | None = None,
        max_memory_mb: float | None = None,
        max_cpu_percent: float | None = None,
        broker: RedisBroker | None = None,
        task_registry: TaskRegistry | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.name = name or f"worker-{self.id[:8]}"
        self.queues = queues or ["default"]
        self.concurrency = concurrency
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.registry = task_registry or registry
        self.broker = broker or self.registry.get_broker()
        self.semaphore = asyncio.Semaphore(concurrency)

        self.info = WorkerInfo(
            id=self.id,
            name=self.name,
            queues=self.queues,
            concurrency=self.concurrency,
            status="idle",
        )
        self.heartbeat = HeartbeatManager(self.broker, self.info)
        self._running = False
        self._paused = False
        self._active_tasks: set[asyncio.Task[Any]] = set()
        self._control_task: asyncio.Task[Any] | None = None

    def pause(self) -> None:
        """Pauses job consumption."""
        self._paused = True
        self.info.status = "paused"
        logger.info(f"Worker {self.name} paused.")

    def resume(self) -> None:
        """Resumes job consumption."""
        self._paused = False
        self.info.status = "idle" if self.info.active_jobs_count == 0 else "busy"
        logger.info(f"Worker {self.name} resumed.")

    async def _listen_control(self) -> None:
        """Listens for remote control signals (pause, resume, stop) via Redis pub/sub."""
        try:
            async for cmd in self.broker.subscribe_control():
                target_id = cmd.get("worker_id")
                if target_id is None or target_id == self.id or target_id == self.name:
                    action = cmd.get("action")
                    if action == "pause":
                        self.pause()
                    elif action == "resume":
                        self.resume()
                    elif action == "stop":
                        asyncio.create_task(self.stop())
        except asyncio.CancelledError:
            pass
        except Exception as err:
            logger.debug(f"Worker control listener closed: {err}")

    async def start(self) -> None:
        """Starts the worker processing loop, heartbeat manager, and control listener."""
        self._running = True
        self.info.status = "idle"
        await self.heartbeat.start()
        self._control_task = asyncio.create_task(self._listen_control())
        limits_str = ""
        if self.max_memory_mb or self.max_cpu_percent:
            limits_str = f" [limits: memory={self.max_memory_mb or 'unlimited'}MB, cpu={self.max_cpu_percent or 'unlimited'}%]"
        logger.info(
            f"Worker {self.name} [{self.id}] started listening on {self.queues} (concurrency={self.concurrency}){limits_str}"
        )

        try:
            while self._running:
                if self._paused:
                    await asyncio.sleep(0.5)
                    continue

                # 1. Resource Backpressure / Guardrails check
                if self.max_memory_mb and self.info.memory_mb >= self.max_memory_mb:
                    logger.warning(
                        f"⚠️ Worker {self.name} atingiu teto de memória ({self.info.memory_mb:.1f}MB >= {self.max_memory_mb}MB). Backpressure ativo (aguardando liberação de memória)..."
                    )
                    self.info.status = "throttled"
                    await asyncio.sleep(2.0)
                    continue

                if self.max_cpu_percent and self.info.cpu_percent >= self.max_cpu_percent:
                    logger.warning(
                        f"⚠️ Worker {self.name} atingiu teto de CPU ({self.info.cpu_percent:.1f}% >= {self.max_cpu_percent}%). Backpressure ativo..."
                    )
                    self.info.status = "throttled"
                    await asyncio.sleep(1.0)
                    continue

                if self.info.status == "throttled":
                    self.info.status = "idle" if self.info.active_jobs_count == 0 else "busy"

                # 2. Wait for available concurrency slot
                await self.semaphore.acquire()

                # 3. Fetch next job
                job = await self.broker.fetch_next_job(self.queues, worker_id=self.id)
                if job:
                    self.info.active_jobs_count += 1
                    self.info.status = "busy"
                    t = asyncio.create_task(self._process_job(job))
                    self._active_tasks.add(t)
                    t.add_done_callback(self._active_tasks.discard)
                else:
                    # Release slot if no job was found
                    self.semaphore.release()
                    await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def _process_job(self, job: Job) -> None:
        """Executes a single job with timeout handling and error catching."""
        try:
            task_def = self.registry.get(job.task_name)
            if not task_def:
                raise ValueError(
                    f"Task '{job.task_name}' is not registered in Worker task registry."
                )

            # Execute with timeout if specified
            timeout = job.timeout or task_def.timeout
            if timeout and timeout > 0:
                result = await asyncio.wait_for(task_def(*job.args, **job.kwargs), timeout=timeout)
            else:
                result = await task_def(*job.args, **job.kwargs)

            await self.broker.mark_completed(job, result=result)
            self.info.completed_jobs_count += 1
            logger.info(f"Job {job.id} [{job.task_name}] completed successfully.")

        except TimeoutError:
            error_msg = f"Job timed out after {job.timeout or task_def.timeout}s"
            tb_str = traceback.format_exc()
            logger.error(f"Job {job.id} timed out: {error_msg}")
            await self.broker.mark_failed(job, error=error_msg, traceback_str=tb_str)
            self.info.failed_jobs_count += 1

        except Exception as err:
            error_msg = str(err) or type(err).__name__
            tb_str = traceback.format_exc()
            logger.error(f"Job {job.id} failed: {error_msg}")
            await self.broker.mark_failed(job, error=error_msg, traceback_str=tb_str)
            self.info.failed_jobs_count += 1

        finally:
            self.info.active_jobs_count = max(0, self.info.active_jobs_count - 1)
            if self.info.active_jobs_count == 0 and not self._paused:
                self.info.status = "idle"
            self.semaphore.release()

    async def stop(self, drain: bool = True, timeout: float = 10.0) -> None:
        """Stops the worker, optionally draining in-flight jobs."""
        if not self._running and self.info.status == "stopped":
            return

        self._running = False
        self.info.status = "stopped"
        logger.info(f"Worker {self.name} stopping (drain={drain})...")

        if self._control_task and not self._control_task.done():
            self._control_task.cancel()

        if drain and self._active_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*list(self._active_tasks), return_exceptions=True),
                    timeout=timeout,
                )
            except TimeoutError:
                logger.warning(f"Worker {self.name} drain timed out. Forcing shutdown.")

        await self.heartbeat.stop()
        logger.info(f"Worker {self.name} stopped.")

