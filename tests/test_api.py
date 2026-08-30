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
        assert "worker_cpu_percent" in data
        assert "worker_memory_mb" in data
        assert "worker_memory_detail" in data

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


@pytest.mark.asyncio
async def test_api_history_and_observability_metrics(app_setup):
    app, broker, _ = app_setup
    job = Job(task_name="api_ping", queue="default")
    await broker.enqueue(job)
    fetched = await broker.fetch_next_job(["default"], worker_id="worker-obs")
    await broker.mark_completed(fetched, result={"status": "pong"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # History
        res_hist = await client.get("/api/jobs/history")
        assert res_hist.status_code == 200
        history_list = res_hist.json()
        assert len(history_list) >= 1
        assert history_list[0]["id"] == job.id
        assert history_list[0]["status"] == "completed"

        # Observability Metrics
        res_metrics = await client.get("/api/metrics/observability")
        assert res_metrics.status_code == 200
        m = res_metrics.json()
        assert m["total_executions"] >= 1
        assert m["success_rate_percent"] == 100.0
        assert "avg_duration_ms" in m
        assert "p95_duration_ms" in m


@pytest.mark.asyncio
async def test_api_worker_spawn_and_control(app_setup):
    app, _, _ = app_setup
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Spawn a dynamic worker
        spawn_payload = {
            "name": "worker-api-test",
            "queues": ["test-queue"],
            "concurrency": 2,
            "max_memory_mb": 512,
        }
        res_spawn = await client.post("/api/workers/spawn", json=spawn_payload)
        assert res_spawn.status_code == 200
        w_data = res_spawn.json()
        assert w_data["status"] == "started"
        worker_id = w_data["id"]

        # 2. Pause worker
        res_pause = await client.post(f"/api/workers/{worker_id}/pause")
        assert res_pause.status_code == 200
        assert res_pause.json()["status"] == "paused"

        # 3. Resume worker
        res_resume = await client.post(f"/api/workers/{worker_id}/resume")
        assert res_resume.status_code == 200
        assert res_resume.json()["status"] == "resumed"

        # 4. Stop worker
        res_stop = await client.post(f"/api/workers/{worker_id}/stop")
        assert res_stop.status_code == 200
        assert res_stop.json()["status"] == "stopped"


@pytest.mark.asyncio
async def test_api_maintenance_flush(app_setup):
    app, broker, _ = app_setup
    job1 = Job(task_name="flush_test_1", queue="default")
    await broker.enqueue(job1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Flush queues
        res_q = await client.post("/api/maintenance/flush", json={"target": "queues"})
        assert res_q.status_code == 200
        assert res_q.json()["status"] == "ok"

        # Flush history
        res_h = await client.post("/api/maintenance/flush", json={"target": "history"})
        assert res_h.status_code == 200
        assert res_h.json()["status"] == "ok"

        # Flush all
        res_all = await client.post("/api/maintenance/flush", json={"target": "all"})
        assert res_all.status_code == 200
        assert res_all.json()["status"] == "ok"

        # Invalid target
        res_inv = await client.post("/api/maintenance/flush", json={"target": "invalid"})
        assert res_inv.status_code == 400
