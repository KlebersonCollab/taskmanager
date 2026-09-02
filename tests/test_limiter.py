import pytest

from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job, JobStatus
from taskmanager.core.limiter import (
    ConcurrencyLimiter,
    RateLimitSpec,
    TokenBucketLimiter,
    parse_rate_limit,
)
from taskmanager.core.task import TaskRegistry


def test_parse_rate_limit_valid():
    spec_s = parse_rate_limit("10/s")
    assert spec_s == RateLimitSpec(rate=10, period=1.0)

    spec_sec = parse_rate_limit("15/second")
    assert spec_sec == RateLimitSpec(rate=15, period=1.0)

    spec_m = parse_rate_limit("100/m")
    assert spec_m == RateLimitSpec(rate=100, period=60.0)

    spec_min = parse_rate_limit("50/min")
    assert spec_min == RateLimitSpec(rate=50, period=60.0)

    spec_h = parse_rate_limit("1000/h")
    assert spec_h == RateLimitSpec(rate=1000, period=3600.0)

    spec_d = parse_rate_limit("5000/d")
    assert spec_d == RateLimitSpec(rate=5000, period=86400.0)


def test_parse_rate_limit_invalid():
    with pytest.raises(ValueError):
        parse_rate_limit("invalid")

    with pytest.raises(ValueError):
        parse_rate_limit("-5/s")

    with pytest.raises(ValueError):
        parse_rate_limit("10/year")

    with pytest.raises(ValueError):
        parse_rate_limit("0/s")


@pytest.mark.asyncio
async def test_token_bucket_limiter_burst_and_exhaustion(fake_redis):
    limiter = TokenBucketLimiter(fake_redis, prefix="test_tm")
    spec = RateLimitSpec(rate=2, period=1.0)  # 2 per second

    # First 2 requests should succeed immediately
    allowed_1, retry_after_1 = await limiter.acquire("api.send_sms", spec)
    assert allowed_1 is True
    assert retry_after_1 == 0.0

    allowed_2, retry_after_2 = await limiter.acquire("api.send_sms", spec)
    assert allowed_2 is True
    assert retry_after_2 == 0.0

    # 3rd request within same second should fail
    allowed_3, retry_after_3 = await limiter.acquire("api.send_sms", spec)
    assert allowed_3 is False
    assert retry_after_3 > 0.0
    assert retry_after_3 <= 0.6


@pytest.mark.asyncio
async def test_concurrency_limiter_semaphore(fake_redis):
    limiter = ConcurrencyLimiter(fake_redis, prefix="test_tm")
    task_name = "reports.heavy_export"

    # Acquire slot 1
    acq_1 = await limiter.acquire(task_name, max_concurrency=2, job_id="job-1")
    assert acq_1 is True

    # Acquire slot 2
    acq_2 = await limiter.acquire(task_name, max_concurrency=2, job_id="job-2")
    assert acq_2 is True

    # Attempt slot 3 (should fail)
    acq_3 = await limiter.acquire(task_name, max_concurrency=2, job_id="job-3")
    assert acq_3 is False

    # Release slot 1
    await limiter.release(task_name, job_id="job-1")

    # Clean up
    await limiter.release(task_name, job_id="job-2")
    await limiter.release(task_name, job_id="job-3")


@pytest.mark.asyncio
async def test_worker_rate_limiting_and_concurrency_rescheduling(fake_redis):
    from taskmanager.worker.worker import Worker

    broker = RedisBroker(fake_redis, prefix="test_worker_limiter_tm")
    reg = TaskRegistry()

    execution_count = 0

    @reg.task(name="test.rate_limited_task", queue="default", rate_limit="1/s")
    async def rate_limited_task():
        nonlocal execution_count
        execution_count += 1
        return "ok"

    worker = Worker(queues=["default"], broker=broker, task_registry=reg)

    # 1. Enqueue job 1
    job1 = Job(task_name="test.rate_limited_task", queue="default")
    await broker.save_job(job1)

    # 2. Process job 1 (should succeed immediately)
    await worker._process_job(job1)
    assert execution_count == 1
    completed_job1 = await broker.get_job(job1.id)
    assert completed_job1.status == JobStatus.COMPLETED

    # 3. Process job 2 immediately within same second (should be delayed, not executed or failed)
    job2 = Job(task_name="test.rate_limited_task", queue="default")
    await broker.save_job(job2)
    await worker._process_job(job2)
    assert execution_count == 1  # Not executed
    delayed_job2 = await broker.get_job(job2.id)
    assert delayed_job2.status == JobStatus.DELAYED
    delayed_count = await fake_redis.zcard(broker._key_delayed("default"))
    assert delayed_count == 1

