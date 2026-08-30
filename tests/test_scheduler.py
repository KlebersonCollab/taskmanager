import time

import pytest

from taskmanager.core.broker import RedisBroker
from taskmanager.scheduler.cron import Schedule, ScheduleType, calculate_next_run
from taskmanager.scheduler.scheduler import Scheduler


@pytest.fixture
def broker(fake_redis):
    return RedisBroker(fake_redis, prefix="test_sched_tm")


def test_calculate_next_run():
    # Interval schedule
    sched_interval = Schedule(
        name="Heartbeat Interval",
        task_name="ping",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=10.0,
    )
    now = 1000.0
    next_time = calculate_next_run(sched_interval, from_timestamp=now)
    assert next_time == 1010.0

    # Cron schedule
    sched_cron = Schedule(
        name="Hourly Cron",
        task_name="cleanup",
        schedule_type=ScheduleType.CRON,
        cron_expression="0 * * * *",
    )
    next_cron = calculate_next_run(sched_cron, from_timestamp=now)
    assert next_cron > now


@pytest.mark.asyncio
async def test_scheduler_crud_and_manual_trigger(broker):
    scheduler = Scheduler(broker)

    sched = Schedule(
        name="Test Schedule",
        task_name="send_digest",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=60.0,
    )

    created = await scheduler.add_schedule(sched)
    assert created.id == sched.id
    assert created.next_run is not None

    all_scheds = await scheduler.list_schedules()
    assert len(all_scheds) == 1
    assert all_scheds[0].name == "Test Schedule"

    # Manual Trigger
    job = await scheduler.trigger_now(created.id)
    assert job is not None
    assert job.task_name == "send_digest"

    fetched_job = await broker.get_job(job.id)
    assert fetched_job is not None

    # Toggle & Delete
    toggled = await scheduler.toggle_schedule(created.id, enabled=False)
    assert toggled.enabled is False
    assert toggled.next_run is None

    deleted = await scheduler.delete_schedule(created.id)
    assert deleted is True
    assert len(await scheduler.list_schedules()) == 0


@pytest.mark.asyncio
async def test_scheduler_tick_enqueuing(broker):
    scheduler = Scheduler(broker)

    sched = Schedule(
        name="Fast Tick",
        task_name="fast_job",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=1.0,
        next_run=time.time() - 1.0,  # Ready to run immediately
    )
    await scheduler.add_schedule(sched)

    # Run single tick
    await scheduler._tick()

    # Verify job enqueued
    fetched = await broker.fetch_next_job(["default"], worker_id="w-1")
    assert fetched is not None
    assert fetched.task_name == "fast_job"

    # Verify schedule next_run was updated
    updated_sched = await scheduler.get_schedule(sched.id)
    assert updated_sched.total_runs == 1
    assert updated_sched.next_run > time.time() - 1.0
