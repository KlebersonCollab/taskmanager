# TaskManager ⚡

> Modern background task execution engine inspired by **Celery** and **BullMQ**, featuring dynamic **Cron/Scheduled Jobs**, **Dead Letter Queue (DLQ)**, worker heartbeat telemetry, and a sleek **Linear Dark SPA Management Dashboard**.

---

## 🌟 Features

- **🚀 Asyncio & Sync Worker Runtime**: Native support for Python async coroutines (`async def`) and synchronous functions (`def`), with configurable concurrency and timeouts.
- **📦 Redis-Native Queues & Storage**: Zero heavyweight brokers. Uses Redis atomic lists, sorted sets (delayed jobs), hashes, and Pub/Sub for sub-millisecond execution and event broadcasting.
- **✨ Simple `@task` Decorator**: Enqueue jobs with `.delay(*args, **kwargs)` or `.apply_async(...)` with exponential backoff and custom priority.
- **⏰ Dynamic Cron & Interval Scheduler**: Dynamic scheduling with standard 5-part cron syntax (`*/5 * * * *`) or interval in seconds, complete with live editing and manual trigger without restarting services.
- **🛡️ Resilience & DLQ**: Configurable retry policies with exponential backoff. Jobs exhausting retries land in a Dead Letter Queue (DLQ) with full exception stack traces and one-click replay.
- **💓 Worker Vitality & Orphan Reaping**: Real-time heartbeat reporting (CPU %, memory MB, active jobs) with automatic reclamation of orphaned jobs if a worker dies.
- **🎨 Linear Dark UI Dashboard**: Built to strict [DESIGN.md](DESIGN.md) specifications (`#010102` canvas, `#0f1011` panels, `#5e6ad2` accent), updating in real time via WebSockets.

---

## 🚀 Quickstart

### 1. Installation & Environment (com `uv`)

```bash
# 1. Sincronizar o ambiente virtual e dependências automaticamente
uv sync --all-extras

# 2. Adicionar novas dependências quando necessário
# uv add <pacote>
# uv add --dev <pacote_dev>
```

### 2. Define Background Tasks

Create a module (e.g. `my_tasks.py`):

```python
import asyncio
from taskmanager.core.task import task

@task(name="send_welcome_email", queue="emails", max_retries=3, retry_backoff=2.0)
async def send_welcome_email(user_email: str, name: str):
    await asyncio.sleep(1) # Simulate network call
    print(f"📧 Sent email to {name} <{user_email}>")
    return {"status": "sent", "to": user_email}

@task(name="generate_monthly_report", queue="reports")
def generate_monthly_report(month: str, year: int):
    # Synchronous task
    print(f"📊 Generating report for {month}/{year}")
    return {"report_id": f"REP-{year}-{month}"}
```

### 3. Enqueue Jobs

```python
import asyncio
from my_tasks import send_welcome_email, generate_monthly_report

async def main():
    # Immediate execution in background
    job1 = await send_welcome_email.delay("alice@example.com", "Alice")
    print(f"Enqueued Job ID: {job1.id}")

    # Delayed execution (run in 30 seconds)
    job2 = await generate_monthly_report.apply_async(
        args=["August", 2026],
        delay=30.0,
    )
    print(f"Delayed Job ID: {job2.id}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 💻 CLI Commands

### ⚡ All-in-One Dev Mode
Starts the **API Server + Dashboard**, **Worker**, and **Scheduler** concurrently:
```bash
# Run with the bundled example tasks
uv run taskmanager dev --modules example_tasks

# Or test programmatically enqueuing jobs in another terminal
uv run python enqueue_examples.py
```
Open **http://localhost:8000** in your browser to access the management dashboard.

### 🏭 Standalone Worker
```bash
taskmanager worker --queues emails,reports,default --concurrency 8 --modules my_tasks
```

### ⏰ Standalone Dynamic Scheduler
```bash
taskmanager scheduler --modules my_tasks
```

### 🌐 Standalone Dashboard & API Server
```bash
taskmanager server --host 0.0.0.0 --port 8000 --app-module my_tasks
```

---

## 🐳 Running with Docker & Docker Compose

To launch the complete distributed stack (**Redis + Dashboard + Specialized Workers + Scheduler**) with one command:

```bash
docker compose up --build -d
```

Check running services:
```bash
docker compose ps
```

* **Dashboard**: [http://localhost:8000](http://localhost:8000)
* **Redis**: `localhost:6379`
* **Worker Emails**: Dedicated worker for `emails` queue (`concurrency=10`).
* **Worker Reports**: Dedicated worker for `reports,default,payments` with 1GB RAM backpressure ceiling (`concurrency=4`).
* **Scheduler**: Distributed cron daemon.

Stop the stack:
```bash
docker compose down
```

---

## 📊 Management Dashboard Overview

The dashboard is accessible directly at `http://localhost:8000/`:

1. **Visão Geral (Overview)**: Live KPI cards (active workers, pending jobs, delayed jobs, DLQ jobs, active crons) and a real-time event ticker streamed via WebSockets.
2. **Workers**: Real-time worker cards displaying memory RSS, CPU load, active/concurrency ratio, queue assignments, and heartbeat timestamps.
3. **Filas & Jobs**: Interactive explorer of all registered `@task` functions with one-click testing and JSON payload dispatching.
4. **Cron & Agendamentos**: Dynamic cron manager allowing you to add, pause, trigger now (⚡), or delete recurring schedules.
5. **Dead Letter Queue (DLQ)**: Failed job viewer with full error tracebacks and one-click replay (⚡).

---

## 🧪 Testing & Verification

Run the automated test suite with fake Redis in-memory isolation:
```bash
uv run pytest -v tests/
```

Run code formatting and linting:
```bash
uv run ruff check taskmanager tests
```

---

## 📄 License
MIT License
