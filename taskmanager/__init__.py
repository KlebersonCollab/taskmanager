"""
TaskManager: Modern background task execution engine with dynamic cron scheduling
and real-time management dashboard.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import fakeredis.aioredis
import redis.asyncio as redis

import taskmanager.core.builtin_tasks as builtin_tasks  # Auto-registers system tasks
from taskmanager.api.app import create_app
from taskmanager.config import settings
from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job
from taskmanager.core.task import Task, TaskRegistry, registry, task
from taskmanager.scheduler.scheduler import Scheduler
from taskmanager.worker.worker import Worker

__version__ = "0.1.0"


class TaskManager:
    """
    High-level manager for embedding TaskManager into existing Python applications
    (FastAPI, Starlette, Django, Flask, or standalone scripts).

    Example:
        ```python
        from taskmanager import TaskManager, task

        tm = TaskManager(redis_url="redis://localhost:6379/0", prefix="myapp")

        @task(name="send_welcome_email")
        async def send_welcome_email(email: str):
            ...

        # Mount into FastAPI
        app.mount("/tasks", tm.get_app())
        ```
    """

    def __init__(
        self,
        redis_url: str | None = None,
        prefix: str | None = None,
        task_registry: TaskRegistry | None = None,
        broker: RedisBroker | None = None,
    ) -> None:
        self.redis_url = redis_url or settings.redis_url
        self.prefix = prefix or settings.redis_prefix
        self.registry = task_registry or registry
        self._broker = broker
        self._scheduler: Scheduler | None = None
        self._app: Any = None

    @property
    def broker(self) -> RedisBroker:
        if self._broker is None:
            if self.redis_url and self.redis_url.startswith("memory://"):
                client = fakeredis.aioredis.FakeRedis(decode_responses=True)
            else:
                client = redis.from_url(self.redis_url, decode_responses=True)
            self._broker = RedisBroker(client, prefix=self.prefix)
            self.registry.set_broker(self._broker)
        return self._broker

    @property
    def scheduler(self) -> Scheduler:
        if self._scheduler is None:
            self._scheduler = Scheduler(self.broker)
        return self._scheduler

    def task(
        self,
        name: str | None = None,
        queue: str = "default",
        max_retries: int = 3,
        retry_backoff: float = 2.0,
        timeout: float | None = None,
    ) -> Callable[..., Task]:
        """Decorator to register a function as a Task within this manager's registry."""

        def decorator(func: Callable[..., Any]) -> Task:
            t = Task(
                func=func,
                name=name,
                queue=queue,
                max_retries=max_retries,
                retry_backoff=retry_backoff,
                timeout=timeout,
                broker=self.broker,
            )
            self.registry.register(t)
            return t

        return decorator

    def create_worker(
        self,
        queues: list[str] | None = None,
        concurrency: int = 5,
        name: str | None = None,
        max_memory_mb: float | None = None,
        max_cpu_percent: float | None = None,
    ) -> Worker:
        """Creates a Worker instance bound to this broker and registry."""
        return Worker(
            broker=self.broker,
            task_registry=self.registry,
            queues=queues or ["default"],
            concurrency=concurrency,
            name=name,
            max_memory_mb=max_memory_mb,
            max_cpu_percent=max_cpu_percent,
        )

    def get_app(self, root_path: str = "") -> Any:
        """Returns the configured FastAPI application for the dashboard and REST API."""
        if self._app is None or root_path:
            self._app = create_app(
                broker=self.broker,
                task_reg=self.registry,
                root_path=root_path,
            )
        return self._app

    def mount_to(self, parent_app: Any, path: str = "/tasks") -> None:
        """Mounts the TaskManager dashboard and API sub-application onto a parent FastAPI/Starlette app."""
        sub_app = self.get_app(root_path=path)
        parent_app.mount(path, sub_app)


__all__ = [
    "TaskManager",
    "task",
    "create_app",
    "Job",
    "Task",
    "TaskRegistry",
    "registry",
    "Worker",
    "Scheduler",
    "RedisBroker",
    "builtin_tasks",
    "__version__",
]
