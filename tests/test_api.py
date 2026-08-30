import pytest
from httpx import ASGITransport, AsyncClient

from taskmanager.api.app import create_app
from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job, JobStatus
from taskmanager.core.task import TaskRegistry, task


@pytest.fixture
def app_setup(fake_redis):
    broker = RedisBroker(fake_redis, prefix="test_api_tm")
    reg = TaskRegistry()
    reg.set_broker(broker)

    @task(name="api_ping", queue="default", broker=broker)
    def api_ping(msg: str):
        return f"pong: {msg}"

    reg.register(api_ping)
    app = create_app(broker=broker, task_reg=reg)
    return app, broker, reg


@pytest.mark.asyncio
async def test_api_overview_and_queues(app_setup):
    app, _, _ = app_setup
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/overview")
        assert res.status_code == 200
        data = res.json()
        assert "workers_count" in data
        assert "queues" in data
        assert data["total_pending"] == 0
        assert "system_cpu_percent" in data
        assert "system_memory_percent" in data
        assert "system_memory_used_mb" in data

        res_queues = await client.get("/api/queues")
        assert res_queues.status_code == 200
        assert isinstance(res_queues.json(), list)


@pytest.mark.asyncio
async def test_api_enqueue_and_get_job(app_setup):
    app, _, _ = app_setup
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Enqueue via API
        res = await client.post("/api/tasks/api_ping/enqueue", json={"args": ["hello_api"]})
        assert res.status_code == 200
        job_data = res.json()
        job_id = job_data["id"]
        assert job_data["task_name"] == "api_ping"

        # Get Job by ID
        res_job = await client.get(f"/api/jobs/{job_id}")
        assert res_job.status_code == 200
        assert res_job.json()["id"] == job_id


@pytest.mark.asyncio
async def test_api_schedules_crud(app_setup):
    app, _, _ = app_setup
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create schedule
        res = await client.post(
            "/api/schedules",
            json={
                "name": "Daily Cleanup",
                "task_name": "api_ping",
                "queue": "default",
                "schedule_type": "cron",
                "cron_expression": "0 0 * * *",
                "args": ["cleanup"],
            },
        )
        assert res.status_code == 200
        created = res.json()
        sched_id = created["id"]
        assert created["name"] == "Daily Cleanup"

        # List schedules
        res_list = await client.get("/api/schedules")
        assert len(res_list.json()) == 1

        # Trigger now
        res_trig = await client.post(f"/api/schedules/{sched_id}/trigger")
        assert res_trig.status_code == 200
        assert res_trig.json()["status"] == "triggered"

        # Delete schedule
        res_del = await client.delete(f"/api/schedules/{sched_id}")
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_api_dlq_operations(app_setup):
    app, broker, _ = app_setup
    # Manually seed a DLQ job
    job = Job(
        task_name="failed_task", queue="default", status=JobStatus.FAILED, error="CriticalError"
    )
    await broker.save_job(job)
    await broker.redis.rpush(broker._key_dlq("default"), job.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Fetch DLQ
        res = await client.get("/api/dlq/default")
        assert res.status_code == 200
        dlq_list = res.json()
        assert len(dlq_list) == 1
        assert dlq_list[0]["id"] == job.id

        # Replay DLQ
        res_replay = await client.post(f"/api/dlq/{job.id}/replay")
        assert res_replay.status_code == 200
        assert res_replay.json()["status"] == "replayed"

        # Check DLQ is now empty
        res_after = await client.get("/api/dlq/default")
        assert len(res_after.json()) == 0


@pytest.mark.asyncio
async def test_api_index_and_static(app_setup):
    app, _, _ = app_setup
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200
        assert "TaskManager Dashboard" in res.text
