from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

import redis.asyncio as redis

from taskmanager.config import settings
from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job


class TaskRegistry:
    """Registry holding all user-defined background task functions."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._default_broker: RedisBroker | None = None

    def register(self, task: Task) -> None:
        self._tasks[task.name] = task

    def get(self, name: str) -> Task | None:
        return self._tasks.get(name)

    def list_tasks(self) -> list[str]:
        return list(self._tasks.keys())

    def get_broker(self) -> RedisBroker:
        if self._default_broker is None:
            client = redis.from_url(settings.redis_url, decode_responses=True)
            self._default_broker = RedisBroker(client, prefix=settings.redis_prefix)
        return self._default_broker

    def set_broker(self, broker: RedisBroker) -> None:
        self._default_broker = broker


registry = TaskRegistry()


class Task:
    """Represents a background task wrapper around a Python callable or coroutine."""

    def __init__(
        self,
        func: Callable[..., Any],
        name: str | None = None,
        queue: str = "default",
        max_retries: int = 3,
        retry_backoff: float = 2.0,
        timeout: float | None = None,
        broker: RedisBroker | None = None,
    ):
        self.func = func
        self.name = name or f"{func.__module__}.{func.__name__}"
        self.queue = queue
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.timeout = timeout
        self._broker = broker
        self.is_async = inspect.iscoroutinefunction(func)

    def get_signature_info(self) -> dict[str, Any]:
        """Extracts parameters, types, defaults, and generates a sample payload."""
        try:
            sig = inspect.signature(self.func)
            params = []
            sample_kwargs: dict[str, Any] = {}
            for param in sig.parameters.values():
                has_default = param.default is not inspect.Parameter.empty
                default_val = param.default if has_default else None
                ann_str = "Any" if param.annotation is inspect.Parameter.empty else str(param.annotation)

                params.append(
                    {
                        "name": param.name,
                        "has_default": has_default,
                        "default": default_val,
                        "annotation": ann_str,
                    }
                )

                # Heuristics for realistic smart sample values
                if has_default and default_val is not None:
                    sample_kwargs[param.name] = default_val
                else:
                    ann_lower = ann_str.lower()
                    p_name = param.name.lower()
                    if "int" in ann_lower or "year" in p_name or "month" in p_name or "count" in p_name:
                        sample_kwargs[param.name] = 2026 if "year" in p_name else (8 if "month" in p_name else 1)
                    elif "float" in ann_lower:
                        sample_kwargs[param.name] = 10.0
                    elif "bool" in ann_lower or "dry_run" in p_name or "force" in p_name:
                        sample_kwargs[param.name] = False
                    elif "list" in ann_lower:
                        sample_kwargs[param.name] = []
                    elif "dict" in ann_lower:
                        sample_kwargs[param.name] = {}
                    elif "email" in p_name:
                        sample_kwargs[param.name] = "cliente@exemplo.com"
                    elif "name" in p_name or "nome" in p_name:
                        sample_kwargs[param.name] = "Carlos Silva"
                    elif "order" in p_name or "id" in p_name:
                        sample_kwargs[param.name] = "PED-12345"
                    elif "command" in p_name:
                        sample_kwargs[param.name] = "python scripts/backup_database.py --compress"
                    elif "path" in p_name:
                        sample_kwargs[param.name] = "scripts/backup_database.py"
                    else:
                        sample_kwargs[param.name] = f"valor_{param.name}"

            doc = inspect.getdoc(self.func) or ""
            return {
                "parameters": params,
                "sample_kwargs": sample_kwargs,
                "docstring": doc,
            }
        except Exception:
            return {
                "parameters": [],
                "sample_kwargs": {},
                "docstring": "",
            }

    @property
    def broker(self) -> RedisBroker:
        return self._broker or registry.get_broker()

    def set_broker(self, broker: RedisBroker) -> None:
        self._broker = broker

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Direct call execution for testing or inline execution."""
        if self.is_async:
            return await self.func(*args, **kwargs)
        return self.func(*args, **kwargs)

    async def delay(self, *args: Any, **kwargs: Any) -> Job:
        """Enqueues the task immediately into the default queue."""
        return await self.apply_async(args=list(args), kwargs=kwargs)

    async def apply_async(
        self,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        queue: str | None = None,
        delay: float | None = None,
        priority: int = 0,
        max_retries: int | None = None,
        retry_backoff: float | None = None,
        timeout: float | None = None,
        idempotency_key: str | None = None,
    ) -> Job:
        """Enqueues the task with custom execution parameters."""
        job = Job(
            task_name=self.name,
            queue=queue or self.queue,
            args=args or [],
            kwargs=kwargs or {},
            priority=priority,
            max_retries=self.max_retries if max_retries is None else max_retries,
            retry_backoff=self.retry_backoff if retry_backoff is None else retry_backoff,
            timeout=self.timeout if timeout is None else timeout,
            idempotency_key=idempotency_key,
        )

        if delay and delay > 0:
            return await self.broker.schedule_delayed(job, delay_seconds=delay)
        return await self.broker.enqueue(job)


def task(
    name: str | None = None,
    queue: str = "default",
    max_retries: int = 3,
    retry_backoff: float = 2.0,
    timeout: float | None = None,
    broker: RedisBroker | None = None,
) -> Callable[[Callable[..., Any]], Task]:
    """Decorator to register a function as a TaskManager background task."""

    def decorator(fn: Callable[..., Any]) -> Task:
        t = Task(
            func=fn,
            name=name or f"{fn.__module__}.{fn.__name__}",
            queue=queue,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            timeout=timeout,
            broker=broker,
        )
        registry.register(t)
        return t

    return decorator
