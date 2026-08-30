# Specification: TaskManager Core Engine & Management Dashboard

## 1. User Stories
- **US-1**: As a developer, I want to annotate Python functions with `@task` and call `.delay(args)` so that my heavy workloads execute asynchronously in the background.
- **US-2**: As an operator, I want workers to send periodic heartbeats and report CPU/memory/active jobs so that I can see live worker status in a dashboard.
- **US-3**: As an operator, I want to configure dynamic cron expressions from the dashboard/API so that recurring jobs run without modifying application code or restarting services.
- **US-4**: As an operator, I want failed jobs to retry with exponential backoff and land in a Dead Letter Queue (DLQ) with error stack traces when exhausted so that I can inspect and replay them.
- **US-5**: As an operator, I want a sleek Linear-themed SPA dashboard updating in real-time via WebSockets so that I can monitor queue depths, worker status, and task lifecycles with zero page reloads.

## 2. Acceptance Criteria (BDD)

### AC-1: Task Registration & Enqueuing
- **Given** a registered task function decorated with `@task(name="send_email", queue="default")`
- **When** calling `send_email.delay(to="user@example.com", body="Hello")`
- **Then** a job hash is persisted in Redis with state `pending`, and the job ID is appended to `tm:queue:default`.

### AC-2: Worker Execution & State Transition
- **Given** a worker listening on queue `default`
- **When** a job is enqueued
- **Then** the worker claims the job, marks status as `active`, executes the coroutine/function, records the return value, and transitions status to `completed` in Redis.

### AC-3: Retry with Exponential Backoff & DLQ Routing
- **Given** a task configured with `max_retries=3` and `retry_backoff=2`
- **When** the task raises an unhandled exception during execution
- **Then** the job is placed into `tm:delayed:<queue>` with exponential delay for attempts 1 and 2; on attempt 3 exhaustion, it is routed to `tm:dlq:<queue>` with state `failed` and full exception traceback.

### AC-4: Worker Heartbeat & Vitality Telemetry
- **Given** a running worker instance
- **When** the worker is active
- **Then** it pings Redis every 3 seconds updating `tm:worker:<worker_id>` with TTL, current active jobs count, and system stats.

### AC-5: Dynamic Cron & Scheduled Execution
- **Given** a schedule registered with cron expression `* * * * *` or interval in seconds
- **When** the current timestamp reaches or exceeds the calculated next execution time
- **Then** the scheduler service acquires the Redis lock and enqueues a new Job into the specified queue, updating the next run timestamp.

### AC-6: Real-Time Telemetry & WebSocket Event Stream
- **Given** an active WebSocket client connected to `/ws/events`
- **When** any job status changes or worker sends a heartbeat
- **Then** the server broadcasts a structured JSON event to the WebSocket connection within 100ms.

### AC-7: UI Dashboard & Linear Design Compliance
- **Given** an operator navigating to the dashboard
- **When** viewing the UI
- **Then** all surfaces use canvas `#010102`, card backgrounds `#0f1011`, border `#23252a`, accent `#5e6ad2`, and show live metric cards, worker cards, queue tables, cron manager, and DLQ replay action.

## 3. Verification Sensors
| Sensor | Command / Target | Success Threshold |
|---|---|---|
| Linter | `ruff check taskmanager tests` | 0 errors |
| Test Suite | `pytest -v tests/` | 100% pass |
| Build / Import | `python -c "import taskmanager; print(taskmanager.__version__)"` | Clean exit 0 |

## 4. UI & Design System Tokens (Linear Dark Theme)
- **Canvas / Background**: `#010102`
- **Card Surface**: `#0f1011` with `1px solid #23252a`
- **Accent Primary**: `#5e6ad2` (hover `#828fff`, focus `#5e69d1`)
- **Text Ink**: Primary `#f7f8f8`, Muted `#d0d6e0`, Subtle `#8a8f98`
- **Semantic Colors**: Success `#27a644`, Warning `#e59a24`, Error `#d14d42`
- **Typography**: Inter / SF Pro Display fallback, clean weights, tight tracking.
