import asyncio

import pytest

from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job, JobStatus
from taskmanager.core.task import task


@pytest.fixture
def broker(fake_redis):
    return RedisBroker(fake_redis, prefix="test_tm")


@pytest.mark.asyncio
async def test_job_model_creation():
    job = Job(task_name="send_email", args=["alice@example.com"], kwargs={"subject": "Hi"})
    assert job.task_name == "send_email"
    assert job.status == JobStatus.PENDING
    assert job.can_retry() is True
    assert job.calculate_next_backoff() == 2.0


@pytest.mark.asyncio
async def test_broker_enqueue_and_fetch(broker):
    job = Job(task_name="compute_stats", queue="default", args=[10, 20])
    enqueued_job = await broker.enqueue(job)
    assert enqueued_job.id == job.id

    fetched = await broker.fetch_next_job(["default"], worker_id="worker-1")
    assert fetched is not None
    assert fetched.id == job.id
    assert fetched.status == JobStatus.ACTIVE
    assert fetched.worker_id == "worker-1"

    # Complete job
    await broker.mark_completed(fetched, result={"sum": 30})
    completed_job = await broker.get_job(job.id)
    assert completed_job.status == JobStatus.COMPLETED
    assert completed_job.result == {"sum": 30}


@pytest.mark.asyncio
async def test_broker_retry_and_dlq(broker):
    job = Job(task_name="failing_task", queue="default", max_retries=1, retry_backoff=0.01)
    await broker.enqueue(job)

    # First attempt fails -> Retrying
    fetched = await broker.fetch_next_job(["default"], worker_id="worker-1")
    await broker.mark_failed(fetched, error="NetworkError", traceback_str="Traceback...")
    retrying_job = await broker.get_job(job.id)
    assert retrying_job.status == JobStatus.DELAYED
    assert retrying_job.retry_count == 1

    # Wait for delay and process delayed
    await asyncio.sleep(0.05)
    await broker.process_delayed_jobs("default")

    # Second attempt fails -> Exhausted -> DLQ
    fetched2 = await broker.fetch_next_job(["default"], worker_id="worker-1")
    assert fetched2 is not None
    await broker.mark_failed(fetched2, error="NetworkError", traceback_str="Traceback...")

    failed_job = await broker.get_job(job.id)
    assert failed_job.status == JobStatus.FAILED
    dlq_jobs = await broker.get_dlq_jobs("default")
    assert len(dlq_jobs) == 1
    assert dlq_jobs[0].id == job.id

    # Replay DLQ
    replayed = await broker.replay_dlq_job(job.id)
    assert replayed is not None
    assert replayed.status == JobStatus.PENDING
    assert replayed.retry_count == 0
    dlq_remaining = await broker.get_dlq_jobs("default")
    assert len(dlq_remaining) == 0


@pytest.mark.asyncio
async def test_task_decorator_and_delay(broker):
    @task(name="math.add", queue="math_queue", broker=broker)
    def add(a: int, b: int) -> int:
        return a + b

    # Direct call
    res = await add(2, 3)
    assert res == 5

    # Delay enqueuing
    job = await add.delay(10, 20)
    assert job.task_name == "math.add"
    assert job.queue == "math_queue"
    assert job.args == [10, 20]

    fetched = await broker.fetch_next_job(["math_queue"], worker_id="worker-math")
    assert fetched is not None
    assert fetched.id == job.id


@pytest.mark.asyncio
async def test_builtin_system_run_command(broker):
    from taskmanager.core.builtin_tasks import run_command

    result = await run_command("python -c \"print('Hello from script runner!')\"")
    assert result["exit_code"] == 0
    assert result["stdout"] == "Hello from script runner!"
