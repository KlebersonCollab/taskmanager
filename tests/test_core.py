import asyncio
import time

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


@pytest.mark.asyncio
async def test_job_progress_and_broker_progress_updates(broker):
    job = Job(task_name="long_task", queue="default")
    assert job.progress == 0.0
    assert job.progress_message is None

    await broker.enqueue(job)

    # Update progress
    updated = await broker.update_job_progress(job.id, progress=45.0, message="Processing items...")
    assert updated is True

    fetched = await broker.get_job(job.id)
    assert fetched.progress == 45.0
    assert fetched.progress_message == "Processing items..."

    # Append custom log
    log_updated = await broker.append_job_log(job.id, "Step 1 completed.")
    assert log_updated is True

    fetched2 = await broker.get_job(job.id)
    assert any("Step 1 completed." in line for line in fetched2.logs)


@pytest.mark.asyncio
async def test_broker_get_timeseries_metrics(broker):
    # 1. Test empty state
    empty_m = await broker.get_timeseries_metrics(window_minutes=30)
    assert "throughput_series" in empty_m
    assert "latency_histogram" in empty_m
    assert "latency_percentiles" in empty_m
    assert "task_breakdown" in empty_m
    assert empty_m["latency_percentiles"]["p50_ms"] == 0.0

    # 2. Seed some executions
    base_t = time.time()
    job1 = Job(task_name="emails.send", queue="default", status=JobStatus.COMPLETED)
    job1.started_at = base_t - 20
    job1.completed_at = base_t - 19.95  # 50ms
    job1.duration = 0.05
    await broker.save_job(job1)
    await broker.redis.zadd(broker._key_history(), {job1.id: job1.completed_at})

    job2 = Job(task_name="reports.generate", queue="reports", status=JobStatus.COMPLETED)
    job2.started_at = base_t - 15
    job2.completed_at = base_t - 14.75  # 250ms
    job2.duration = 0.25
    await broker.save_job(job2)
    await broker.redis.zadd(broker._key_history(), {job2.id: job2.completed_at})

    job3 = Job(task_name="emails.send", queue="default", status=JobStatus.FAILED)
    job3.started_at = base_t - 10
    job3.completed_at = base_t - 9.90  # 100ms
    job3.duration = 0.10
    await broker.save_job(job3)
    await broker.redis.zadd(broker._key_history(), {job3.id: job3.completed_at})

    m = await broker.get_timeseries_metrics(window_minutes=30, reference_time=base_t)
    assert len(m["throughput_series"]) > 0
    assert m["total_executions"] == 3
    assert m["completed_count"] == 2
    assert m["failed_count"] == 1
    assert m["latency_percentiles"]["p50_ms"] > 0
    assert len(m["task_breakdown"]) == 2
    email_stat = next(t for t in m["task_breakdown"] if t["task_name"] == "emails.send")
    assert email_stat["total"] == 2
    assert email_stat["completed"] == 1
    assert email_stat["failed"] == 1


