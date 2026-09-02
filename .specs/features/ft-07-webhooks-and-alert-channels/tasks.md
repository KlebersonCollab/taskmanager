# Task List: Webhooks & Multi-Platform Alert Channels (ft-07)

## Sequence Guidelines (MetaGPT SOP)
- **Strict Sequential Order**: Tasks must be executed top-to-bottom without reordering or cherry-picking.
- **Atomic File Boundaries**: Each task must modify at most 1–3 specific target files.
- **Decoupled Test Setup**: Test definition / scaffolding tasks (`Type: test`) MUST precede implementation tasks (`Type: feat`).
- **Sensor Evidence Gate**: Mark complete `[x]` ONLY after passing build, lint, and test sensors with recorded evidence.

## Implementation Tasks

| Status | ID | Type | Description | Target Files | Dependencies | Evidence |
|---|---|---|---|---|---|---|
| [x] | TASK-01 | test | Scaffold unit tests for AlertChannel model, multi-platform formatters (Slack, Discord, Teams, Telegram, Webhook), and async dispatcher | `tests/test_alerts.py` | None | `pytest tests/test_alerts.py` (4/4 passed) |
| [x] | TASK-02 | feat | Create AlertChannel model and ChannelType enum with platform configuration fields and event subscriptions | `taskmanager/alerts/channel.py`, `taskmanager/alerts/__init__.py` | TASK-01 | Unit models validated for Slack, Discord, Teams, Telegram, Webhook |
| [x] | TASK-03 | feat | Implement multi-platform payload formatters and fail-safe async HTTP dispatcher for Slack, Discord, Teams, Telegram, and Webhooks | `taskmanager/alerts/dispatcher.py` | TASK-02 | Formatter unit tests passing |
| [x] | TASK-04 | feat | Implement Alert Channels CRUD in RedisBroker and wire automatic alert dispatching on job failure (DLQ) | `taskmanager/core/broker.py` | TASK-03 | Broker CRUD & DLQ auto-dispatch tests passing |
| [x] | TASK-05 | feat | Expose Alert Channels CRUD REST endpoints and test ping endpoint in FastAPI application | `taskmanager/api/app.py` | TASK-04 | API CRUD & test ping endpoints verified |
| [x] | TASK-06 | feat | Add Alert Channels management modal, platform badge rendering, test ping trigger, and styles in Dashboard | `taskmanager/ui/index.html`, `taskmanager/ui/styles.css`, `taskmanager/ui/app.js` | TASK-05 | UI modal, platform selector & dynamic badge rendering complete |
| [x] | TASK-07 | test | Add integration tests for Alert Channels REST API and test dispatching | `tests/test_api.py` | TASK-06 | `pytest tests/test_api.py::test_api_alert_channels_crud_and_test_dispatch` passed |
| [x] | TASK-08 | review | Run full sensor verification suite (ruff lint, pytest 100% pass, zero spec drift) | `taskmanager/`, `tests/` | TASK-07 | `ruff check` (0 errors), `pytest` (37/37 passed in 2.97s) |

## Schema Dictionary
- **Status**: `[ ]` (Pending) | `[x]` (Verified Complete).
- **ID**: `TASK-01` through `TASK-08`.
- **Type**: `test` | `feat` | `fix` | `refactor` | `docs` | `rules` | `skill` | `review`.
- **Target Files**: Concrete comma-separated file paths (relative to workspace root).
- **Dependencies**: Comma-separated list of preceding task IDs or `None`.
- **Evidence**: Commit hash (`git rev-parse --short HEAD`) + sensor output snippet.
