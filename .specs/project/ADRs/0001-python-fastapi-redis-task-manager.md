# ADR 0001: Python (FastAPI + Asyncio Worker) with Redis Broker & SPA Dashboard

## Status
Accepted

## Context
The goal is to build a modern background task manager inspired by Celery and BullMQ, featuring worker management, dynamic cron/scheduled tasks, real-time live telemetry, DLQ handling, and a management frontend dashboard complying with the `DESIGN.md` Linear design system.

The core challenge is balancing high performance, developer convenience, robust worker resilience, and real-time observability without unnecessary operational complexity.

## Decision
1. **Runtime & Language**: Use Python 3.11+ leveraging `asyncio` for non-blocking I/O, FastAPI for the REST/WebSocket management API, and standard process/coroutine worker primitives.
2. **Broker & Storage**: Use Redis 7+ data structures:
   - Lists (`RPUSH` / `BLPOP` or `BRPOPLPUSH`) for FIFO queues.
   - Sorted Sets (`ZADD` / `ZRANGEBYSCORE`) for delayed jobs and cron scheduling.
   - Hashes for job payload, execution metadata, and worker telemetry.
   - Sets for active worker registry and queue registration.
   - Pub/Sub / Redis Streams for live event broadcasting to WebSocket connections.
3. **Cron Engine**: Built-in dynamic scheduler service utilizing croniter/standard cron parsing with distributed leader locking via Redis `SET NX PX`.
4. **Frontend Architecture**: Minimalist SPA dashboard built with HTML5/Modern Vanilla JS/Tailwind or lightweight SPA bundle, rigorously adopting the color palette, typography, and card panels from `DESIGN.md`.

## Consequences
### Positive
- Unified Python developer experience for defining and executing async background tasks with clean `@task` decorators.
- Zero external heavyweight dependencies (e.g., no Erlang/RabbitMQ required; Redis handles queuing, storage, and pub/sub).
- Real-time updates delivered smoothly via FastAPI WebSockets.
- Fully controllable workers with heartbeats, drain/pause operations, and orphan job reaping.

### Negative / Trade-offs
- In-memory Redis requires memory monitoring for massive queue backlogs (mitigated by job result TTL and payload size limits).
