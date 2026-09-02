import asyncio

import pytest

from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job, JobStatus
from taskmanager.core.task import TaskRegistry, task
from taskmanager.worker.heartbeat import HeartbeatManager
from taskmanager.worker.worker import Worker


@pytest.fixture
def test_setup(fake_redis):
    broker = RedisBroker(fake_redis, prefix="test_worker_tm")
    reg = TaskRegistry()
    reg.set_broker(broker)
    return broker, reg


@pytest.mark.asyncio
async def test_worker_execute_async_and_sync_task(test_setup):
    broker, reg = test_setup

    @task(name="sync_greet", broker=broker)
    def sync_greet(name: str) -> str:
        return f"Hello, {name}!"

    @task(name="async_multiply", broker=broker)
    async def async_multiply(x: int, y: int) -> int:
        await asyncio.sleep(0.01)
        return x * y

    reg.register(sync_greet)
    reg.register(async_multiply)

    # Enqueue jobs
    job1 = await sync_greet.delay("Alice")
    job2 = await async_multiply.delay(4, 5)

    worker = Worker(queues=["default"], concurrency=2, broker=broker, task_registry=reg)
    worker_task = asyncio.create_task(worker.start())

    # Wait for execution
    await asyncio.sleep(0.1)
    await worker.stop()
    worker_task.cancel()

    res1 = await broker.get_job(job1.id)
    assert res1.status == JobStatus.COMPLETED
    assert res1.result == "Hello, Alice!"

    res2 = await broker.get_job(job2.id)
    assert res2.status == JobStatus.COMPLETED
    assert res2.result == 20


@pytest.mark.asyncio
async def test_worker_timeout_handling(test_setup):
    broker, reg = test_setup

    @task(name="slow_task", timeout=0.05, max_retries=0, broker=broker)
    async def slow_task():
        await asyncio.sleep(0.5)
        return "done"

    reg.register(slow_task)
    job = await slow_task.delay()

    worker = Worker(queues=["default"], concurrency=1, broker=broker, task_registry=reg)
    worker_task = asyncio.create_task(worker.start())

    await asyncio.sleep(0.15)
    await worker.stop()
    worker_task.cancel()

    res = await broker.get_job(job.id)
    assert res.status == JobStatus.FAILED
    assert "timed out" in res.error.lower()


@pytest.mark.asyncio
async def test_worker_heartbeat_and_orphan_reaper(test_setup):
    broker, _ = test_setup

    # Manually simulate an active job on a dead worker
    job = Job(
        task_name="dummy", queue="default", status=JobStatus.ACTIVE, worker_id="worker-dead-1"
    )
    await broker.save_job(job)
    await broker.redis.sadd(broker._key_active("worker-dead-1"), job.id)
    await broker.redis.sadd(broker._key_workers(), "worker-dead-1")

    # Worker info key does not exist (simulating expired TTL)
    reaped = await HeartbeatManager.reap_orphans(broker)
    assert reaped == 1

    reaped_job = await broker.get_job(job.id)
    assert reaped_job.status == JobStatus.PENDING
    assert reaped_job.worker_id is None


@pytest.mark.asyncio
async def test_worker_resource_backpressure(test_setup):
    broker, reg = test_setup

    @task(name="quick_task", broker=broker)
    def quick_task():
        return "ok"

    reg.register(quick_task)
    job = await quick_task.delay()

    # Create worker with max_memory_mb set lower than actual memory to force throttle
    worker = Worker(
        queues=["default"],
        concurrency=1,
        max_memory_mb=0.0001,  # Forces throttling
        broker=broker,
        task_registry=reg,
    )
    worker.info.memory_mb = 50.0  # Exceeds max_memory_mb

    worker_task = asyncio.create_task(worker.start())
    await asyncio.sleep(0.1)

    # Job should not be picked up because worker is throttled
    res = await broker.get_job(job.id)
    assert res.status == JobStatus.PENDING
    assert worker.info.status == "throttled"

    await worker.stop()
    worker_task.cancel()


@pytest.mark.asyncio
async def test_worker_task_context_progress_and_logs(test_setup):
    from taskmanager.core.task import TaskContext

    broker, reg = test_setup

    @task(name="batch_import_task", broker=broker)
    async def batch_import_task(total: int, ctx: TaskContext) -> str:
        await ctx.update_progress(25.0, "Carregando dados...")
        await ctx.append_log("Arquivo aberto com sucesso.")
        await ctx.update_progress(75.0, "Gravando registros...")
        await ctx.append_log("75% dos itens importados.")
        return f"Importados {total} itens"

    reg.register(batch_import_task)
    job = await batch_import_task.delay(100)

    worker = Worker(queues=["default"], concurrency=1, broker=broker, task_registry=reg)
    worker_task = asyncio.create_task(worker.start())

    await asyncio.sleep(0.1)
    await worker.stop()
    worker_task.cancel()

    res = await broker.get_job(job.id)
    assert res.status == JobStatus.COMPLETED
    assert res.result == "Importados 100 itens"
    assert res.progress == 100.0  # Completed jobs reach 100%
    assert any("Arquivo aberto com sucesso." in line for line in res.logs)
    assert any("75% dos itens importados." in line for line in res.logs)

