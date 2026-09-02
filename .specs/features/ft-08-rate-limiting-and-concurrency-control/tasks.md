# Task List: Rate Limiting & Concurrency Control (ft-08)

## Sequence Guidelines (MetaGPT SOP)
- **Strict Sequential Order**: Tasks must be executed top-to-bottom without reordering or cherry-picking.
- **Atomic File Boundaries**: Each task must modify at most 1–3 specific target files.
- **Decoupled Test Setup**: Test definition / scaffolding tasks (`Type: test`) MUST precede implementation tasks (`Type: feat`).
- **Sensor Evidence Gate**: Mark complete `[x]` ONLY after passing build, lint, and test sensors with recorded evidence.

## Implementation Tasks

| Status | ID | Type | Description | Target Files | Dependencies | Evidence |
|---|---|---|---|---|---|---|
| [x] | TASK-01 | test | Scaffold unit tests for rate limit parser, token bucket limiter, concurrency semaphore, and worker retry-after interception | `tests/test_limiter.py` | None | `pytest tests/test_limiter.py` (5/5 passed) |
| [x] | TASK-02 | feat | Implement RateLimitSpec, parse_rate_limit, TokenBucketLimiter, and ConcurrencyLimiter in Redis | `taskmanager/core/limiter.py` | TASK-01 | RateLimitSpec and Redis Token Bucket / Semaphore passing |
| [x] | TASK-03 | feat | Add rate_limit and max_concurrency fields to Task model and @task decorator with validation | `taskmanager/core/task.py` | TASK-02 | `@task` decorator validation tests passing |
| [x] | TASK-04 | feat | Wire TokenBucketLimiter and ConcurrencyLimiter checks with graceful delayed rescheduling in Worker runtime | `taskmanager/worker/worker.py` | TASK-03 | Worker delayed retry-after rescheduling verified |
| [x] | TASK-05 | feat | Render rate limit and concurrency badges in Dashboard Tasks table and Command Palette | `taskmanager/ui/index.html`, `taskmanager/ui/styles.css`, `taskmanager/ui/app.js` | TASK-04 | Tasks table rendering badges for `⚡ rate_limit` and `🔒 max_concurrency` |
| [x] | TASK-06 | feat | Update taskmanager/example_tasks.py with comprehensive showcases for progress, logs, rate limits, concurrency, and subprocesses | `taskmanager/example_tasks.py` | TASK-05 | example_tasks.py updated with complete real-world task showcases |
| [x] | TASK-07 | feat | Bump package version to 0.3.0 in pyproject.toml and taskmanager/__init__.py, and update README.md documentation | `pyproject.toml`, `taskmanager/__init__.py`, `README.md` | TASK-06 | Version 0.3.0 bumped and README.md refreshed |
| [x] | TASK-08 | review | Run full sensor verification suite (ruff lint, pytest 100% pass, zero spec drift) | `taskmanager/`, `tests/`, `samples/` | TASK-07 | `ruff check` (0 errors), `pytest` (42/42 passed in 2.94s) |

## Schema Dictionary
- **Status**: `[ ]` (Pending) | `[x]` (Verified Complete).
- **ID**: `TASK-01` through `TASK-08`.
- **Type**: `test` | `feat` | `fix` | `refactor` | `docs` | `rules` | `skill` | `review`.
- **Target Files**: Concrete comma-separated file paths (relative to workspace root).
- **Dependencies**: Comma-separated list of preceding task IDs or `None`.
- **Evidence**: Commit hash (`git rev-parse --short HEAD`) + sensor output snippet.
