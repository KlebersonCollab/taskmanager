# TaskManager ⚡

> Modern high-performance background task execution engine inspired by **Celery** and **BullMQ**, featuring **Dynamic Cron Scheduling**, **Observabilidade Completa (LGTM Stack)**, **Dead Letter Queue (DLQ)**, worker heartbeat telemetry, backpressure resource guardrails, and a sleek **Linear Dark SPA Management Dashboard**.

---

## 🌟 Key Features

- **🚀 Asyncio & Sync Worker Runtime**: Native support for Python async coroutines (`async def`) and synchronous functions (`def`), with configurable concurrency and timeouts.
- **📦 Redis-Native Queues & Storage**: Zero heavyweight brokers. Uses Redis atomic lists (`LPOP`/`BLPOP`), sorted sets (delayed jobs & history), hashes, and Pub/Sub for sub-millisecond execution and event broadcasting.
- **🧠 Zero-Dependency In-Memory Fallback**: Automatic fallback to built-in in-memory Redis (`fakeredis`) during development if an external Redis server is not running.
- **✨ Simple `@task` Decorator & Signature Introspection**: Enqueue jobs with `.delay(*args, **kwargs)` or `.apply_async(...)`. The dashboard automatically inspects function parameters and docstrings to prefill typed JSON payloads.
- **⏰ Dynamic Cron & Interval Scheduler**: Dynamic scheduling with standard 5-part cron syntax (`*/5 * * * *`) or interval in seconds, complete with live editing, toggle, and manual trigger without restarting services.
- **🛡️ Resilience, DLQ & Backpressure**: Configurable retry policies with exponential backoff. Jobs exhausting retries land in a Dead Letter Queue (DLQ) with full stack traces and one-click replay. Workers feature memory/CPU backpressure circuit breakers.
- **📊 LGTM Observability Stack**:
  - **📈 Mimir/Prometheus**: Live aggregated KPIs (Success Rate %, Avg Duration ms, P95 Latency ms, Throughput/min).
  - **📜 Loki**: Execution log stream, error tracebacks, and captured output.
  - **⏱️ Tempo**: Lifecycle trace timeline waterfall (Enqueued ➔ Worker Dequeue ➔ Active ➔ Completed/Failed).
  - **📊 Grafana Dashboard**: Live execution history table with status filtering and real-time WebSocket ticker.
- **🎨 Linear Dark UI Dashboard**: Built to strict [DESIGN.md](DESIGN.md) specifications (`#010102` canvas, `#0f1011` panels, `#5e6ad2` accent), updating in real time via WebSockets.

---

## 🚀 Installation & Environment (with `uv`)

```bash
# 1. Clone the repository
git clone https://github.com/usuario/taskmanager.git
cd taskmanager

# 2. Sync virtual environment and install all dependencies
uv sync --all-extras
```

---

## 💻 Complete CLI Commands Reference

TaskManager provides a unified CLI with 4 primary commands: `dev`, `worker`, `scheduler`, and `server`.

### 1. `taskmanager dev` (All-in-One Development Mode)
Starts the **API Server + Dashboard**, **Worker**, and **Scheduler** in a single concurrent process.

```bash
# Run with bundled example tasks (auto-falls back to in-memory Redis if local Redis is offline)
uv run taskmanager dev --modules example_tasks

# Customize host, port, concurrency, and memory guardrails
uv run taskmanager dev --host 0.0.0.0 --port 8000 -c 8 --max-memory-mb 512 --max-cpu-percent 85 --modules example_tasks
```

**Options:**
| Flag | Description | Default |
| :--- | :--- | :--- |
| `--host HOST` | Host interface to bind API server | `0.0.0.0` |
| `--port PORT` | Port for Dashboard & API server | `8000` |
| `-q, --queues QUEUES` | Comma-separated queue names (auto-listens to all registered queues if `default`) | `default` |
| `-c, --concurrency N` | Maximum concurrent tasks for the dev worker | `5` |
| `--max-memory-mb MB` | Max RSS memory limit (MB) before pausing job consumption (backpressure) | `None` (Unlimited) |
| `--max-cpu-percent PCT`| Max CPU percentage before pausing job consumption (backpressure) | `None` (Unlimited) |
| `--redis-url URL` | Redis connection URL | `redis://localhost:6379/0` |
| `--in-memory` | Force built-in In-Memory Redis mode | `False` |
| `-m, --modules [MOD ...]` | Python modules or `.py` file paths to import for task auto-discovery | `[]` |

---

### 2. `taskmanager worker` (Distributed Worker Process)
Starts an async worker daemon capable of concurrent job execution with automatic Redis competing-consumers load balancing.

```bash
# Launch a dedicated worker for email jobs
uv run taskmanager worker -n worker-emails -q emails -c 10 -m example_tasks

# Launch a memory-capped worker for heavy reports and general queues
uv run taskmanager worker -n worker-heavy -q reports,default,payments -c 4 --max-memory-mb 1024 -m example_tasks

# Connect to a remote Redis instance
uv run taskmanager worker -q default -c 5 --redis-url redis://redis.producao.com:6379/0 -m example_tasks
```

**Options:**
| Flag | Description | Default |
| :--- | :--- | :--- |
| `-n, --name NAME` | Custom worker identifier name | `worker-<uuid>` |
| `-q, --queues QUEUES` | Comma-separated queues to consume from (ordered priority) | `default` |
| `-c, --concurrency N` | Maximum concurrent tasks for this worker | `5` |
| `--max-memory-mb MB` | Max RSS memory (MB) before backpressure | `None` |
| `--max-cpu-percent PCT`| Max CPU percentage before backpressure | `None` |
| `--redis-url URL` | Redis connection URL | `redis://localhost:6379/0` |
| `--in-memory` | Force in-memory mode | `False` |
| `-m, --modules [MOD ...]` | Modules or `.py` files containing `@task` definitions | `[]` |

---

### 3. `taskmanager scheduler` (Dynamic Cron Scheduler Daemon)
Starts the distributed scheduler that evaluates cron expressions and interval schedules, enqueuing jobs with distributed Redis leader locking.

```bash
uv run taskmanager scheduler -m example_tasks
```

**Options:**
| Flag | Description | Default |
| :--- | :--- | :--- |
| `--redis-url URL` | Redis connection URL | `redis://localhost:6379/0` |
| `--in-memory` | Force in-memory mode | `False` |
| `-m, --modules [MOD ...]` | Modules or `.py` files to import for task validation | `[]` |

---

### 4. `taskmanager server` (Standalone Dashboard & REST API)
Starts only the FastAPI application, WebSocket broadcaster, and Linear Dark SPA Dashboard without running local workers.

```bash
uv run taskmanager server --host 0.0.0.0 --port 8000 --app-module example_tasks
```

**Options:**
| Flag | Description | Default |
| :--- | :--- | :--- |
| `--host HOST` | Host address to bind | `0.0.0.0` |
| `--port PORT` | HTTP port | `8000` |
| `--redis-url URL` | Redis connection URL | `redis://localhost:6379/0` |
| `--in-memory` | Force in-memory mode | `False` |
| `--app-module [MOD ...]`| Modules containing `@task` definitions | `[]` |

---

## 🐍 Python SDK Guide

### 1. Defining Tasks (`@task`)

```python
# example_tasks.py
import asyncio
from taskmanager import task

# Async Task with Exponential Backoff
@task(
    name="emails.send_welcome_email",
    queue="emails",
    max_retries=3,
    retry_backoff=2.0,  # 2s, 4s, 8s backoff
    timeout=10.0,
)
async def send_welcome_email(email: str, name: str) -> dict:
    """Simulates async email delivery."""
    await asyncio.sleep(1.5)
    print(f"📧 Sent email to {name} <{email}>")
    return {"status": "delivered", "recipient": email}


# Synchronous Heavy CPU Task
@task(
    name="reports.generate_sales_report",
    queue="reports",
    max_retries=1,
    timeout=60.0,
)
def generate_sales_report(year: int, month: int, department: str = "Geral") -> dict:
    """Simulates CPU-heavy report generation."""
    # Runs in threadpool executor without blocking the asyncio event loop
    return {"file": f"/exports/{department}_{year}_{month:02d}.pdf"}
```

### 2. Enqueuing Jobs Programmatically

```python
# enqueue_examples.py
import asyncio
from example_tasks import send_welcome_email, generate_sales_report

async def main():
    # 1. Immediate Execution (.delay)
    job1 = await send_welcome_email.delay("cliente@empresa.com", "Carlos Silva")
    print(f"Enqueued Job ID: {job1.id}")

    # 2. Delayed Execution (.apply_async)
    job2 = await generate_sales_report.apply_async(
        kwargs={"year": 2026, "month": 8, "department": "Financeiro"},
        delay=15.0,  # Runs after 15 seconds
        queue="reports",
        priority=1,
    )
    print(f"Delayed Job ID: {job2.id}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Built-in System Tasks (Zero-Code Script Execution)
You can trigger standalone shell or python scripts directly from the Dashboard without authoring Python decorators:

* **`system.run_command`**: Runs arbitrary shell commands (e.g. `python scripts/backup_database.py --compress`).
* **`system.run_script`**: Runs a Python script file with arguments.

---

## 🐳 Docker & Docker Compose Stack

Launch a complete multi-worker distributed cluster with Redis in seconds:

```bash
# Start all services in the background
docker compose up --build -d

# Check cluster health
docker compose ps

# Follow live cluster logs
docker compose logs -f

# Scale workers horizontally
docker compose up -d --scale worker-emails=3

# Stop cluster
docker compose down
```

**Services in `docker-compose.yml`:**
- 🔴 **`redis`**: Redis 7 Alpine with persistent storage volume (`redis_data`).
- 🌐 **`dashboard`**: Management Dashboard & API server on [http://localhost:8000](http://localhost:8000).
- 📧 **`worker-emails`**: High-concurrency worker dedicated to `emails` (`concurrency=10`).
- 📊 **`worker-reports`**: Memory-capped worker for `reports,default,payments` (`max-memory-mb=1024`, `concurrency=4`).
- ⏰ **`scheduler`**: Distributed cron scheduler daemon.

---

## 📊 Management Dashboard Walkthrough

Access the web console directly at **http://localhost:8000/**:

1. **Visão Geral (Overview)**: Real-time KPI cards for active workers, pending jobs, delayed jobs, DLQ jobs, worker CPU & RSS memory telemetry, and WebSocket live event ticker.
2. **Workers**: Health matrix of all worker processes showing RSS memory (MB), CPU %, concurrency slots, queues, and last heartbeat.
3. **Filas & Jobs**: Interactive explorer of all registered `@task` functions with signature inspection and prefilled JSON payload dispatching.
4. **Cron & Agendamentos**: Dynamic cron manager allowing you to create, pause/resume, delete, or trigger now (⚡) recurring schedules.
5. **Dead Letter Queue (DLQ)**: Failed job inspector displaying exception stack traces, attempt counts, and one-click replay (⚡).
6. **📊 Execuções & Métricas (LGTM Stack)**:
   - **Mimir/Prometheus KPIs**: Success rate %, average duration ms, P95 latency ms, and throughput/min.
   - **Execution History**: Searchable and filterable log of recent jobs.
   - **Tempo Trace & Loki Log Inspector**: Full lifecycle timeline waterfall and captured logs console.

---

## 🧪 Testing & Verification

Run the full automated test suite with in-memory Redis isolation:
```bash
uv run pytest -v tests/
```

Run code quality linting:
```bash
uv run ruff check taskmanager tests example_tasks.py enqueue_examples.py scripts/
```

Run Pre-Commit Spec Drift Sensor:
```bash
node .agents/scripts/check-spec-drift.js
```

---

## ⚙️ Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `REDIS_PREFIX` | Key namespace prefix in Redis | `tm` |
| `DEFAULT_QUEUE` | Default queue name | `default` |

---

## 📄 License
MIT License. Open-source and enterprise-ready.
