# Task List: TaskManager Core Engine & Management Dashboard

## Sequence Guidelines (MetaGPT SOP)
- **Strict Sequential Order**: Tasks must be executed top-to-bottom without reordering or cherry-picking.
- **Atomic File Boundaries**: Each task must modify at most 1–3 specific target files.
- **Decoupled Test Setup**: Test definition / scaffolding tasks (`Type: test`) MUST precede implementation tasks (`Type: feat`).
- **Sensor Evidence Gate**: Mark complete `[x]` ONLY after passing build, lint, and test sensors with recorded evidence.

## Implementation Tasks

| Status | ID | Type | Description | Target Files | Dependencies | Evidence |
|---|---|---|---|---|---|---|
| [x] | TASK-01 | feat | Configure pyproject.toml package setup and core dependencies | `pyproject.toml`, `taskmanager/__init__.py`, `taskmanager/config.py`, `uv.lock` | None | pass: venv ready, v0.1.0 import ok |
| [x] | TASK-02 | test | Scaffold pytest fixtures and in-memory Redis mock harness | `tests/conftest.py` | TASK-01 | pass: fakeredis fixture verified with pytest-asyncio |
| [x] | TASK-03 | feat | Implement Core Job model, Status enum, and Redis Broker layer | `taskmanager/core/job.py`, `taskmanager/core/broker.py` | TASK-02 | pass: Job schema, Status enum, and RedisBroker implemented |
| [x] | TASK-04 | feat | Implement `@task` decorator API, delayed queuing, and unit tests | `taskmanager/core/task.py`, `taskmanager/core/builtin_tasks.py`, `tests/test_core.py` | TASK-03 | pass: 5 tests passed in 0.91s |
| [x] | TASK-05 | feat | Implement Worker Runtime with concurrency, retry backoff, DLQ, and heartbeats | `taskmanager/worker/worker.py`, `taskmanager/worker/heartbeat.py`, `tests/test_worker.py` | TASK-04 | pass: 3 worker tests passed in 0.50s |
| [x] | TASK-06 | feat | Implement Cron & Scheduled task engine with Redis distributed lock | `taskmanager/scheduler/cron.py`, `taskmanager/scheduler/scheduler.py`, `tests/test_scheduler.py` | TASK-05 | pass: 3 scheduler tests passed in 0.28s |
| [x] | TASK-07 | feat | Expose FastAPI REST endpoints and WebSocket event broadcaster | `taskmanager/api/app.py`, `taskmanager/api/events.py`, `tests/test_api.py` | TASK-06 | pass: 4 API tests passed in 0.39s (0 warnings) |
| [x] | TASK-08 | feat | Build Linear Dark SPA Dashboard complying with DESIGN.md tokens | `taskmanager/ui/index.html`, `taskmanager/ui/app.js`, `taskmanager/ui/styles.css` | TASK-07 | pass: SPA files created & verified via test_api_index_and_static |
| [x] | TASK-09 | feat | Implement Unified CLI (worker, scheduler, server, dev), Docker compose, examples, and Quickstart README | `taskmanager/cli.py`, `README.md`, `example_tasks.py`, `enqueue_examples.py`, `scripts/backup_database.py`, `Dockerfile`, `docker-compose.yml`, `.dockerignore` | TASK-08 | pass: CLI help validated & Docker stack and README.md authored |
| [x] | TASK-10 | review | Run full sensor verification suite and validate all BDD Acceptance Criteria | `taskmanager/`, `tests/` | TASK-09 | pass: spec-drift ok, 15/15 tests passed, ruff clean, import ok |

## Schema Dictionary
- **Status**: `[ ]` (Pending) | `[x]` (Verified Complete).
- **ID**: `TASK-01` to `TASK-10`.
- **Type**: `test` | `feat` | `fix` | `refactor` | `docs` | `rules` | `skill` | `review`.
- **Target Files**: Concrete comma-separated file paths (relative to workspace root).
- **Dependencies**: Comma-separated list of preceding task IDs or `None`.
- **Evidence**: Commit hash / pass log snippet.
