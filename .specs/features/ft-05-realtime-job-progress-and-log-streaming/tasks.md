# Task List: Real-Time Job Progress & Live Log Streaming (ft-05)

## Sequence Guidelines (MetaGPT SOP)
- **Strict Sequential Order**: Tasks must be executed top-to-bottom without reordering or cherry-picking.
- **Atomic File Boundaries**: Each task must modify at most 1–3 specific target files.
- **Decoupled Test Setup**: Test definition / scaffolding tasks (`Type: test`) MUST precede implementation tasks (`Type: feat`).
- **Sensor Evidence Gate**: Mark complete `[x]` ONLY after passing build, lint, and test sensors with recorded evidence.

## Implementation Tasks

| Status | ID | Type | Description | Target Files | Dependencies | Evidence |
|---|---|---|---|---|---|---|
| [x] | TASK-01 | test | Scaffold unit tests for Job progress fields, TaskContext updates, and broker progress/log events | `tests/test_core.py`, `tests/test_worker.py` | None | `pytest` red verification pass on test_job_progress and test_worker_task_context |
| [x] | TASK-02 | feat | Extend Job model with progress and progress_message; implement broker atomic progress update and log append with event publishing | `taskmanager/core/job.py`, `taskmanager/core/broker.py` | TASK-01 | `pytest tests/test_core.py` (6/6 passed) |
| [x] | TASK-03 | feat | Define TaskContext and implement dynamic context introspection and injection in Worker job processor | `taskmanager/core/task.py`, `taskmanager/worker/worker.py` | TASK-02 | `pytest tests/test_worker.py` (5/5 passed) |
| [x] | TASK-04 | feat | Update system.run_command and run_script in builtin_tasks to stream subprocess stdout/stderr line-by-line via TaskContext | `taskmanager/core/builtin_tasks.py` | TASK-03 | `pytest tests/test_core.py` (6/6 passed) |
| [x] | TASK-05 | feat | Expose WebSocket broadcasting for job:progress and job:log events in events manager and verify API responses | `taskmanager/api/events.py`, `taskmanager/api/app.py` | TASK-04 | `pytest tests/test_api.py` (10/10 passed) |
| [x] | TASK-06 | feat | Update Dashboard UI (styles, templates, app controller) with animated progress bars, live Loki log stream appending, and trace progress header | `taskmanager/ui/app.js`, `taskmanager/ui/index.html`, `taskmanager/ui/styles.css` | TASK-05 | `ruff` clean, UI rendered with progress column & trace progress card |
| [x] | TASK-07 | test | Add integration tests for end-to-end task progress tracking, WebSocket event broadcast, and subprocess streaming | `tests/test_api.py` | TASK-06 | `pytest tests/test_api.py::test_api_job_progress_and_live_events` passed |
| [x] | TASK-08 | review | Run full sensor verification suite (ruff lint, pytest 100% pass, zero spec drift) | `taskmanager/`, `tests/` | TASK-07 | `ruff check` (0 errors), `pytest` (30/30 passed in 2.75s) |

## Schema Dictionary
- **Status**: `[ ]` (Pending) | `[x]` (Verified Complete).
- **ID**: `TASK-01` through `TASK-08`.
- **Type**: `test` | `feat` | `fix` | `refactor` | `docs` | `rules` | `skill` | `review`.
- **Target Files**: Concrete comma-separated file paths (relative to workspace root).
- **Dependencies**: Comma-separated list of preceding task IDs or `None`.
- **Evidence**: Commit hash (`git rev-parse --short HEAD`) + sensor output snippet.
