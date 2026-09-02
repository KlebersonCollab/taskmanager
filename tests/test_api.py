import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient

from taskmanager.api.app import create_app
from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job, JobStatus
from taskmanager.core.task import TaskRegistry, task
from taskmanager.scheduler.cron import Schedule, ScheduleType


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

        # 1. Create custom queue
        res_create_q = await client.post("/api/queues", json={"name": "custom_queue_test"})
        assert res_create_q.status_code == 200
        assert res_create_q.json()["status"] == "created"
        assert res_create_q.json()["queue"] == "custom_queue_test"

        # 2. Verify queue appears in list
        res_queues2 = await client.get("/api/queues")
        q_names = [q["queue"] for q in res_queues2.json()]
        assert "custom_queue_test" in q_names

        # 3. Create invalid empty queue
        res_err = await client.post("/api/queues", json={"name": "   "})
        assert res_err.status_code == 400

        # 4. Delete default queue forbidden
        res_del_def = await client.delete("/api/queues/default")
        assert res_del_def.status_code == 400

        # 5. Delete custom queue
        res_del_q = await client.delete("/api/queues/custom_queue_test")
        assert res_del_q.status_code == 200
        assert res_del_q.json()["status"] == "deleted"

        # 6. Delete nonexistent queue
        res_del_non = await client.delete("/api/queues/non_existent_queue_xyz")
        assert res_del_non.status_code == 404


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
    # Manually seed DLQ jobs in different queues
    job1 = Job(
        task_name="failed_task_1", queue="default", status=JobStatus.FAILED, error="CriticalError"
    )
    job2 = Job(
        task_name="failed_task_2", queue="payments", status=JobStatus.FAILED, error="PaymentDeclined"
    )
    await broker.save_job(job1)
    await broker.save_job(job2)
    await broker.redis.sadd(broker._key_queues(), "default", "payments")
    await broker.redis.rpush(broker._key_dlq("default"), job1.id)
    await broker.redis.rpush(broker._key_dlq("payments"), job2.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Fetch DLQ for all queues
        res_all = await client.get("/api/dlq")
        assert res_all.status_code == 200
        dlq_all = res_all.json()
        assert len(dlq_all) == 2

        # Fetch DLQ for specific payments queue
        res_pay = await client.get("/api/dlq/payments")
        assert res_pay.status_code == 200
        dlq_pay = res_pay.json()
        assert len(dlq_pay) == 1
        assert dlq_pay[0]["id"] == job2.id

        # Replay DLQ job1
        res_replay = await client.post(f"/api/dlq/{job1.id}/replay")
        assert res_replay.status_code == 200
        assert res_replay.json()["status"] == "replayed"

        # Check default DLQ is empty, but payments still has job2
        res_after = await client.get("/api/dlq/default")
        assert len(res_after.json()) == 0
        res_after_all = await client.get("/api/dlq")
        assert len(res_after_all.json()) == 1

        # Purge all DLQ
        res_purge = await client.post("/api/dlq/purge")
        assert res_purge.status_code == 200
        assert res_purge.json()["status"] == "purged"
        res_final = await client.get("/api/dlq")
        assert len(res_final.json()) == 0


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


@pytest.mark.asyncio
async def test_api_lifespan_scheduler_execution(app_setup):
    app, broker, _ = app_setup
    # Add a schedule that is immediately due
    sched = Schedule(
        name="Lifespan Sched",
        task_name="api_ping",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=0.5,
        next_run=time.time() - 1.0,
    )
    await app.state.scheduler.add_schedule(sched)

    # Use lifespan context manager to run lifespan startup/shutdown
    async with app.router.lifespan_context(app):
        # Give the scheduler daemon a moment to tick
        await asyncio.sleep(1.2)

        # Verify job was enqueued into broker
        fetched = await broker.fetch_next_job(["default"], worker_id="lifespan-w")
        assert fetched is not None
        assert fetched.task_name == "api_ping"


@pytest.mark.asyncio
async def test_api_job_progress_and_live_events(app_setup):
    app, broker, reg = app_setup
    from taskmanager.core.task import TaskContext

    @task(name="api_progress_task", queue="default", broker=broker)
    async def api_progress_task(steps: int, ctx: TaskContext):
        for i in range(steps):
            await ctx.update_progress(
                percent=((i + 1) / steps) * 100.0,
                message=f"Step {i+1}/{steps} complete",
            )
            await ctx.append_log(f"Log event for step {i+1}")
        return {"status": "ok", "steps": steps}

    reg.register(api_progress_task)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Enqueue task via REST API
        res = await client.post(
            "/api/tasks/api_progress_task/enqueue",
            json={"args": [3]},
        )
        assert res.status_code == 200
        job_id = res.json()["id"]

        # 2. Worker executes task
        from taskmanager.worker.worker import Worker
        worker = Worker(queues=["default"], concurrency=1, broker=broker, task_registry=reg)
        worker_task = asyncio.create_task(worker.start())

        await asyncio.sleep(0.1)
        await worker.stop()
        worker_task.cancel()

        # 3. Verify get job by ID returns 100% progress and logs
        res_job = await client.get(f"/api/jobs/{job_id}")
        assert res_job.status_code == 200
        job_data = res_job.json()
        assert job_data["status"] == "completed"
        assert job_data["progress"] == 100.0
        assert any("Log event for step 3" in log for log in job_data["logs"])

        # 4. Verify history endpoint contains progress
        res_hist = await client.get("/api/jobs/history")
        assert res_hist.status_code == 200
        hist_jobs = res_hist.json()
        target = next((j for j in hist_jobs if j["id"] == job_id), None)
        assert target is not None
        assert target["progress"] == 100.0


@pytest.mark.asyncio
async def test_api_timeseries_metrics_endpoint(app_setup):
    app, broker, _ = app_setup
    job = Job(task_name="api_ping", queue="default", status=JobStatus.COMPLETED)
    job.started_at = time.time() - 10
    job.completed_at = time.time()
    job.duration = 0.08
    await broker.save_job(job)
    await broker.redis.zadd(broker._key_history(), {job.id: job.completed_at})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/metrics/timeseries?window_minutes=30")
        assert res.status_code == 200
        data = res.json()
        assert "throughput_series" in data
        assert "latency_histogram" in data
        assert "latency_percentiles" in data
        assert "task_breakdown" in data
        assert data["total_executions"] >= 1
        assert data["window_minutes"] == 30

        # Test bounds clamping (< 5 clamped to 5, > 1440 clamped to 1440)
        res_min = await client.get("/api/metrics/timeseries?window_minutes=-5")
        assert res_min.status_code == 200
        assert res_min.json()["window_minutes"] == 5

        res_max = await client.get("/api/metrics/timeseries?window_minutes=99999")
        assert res_max.status_code == 200
        assert res_max.json()["window_minutes"] == 1440


@pytest.mark.asyncio
async def test_api_alert_channels_crud_and_test_dispatch(app_setup):
    app, broker, _ = app_setup
    from unittest.mock import AsyncMock, patch

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create alert channel
        payload = {
            "name": "Ops Slack Alerts",
            "channel_type": "slack",
            "target_url": "https://hooks.slack.com/services/test/xxx/yyy",
            "events": ["job:failed"],
            "enabled": True,
        }
        res = await client.post("/api/alerts/channels", json=payload)
        assert res.status_code == 200
        created = res.json()
        ch_id = created["id"]
        assert created["name"] == "Ops Slack Alerts"
        assert created["channel_type"] == "slack"

        # 2. List alert channels
        res_list = await client.get("/api/alerts/channels")
        assert res_list.status_code == 200
        channels = res_list.json()
        assert len(channels) == 1
        assert channels[0]["id"] == ch_id

        # 3. Get channel by ID
        res_get = await client.get(f"/api/alerts/channels/{ch_id}")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == ch_id

        # 4. Update channel
        payload["name"] = "Updated Slack Alerts"
        res_put = await client.put(f"/api/alerts/channels/{ch_id}", json=payload)
        assert res_put.status_code == 200
        assert res_put.json()["name"] == "Updated Slack Alerts"

        # 5. Test ping dispatch
        with patch.object(broker.alert_dispatcher, "send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}
            res_test = await client.post(f"/api/alerts/channels/{ch_id}/test")
            assert res_test.status_code == 200
            assert res_test.json()["success"] is True
            mock_send.assert_called_once()

        # 6. Delete channel
        res_del = await client.delete(f"/api/alerts/channels/{ch_id}")
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "deleted"

        # 7. Verify 404 after deletion
        res_404 = await client.get(f"/api/alerts/channels/{ch_id}")
        assert res_404.status_code == 404




