# Task List: Native Rich Observability Dashboards & Time-Series Charts (ft-06)

## Sequence Guidelines (MetaGPT SOP)
- **Strict Sequential Order**: Tasks must be executed top-to-bottom without reordering or cherry-picking.
- **Atomic File Boundaries**: Each task must modify at most 1–3 specific target files.
- **Decoupled Test Setup**: Test definition / scaffolding tasks (`Type: test`) MUST precede implementation tasks (`Type: feat`).
- **Sensor Evidence Gate**: Mark complete `[x]` ONLY after passing build, lint, and test sensors with recorded evidence.

## Implementation Tasks

| Status | ID | Type | Description | Target Files | Dependencies | Evidence |
|---|---|---|---|---|---|---|
| [x] | TASK-01 | test | Scaffold unit tests for broker timeseries metrics aggregation and API endpoint GET /api/metrics/timeseries | `tests/test_core.py`, `tests/test_api.py` | None | `pytest` red verification pass on test_broker_get_timeseries_metrics and test_api_timeseries_metrics_endpoint |
| [x] | TASK-02 | feat | Implement get_timeseries_metrics in RedisBroker with throughput time buckets, latency histogram, percentiles (P50..P99), and task breakdown | `taskmanager/core/broker.py` | TASK-01 | `pytest tests/test_core.py` (7/7 passed) |
| [x] | TASK-03 | feat | Expose GET /api/metrics/timeseries endpoint in FastAPI application with window_minutes clamping | `taskmanager/api/app.py` | TASK-02 | `pytest tests/test_api.py` (11/11 passed) |
| [x] | TASK-04 | feat | Add layout grid, Canvas chart containers, latency histogram bars, and time window switcher in UI templates and styles | `taskmanager/ui/index.html`, `taskmanager/ui/styles.css` | TASK-03 | HTML/CSS markup structured conforming to `DESIGN.md` |
| [x] | TASK-05 | feat | Implement native Canvas throughput area chart rendering, latency histogram updater, and task breakdown table in app.js | `taskmanager/ui/app.js` | TASK-04 | Native Canvas area chart and histogram rendered with DPI scaling |
| [x] | TASK-06 | test | Add integration tests for empty state, window parameter bounds, and live timeseries endpoint serialization | `tests/test_api.py` | TASK-05 | `pytest tests/test_api.py::test_api_timeseries_metrics_endpoint` passed with bounds tests |
| [x] | TASK-07 | review | Run full sensor verification suite (ruff lint, pytest 100% pass, zero spec drift) | `taskmanager/`, `tests/` | TASK-06 | `ruff check` (0 errors), `pytest` (32/32 passed in 2.78s) |

## Schema Dictionary
- **Status**: `[ ]` (Pending) | `[x]` (Verified Complete).
- **ID**: `TASK-01` through `TASK-07`.
- **Type**: `test` | `feat` | `fix` | `refactor` | `docs` | `rules` | `skill` | `review`.
- **Target Files**: Concrete comma-separated file paths (relative to workspace root).
- **Dependencies**: Comma-separated list of preceding task IDs or `None`.
- **Evidence**: Commit hash (`git rev-parse --short HEAD`) + sensor output snippet.
