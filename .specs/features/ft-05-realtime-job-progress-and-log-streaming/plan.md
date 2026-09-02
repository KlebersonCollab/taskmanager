# Plan: Real-Time Job Progress & Live Log Streaming (ft-05)

## 1. Problem Statement & Motivation
Background tasks often execute long-running operations (file imports, data syncing, shell commands, batch processing) that can take seconds or minutes. Currently, jobs run as black boxes: the system only records static logs at state transitions (enqueued, started, completed, failed), and subprocess tasks buffer all stdout/stderr until completion. Users and API consumers have no visibility into intermediate progress percent (e.g. 45%) or live output streams.

This feature introduces a first-class `TaskContext` for cooperative progress reporting (0–100% with status message) and real-time streaming of stdout/stderr logs over Redis Pub/Sub and WebSockets to the Linear Dark dashboard.

## 2. Scope & Boundaries
- **In Scope**:
  - `Job` model extensions: `progress: float` (0.0 to 100.0) and `progress_message: str | None`.
  - `TaskContext` runtime context injectable into tasks for `await ctx.update_progress(percent, message)` and `await ctx.append_log(line)`.
  - Automatic dependency injection of `TaskContext` into worker task invocations.
  - Subprocess live streaming in `system.run_command` via asynchronous line-by-line stdout/stderr consumption.
  - Redis broker primitives for atomic progress update and live log appending.
  - WebSocket telemetry broadcasting of `job:progress` and `job:log` events.
  - Linear Dark UI updates: animated progress bars in History table, real-time log append in Loki viewer, and progress indicators in LGTM trace modal.
- **Out of Scope**:
  - Binary streaming / audio-video WebRTC transport (text/json only).
  - Terminal interactive stdin input emulation.

## 3. High-Level Approach
1. **Core Domain**: Extend `Job` with `progress` and `progress_message`. Provide `TaskContext` with async helpers `update_progress` and `append_log`.
2. **Broker & Events**: Add `update_job_progress` and `append_job_log` to `RedisBroker` with `job:progress` and `job:log` pub/sub events.
3. **Worker Runtime**: Update `Worker._process_job` to introspect signatures and inject `TaskContext`.
4. **Builtin Tasks**: Update `run_command` in `builtin_tasks.py` to stream subprocess stdout/stderr line-by-line when `ctx` is supplied.
5. **Dashboard SPA**: Enhance `app.js`, `index.html`, and `styles.css` with live progress bars, real-time Loki log console appending, and event formatting.

## 4. Dependencies & Prerequisites
- Existing `fastapi`, `redis.asyncio`, `websockets`, `pydantic` v2.
- Zero external libraries required.

## 5. Architectural Decision Records (ADRs)
- Complements `0001-python-fastapi-redis-task-manager.md`.
