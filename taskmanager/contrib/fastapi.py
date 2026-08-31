from __future__ import annotations

from fastapi import FastAPI

from taskmanager.api.app import create_app
from taskmanager.core.broker import RedisBroker
from taskmanager.core.task import TaskRegistry, registry


def mount_taskmanager(
    parent_app: FastAPI,
    path: str = "/tasks",
    broker: RedisBroker | None = None,
    task_reg: TaskRegistry | None = None,
    redis_url: str | None = None,
    prefix: str | None = None,
) -> FastAPI:
    """
    Mounts the TaskManager dashboard and REST API onto an existing FastAPI/Starlette application.

    Example:
        app = FastAPI()
        mount_taskmanager(app, path="/tasks")
    """
    sub_app = create_app(
        broker=broker,
        task_reg=task_reg or registry,
        root_path=path,
    )
    parent_app.mount(path, sub_app)
    return sub_app
