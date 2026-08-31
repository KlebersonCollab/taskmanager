from __future__ import annotations

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from taskmanager import TaskManager, create_app
from taskmanager.contrib.fastapi import mount_taskmanager
from taskmanager.core.broker import RedisBroker
from taskmanager.core.task import TaskRegistry


@pytest.mark.asyncio
async def test_taskmanager_initialization_and_properties():
    server = fakeredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    broker = RedisBroker(client, prefix="testlib")
    reg = TaskRegistry()

    tm = TaskManager(broker=broker, task_registry=reg, prefix="testlib")
    assert tm.broker == broker
    assert tm.registry == reg
    assert tm.scheduler is not None

    # Test task decorator
    @tm.task(name="testlib.my_task", queue="test_q")
    async def sample_func(x: int) -> int:
        return x * 2

    assert reg.get("testlib.my_task") is not None

    # Test worker creation
    worker = tm.create_worker(queues=["test_q"], concurrency=2)
    assert worker.queues == ["test_q"]
    assert worker.concurrency == 2


@pytest.mark.asyncio
async def test_taskmanager_fastapi_subapp_mount():
    server = fakeredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    broker = RedisBroker(client, prefix="subapp_test")
    reg = TaskRegistry()

    @reg.task(name="demo.subapp_task", queue="sub_q")
    async def demo_task():
        return {"status": "ok"}

    parent_app = FastAPI(title="Parent Application")
    sub_app = create_app(broker=broker, task_reg=reg, root_path="/taskmanager")
    parent_app.mount("/taskmanager", sub_app)

    async with AsyncClient(
        transport=ASGITransport(app=parent_app), base_url="http://testserver"
    ) as ac:
        # Test subpath API access
        res = await ac.get("/taskmanager/api/overview")
        assert res.status_code == 200
        data = res.json()
        assert "queues" in data
        assert "active_jobs" in data

        # Test UI index at subpath
        res_ui = await ac.get("/taskmanager/")
        assert res_ui.status_code == 200
        assert "TaskManager Dashboard" in res_ui.text


@pytest.mark.asyncio
async def test_mount_taskmanager_helper():
    server = fakeredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    broker = RedisBroker(client, prefix="mount_helper")
    reg = TaskRegistry()

    parent_app = FastAPI(title="Host App")
    mount_taskmanager(parent_app, path="/tasks", broker=broker, task_reg=reg)

    async with AsyncClient(
        transport=ASGITransport(app=parent_app), base_url="http://testserver"
    ) as ac:
        res = await ac.get("/tasks/api/overview")
        assert res.status_code == 200
