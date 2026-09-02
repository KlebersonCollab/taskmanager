# Specification: Real-Time Job Progress & Live Log Streaming (ft-05)

## 1. User Stories
- **US-1**: As a developer running a long background task, I want to report real-time percentage progress and current status message from inside my task function, so that consumers can track task execution state live.
- **US-2**: As an operations engineer running shell scripts and database backups via `system.run_command`, I want to see log output streaming live line-by-line in the dashboard console, so that I don't have to wait for the entire job to finish to diagnose issues.
- **US-3**: As a dashboard user, I want to see visual progress bars and live log stream updates via WebSockets without manual page refresh, so that I have immediate visibility into active jobs.

## 2. Business Rules & Invariants
- **BR-1**: Progress values must always be clamped between `0.0` and `100.0`.
- **BR-2**: When a job completes with status `COMPLETED`, its final progress is recorded as `100.0` unless explicitly overridden.
- **BR-3**: Calling `ctx.update_progress()` or `ctx.append_log()` must atomically update the Redis job record and broadcast an event (`job:progress` or `job:log`) without interrupting or blocking the task execution flow.
- **BR-4**: If a task does not accept `ctx`, the worker executes the task normally without error (full backward compatibility).
- **BR-5**: UI progress bars and Loki log consoles must strictly comply with `DESIGN.md` tokens (Linear Dark `#5e6ad2` primary accent, dark canvas `#010102`, hairline borders).

## 3. Acceptance Criteria (BDD)

### Happy Path (Success Scenarios)
- **AC-1: TaskContext Progress Reporting**
  - **Given** an async task function accepting `ctx: TaskContext`
  - **When** the task calls `await ctx.update_progress(50.0, "Halfway done")`
  - **Then** the job in Redis has `progress=50.0` and `progress_message="Halfway done"`, and a `job:progress` event is emitted.

- **AC-2: TaskContext Live Log Appending**
  - **Given** an active job executing in a worker
  - **When** the task calls `await ctx.append_log("Processing item #42")`
  - **Then** the line is appended to `job.logs` in Redis and a `job:log` event with `{"job_id": ..., "line": ...}` is broadcasted.

- **AC-3: Subprocess Real-Time Line-by-Line Streaming**
  - **Given** `system.run_command` executing a multi-step command
  - **When** the subprocess prints lines to stdout/stderr
  - **Then** each line is read as soon as it is emitted and streamed via `ctx.append_log`, appearing incrementally before process termination.

### Input & Validation Scenarios
- **AC-4: Clamping Out-of-Bounds Progress**
  - **Given** a task calls `await ctx.update_progress(150.0)` or `await ctx.update_progress(-20.0)`
  - **When** the update is processed
  - **Then** `progress` is clamped to `100.0` and `0.0` respectively without throwing an error.

### Edge Cases & Exceptions (Resilience)
- **AC-5: Backward Compatibility for Tasks without TaskContext**
  - **Given** a legacy task function `async def my_task(x: int, y: int)` without `ctx`
  - **When** the worker processes the job
  - **Then** the task executes successfully, ignoring context injection, and completes with status `COMPLETED`.

- **AC-6: UI Real-Time Updates**
  - **Given** a connected dashboard client on the History tab or Job Trace Modal
  - **When** a `job:progress` or `job:log` WebSocket message is received
  - **Then** the active row progress bar and the Loki log console dynamically update without reloading the page.

## 4. Test Data & Boundary Matrix
| Parameter / Field | Valid Inputs (Happy) | Invalid / Boundary Inputs (Edge) | Clamped / Resolved Output |
|---|---|---|---|
| `progress` | `0.0`, `50.5`, `100.0` | `-10.0`, `125.0`, `float('nan')` | `0.0`, `100.0`, `0.0` |
| `progress_message` | `"Processando 10/20"`, `""` | `None`, `12345` | `"Processando 10/20"`, `""`, `None`, `"12345"` |
| `line` (append_log) | `"Linha de log normal"` | `""`, multiline string | Formatted log entry |

## 5. Verification Sensors
| Sensor | Command / Target | Success Threshold |
|---|---|---|
| Linter | `uv run ruff check taskmanager tests` | 0 errors |
| Test Suite | `uv run pytest` | 100% pass (all unit, worker, api tests passing) |
| Spec Drift | `node .agents/scripts/check-spec-drift.js` | 0 drift violations |

## 6. UI & Design System Tokens
- Progress Bar Fill: `var(--brand-primary, #5e6ad2)` with subtle transition `width 0.3s cubic-bezier(0.16, 1, 0.3, 1)`.
- Progress Bar Track: `background: rgba(255, 255, 255, 0.08); border-radius: var(--radius-sm)`.
- Status Message: `font-size: 11px; color: var(--ink-secondary); font-family: var(--font-sans)`.
