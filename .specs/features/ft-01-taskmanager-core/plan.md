# Plan: TaskManager Core Engine & Real-Time Management Dashboard

## 1. Problem Statement & Motivation
Modern distributed systems require reliable background task processing (like Celery/BullMQ) with low operational overhead, straightforward Python syntax, and real-time visibility into worker health, dynamic cron schedules, and failed job handling. Existing tools are often either too complex (Celery + Flower + RabbitMQ configuration matrix) or require NodeJS (BullMQ). 

This feature delivers a unified, lightweight Python solution with Redis storage, an async worker runtime, dynamic cron scheduler, and a management SPA dashboard strictly styled to the Linear design system tokens.

## 2. Scope & Boundaries
- **In Scope**:
  - Python `@task` decorator and client library with `.delay()` and `.apply_async()`.
  - Redis broker layer supporting FIFO queues, delayed jobs (ZSet), active worker registry, and Pub/Sub event telemetry.
  - Async Worker Runtime supporting concurrency, task execution, timeout handling, retries with exponential backoff, and heartbeat vitality pings.
  - Dynamic Cron & Scheduled task engine allowing CRUD operations and scheduled execution via Redis locking.
  - Dead Letter Queue (DLQ) for permanently failed tasks with full stack trace capture and replay capability.
  - FastAPI REST & WebSocket server exposing real-time metrics, queue inspection, worker control, and cron configuration.
  - Minimalist SPA Dashboard adhering to `DESIGN.md` (Linear Dark palette `#010102`, cards `#0f1011`, accent `#5e6ad2`, live WebSocket streaming).
  - Comprehensive automated test suite using `fakeredis` and `pytest-asyncio`.
- **Out of Scope**:
  - Multi-datacenter geo-replication.
  - OAuth2 multi-tenant authentication (prepared for future extension).

## 3. High-Level Approach
1. **Core Package Structure**: Implement `taskmanager` with clean separation between `core` (models/broker), `worker` (runner/heartbeat), `scheduler` (cron parser/runner), `api` (FastAPI/WebSocket), and `ui` (SPA dashboard).
2. **Reliable Redis Queuing Primitives**: Use Redis atomic commands (`RPUSH`, `BLPOP`, `HSET`, `ZADD`, `ZPOPMIN`, `SET NX PX`) for zero-loss task dispatching and leader election.
3. **Decoupled Test Suite**: Build a comprehensive `pytest` test suite using `fakeredis` to guarantee 100% test pass rates without external dependencies.
4. **Linear Design UI**: Implement an SPA served by FastAPI utilizing exact tokens from `DESIGN.md`.

## 4. Dependencies & Prerequisites
- Python 3.11+
- `fastapi`, `uvicorn`, `redis`, `pydantic`, `croniter`, `pytest`, `pytest-asyncio`, `fakeredis`

## 5. Architectural Decision Records (ADRs)
- [ADR 0001: Python FastAPI Redis Task Manager Architecture](file:///F:/Projetos/taskmanager/.specs/project/ADRs/0001-python-fastapi-redis-task-manager.md)
