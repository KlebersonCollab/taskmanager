# Roadmap: TaskManager

## Milestone 1: Engine Core & Worker Orchestration (MVP Core)
- [ ] **Redis Broker & Storage Layer**: Queue data structures (ready list, delayed zset, active set, completed/failed hashes).
- [ ] **Task Definition & Client API**: `@task` decorator, `.delay()`, `.apply_async()`, job options (priority, delay, retries, timeout).
- [ ] **Async Worker Runtime**: Process/asyncio job runner, concurrency controls, signal handling (`SIGINT`, `SIGTERM`), heartbeat reporting to Redis.
- [ ] **Orphan Job Reaper & Heartbeat Monitor**: Detect worker crashes and reclaim un-acked active jobs.

## Milestone 2: Scheduled & Cron Engine
- [ ] **Cron Scheduler Service**: Dynamic cron parser (standard 5-part cron syntax), interval expressions, next run calculations.
- [ ] **Schedule Persistence & Mutability**: CRUD API for registering, enabling, disabling, and dynamically editing cron schedules without restarting workers.

## Milestone 3: Real-Time Management API & Telemetry
- [ ] **FastAPI REST API**: Endpoints for queues, jobs (filtering by state), workers, schedules, and metrics.
- [ ] **Real-Time Event Stream**: WebSocket / SSE broadcasting job status transitions, worker heartbeats, and queue depth metrics.
- [ ] **Control Actions**: Pause/resume queues, cancel running jobs, manual job retry, and worker drain.

## Milestone 4: Dead Letter Queue (DLQ) & Resilience
- [ ] **DLQ Storage & Stack Trace Capture**: Automated routing of exhausted failures to DLQ with execution metadata.
- [ ] **DLQ Management**: Inspect error tracebacks, edit payload (optional), and bulk replay or purge failed jobs.

## Milestone 5: SPA Management Dashboard (Linear Theme)
- [ ] **Dashboard Layout & Overview**: Real-time queue counters, throughput chart, active worker counter, system health.
- [ ] **Workers View**: Live heartbeat monitor, active jobs per worker, memory/CPU telemetry, pause/drain controls.
- [ ] **Jobs & Queues Explorer**: Paginated job list with state filters (Active, Waiting, Delayed, Completed, Failed), detailed modal with args and return values.
- [ ] **Cron / Scheduled Tasks View**: Interactive table with next run countdown, trigger now button, add/edit schedule modal.
- [ ] **DLQ Inspector**: Error viewer with syntax highlighting and one-click replay.
