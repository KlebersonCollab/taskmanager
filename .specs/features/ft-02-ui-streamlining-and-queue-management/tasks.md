# Tasks: UI Streamlining & Queue Management (ft-02)

| Status | ID | Type | Description | Target Files | Dependencies | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [x] | TASK-01 | feat | Add `POST /api/queues` and `DELETE /api/queues/{queue}` endpoints with RedisBroker integration | `taskmanager/api/app.py`, `taskmanager/core/broker.py` | None | Verified in RedisBroker and FastAPI routes |
| [x] | TASK-02 | test | Add unit/integration tests for queue creation, deletion, and validation | `tests/test_api.py` | TASK-01 | Pytest 21/21 passed with multi-queue tests |
| [x] | TASK-03 | feat | Build unified `+ Criar ▾` Action Menu, `⚙️` settings trigger, and `+ Nova Fila` modal in index.html and app.js | `taskmanager/ui/index.html`, `taskmanager/ui/app.js` | TASK-01 | Dropdown and modal live |
| [x] | TASK-04 | feat | Refactor table row actions across Overview, Tasks, Schedules, DLQ, and Workers into Linear micro-icon groups with tooltips and hover-reveal CSS | `taskmanager/ui/app.js`, `taskmanager/ui/styles.css` | TASK-03 | Micro-icon action groups and hover CSS verified |
| [x] | TASK-05 | feat | Implement Command Palette (`Ctrl+K` / `⌘K`) with quick search for navigation, modal dispatch, and worker controls | `taskmanager/ui/index.html`, `taskmanager/ui/app.js`, `taskmanager/ui/styles.css` | TASK-04 | Keyboard shortcut and search actions active |
| [x] | TASK-06 | refactor | Full sensor audit (ruff linter, pytest suite, spec drift sensor) | `taskmanager/`, `tests/` | TASK-05 | 100% passing (pytest, ruff, spec-drift) |

