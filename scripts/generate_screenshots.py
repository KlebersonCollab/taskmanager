import asyncio
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath("."))

import redis.asyncio as redis
from playwright.async_api import async_playwright

from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job, JobStatus
from taskmanager.scheduler.cron import Schedule, ScheduleType
from taskmanager.scheduler.scheduler import Scheduler
from taskmanager.worker.heartbeat import WorkerInfo

DEMO_PORT = 8899
REDIS_URL = "redis://localhost:6379/15"  # Use isolated DB 15 for demo screenshots
OUTPUT_DIR = os.path.abspath("docs/images")

async def seed_demo_data(broker: RedisBroker):
    # 1. Clean DB 15
    await broker.flush_all()

    # 2. Register Queues
    for q in ["default", "emails", "payments", "reports", "webhooks"]:
        await broker.create_queue(q)

    # 3. Create Workers
    w1 = WorkerInfo(
        id="w_emails_01",
        name="worker-emails-prod-01",
        queues=["emails", "default"],
        concurrency=10,
        status="busy",
        active_jobs_count=6,
        cpu_percent=32.4,
        memory_mb=145.2,
        completed_jobs_count=1240,
        failed_jobs_count=3
    )

    w2 = WorkerInfo(
        id="w_reports_02",
        name="worker-reports-heavy-02",
        queues=["reports"],
        concurrency=4,
        status="busy",
        active_jobs_count=1,
        cpu_percent=68.5,
        memory_mb=420.8,
        completed_jobs_count=312,
        failed_jobs_count=1
    )

    w3 = WorkerInfo(
        id="w_payments_03",
        name="worker-payments-secure-03",
        queues=["payments", "webhooks"],
        concurrency=8,
        status="idle",
        active_jobs_count=0,
        cpu_percent=4.2,
        memory_mb=98.0,
        completed_jobs_count=850,
        failed_jobs_count=0
    )

    for w in [w1, w2, w3]:
        key = broker._key_worker(w.id)
        await broker.redis.set(key, w.model_dump_json(), ex=600)
        await broker.redis.sadd(broker._key_workers(), w.id)

    # 4. Create Schedules
    sched = Scheduler(broker)
    s1 = Schedule(
        name="sync_stripe_charges",
        task_name="example_tasks.sync_stripe_payouts",
        schedule_type=ScheduleType.CRON,
        cron_expression="*/5 * * * *",
        queue="payments",
        args=["USD", "BRL"],
    )
    await sched.add_schedule(s1)

    s2 = Schedule(
        name="daily_executive_metrics",
        task_name="example_tasks.generate_pdf_report",
        schedule_type=ScheduleType.CRON,
        cron_expression="0 8 * * *",
        queue="reports",
        kwargs={"format": "pdf", "notify": True},
    )
    await sched.add_schedule(s2)

    s3 = Schedule(
        name="cleanup_expired_sessions",
        task_name="example_tasks.cleanup_temp_files",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
        queue="default",
    )
    await sched.add_schedule(s3)

    # 5. Seed Enqueued & Delayed Jobs
    for i in range(12):
        j = Job(task_name="example_tasks.send_email", queue="emails", args=[f"user{i}@enterprise.com", "Fatura Processada"])
        await broker.enqueue(j)

    for i in range(4):
        j = Job(task_name="example_tasks.generate_pdf_report", queue="reports", kwargs={"report_id": 100 + i})
        await broker.schedule_delayed(j, delay_seconds=120 + (i * 60))

    # 6. Seed DLQ Jobs
    dlq_job1 = Job(task_name="example_tasks.charge_credit_card", queue="payments", args=["cust_9921", 450.00], max_retries=3)
    dlq_job1.status = JobStatus.FAILED
    dlq_job1.retry_count = 3
    dlq_job1.completed_at = time.time() - 120
    dlq_job1.duration = 1.45
    dlq_job1.error = "StripeGatewayTimeoutError: Gateway 504 on POST /v1/charges after 3 attempts."
    await broker.save_job(dlq_job1)
    await broker.redis.lpush(broker._key_dlq("payments"), dlq_job1.id)
    await broker.redis.zadd(broker._key_history(), {dlq_job1.id: dlq_job1.completed_at})

    dlq_job2 = Job(task_name="example_tasks.send_email", queue="emails", args=["invalid-email@", "Boas-vindas"], max_retries=2)
    dlq_job2.status = JobStatus.FAILED
    dlq_job2.retry_count = 2
    dlq_job2.completed_at = time.time() - 60
    dlq_job2.duration = 0.22
    dlq_job2.error = "InvalidEmailRecipient: Domain lookup failed for 'invalid-email@'."
    await broker.save_job(dlq_job2)
    await broker.redis.lpush(broker._key_dlq("emails"), dlq_job2.id)
    await broker.redis.zadd(broker._key_history(), {dlq_job2.id: dlq_job2.completed_at})

    # 7. Seed Completed History Jobs
    for i in range(8):
        h = Job(task_name="example_tasks.process_payment", queue="payments", args=[f"order_{1000+i}", 99.90])
        h.status = JobStatus.COMPLETED
        h.started_at = time.time() - 300 + (i * 20)
        h.completed_at = h.started_at + 0.142 + (i * 0.02)
        h.duration = h.completed_at - h.started_at
        h.worker_id = "worker-payments-secure-03"
        h.result = {"status": "approved", "auth_code": f"AUTH_{9821+i}"}
        await broker.save_job(h)
        await broker.redis.zadd(broker._key_history(), {h.id: h.completed_at})

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    broker = RedisBroker(redis_client, prefix="tm_demo")

    print("[1/5] Populando dados de demonstração no Redis DB 15...")
    await seed_demo_data(broker)

    print(f"[2/5] Iniciando servidor FastAPI em http://127.0.0.1:{DEMO_PORT} via subprocess...")
    env = os.environ.copy()
    env["REDIS_URL"] = REDIS_URL
    env["REDIS_PREFIX"] = "tm_demo"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "taskmanager.cli",
            "server",
            "--port",
            str(DEMO_PORT),
            "--app-module",
            "example_tasks",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)  # Wait for server to start

    try:
        print("[3/5] Abrindo Playwright Chromium headless (1440x920 @ 2x Retina DPI)...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1440, "height": 920},
                device_scale_factor=2,  # Crisp Retina Screenshots
                color_scheme="dark",
            )
            page = await context.new_page()

            # 1. Overview Tab
            print("[4/5] Capturando 01_dashboard_overview.png...")
            await page.goto(f"http://127.0.0.1:{DEMO_PORT}/", wait_until="networkidle")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "01_dashboard_overview.png"))

            # 2. Workers Tab
            print("Capturando 02_workers_management.png...")
            await page.click('button[data-tab="workers"]')
            await page.wait_for_timeout(600)
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "02_workers_management.png"))

            # 3. Queues & Tasks Tab
            print("Capturando 03_tasks_queues.png...")
            await page.click('button[data-tab="queues"]')
            await page.wait_for_timeout(600)
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "03_tasks_queues.png"))

            # 4. Cron Schedules Tab
            print("Capturando 04_cron_schedules.png...")
            await page.click('button[data-tab="schedules"]')
            await page.wait_for_timeout(600)
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "04_cron_schedules.png"))

            # 5. DLQ Tab
            print("Capturando 05_dlq_inspector.png...")
            await page.click('button[data-tab="dlq"]')
            await page.wait_for_timeout(600)
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "05_dlq_inspector.png"))

            # 6. Observability & Trace Modal
            print("Capturando 06_observability_trace.png...")
            await page.click('button[data-tab="history"]')
            await page.wait_for_timeout(600)
            # Open trace modal for the first completed job
            first_trace_btn = await page.query_selector('#history-table button.btn-action')
            if first_trace_btn:
                await first_trace_btn.click()
                await page.wait_for_timeout(600)
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "06_observability_trace.png"))
            await page.evaluate("closeModal('modal-lgtm-trace')")
            await page.wait_for_timeout(400)

            # 7. Command Palette (Ctrl+K)
            print("Capturando 07_command_palette.png...")
            await page.click('button[data-tab="overview"]')
            await page.wait_for_timeout(400)
            await page.click('button.btn-command-palette')
            await page.wait_for_timeout(500)
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "07_command_palette.png"))
            await page.evaluate("closeModal('modal-command-palette')")
            await page.wait_for_timeout(400)

            # 8. Create Dropdown Menu Open
            print("Capturando 08_quick_create_menu.png...")
            await page.click('#dropdown-create > button')
            await page.wait_for_timeout(500)
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "08_quick_create_menu.png"))

            await browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
        await broker.flush_all()
        await redis_client.aclose()

    print(f"[5/5] Todas as 8 capturas em alta resolucao foram salvas com sucesso em: {OUTPUT_DIR}")

if __name__ == "__main__":
    asyncio.run(main())
