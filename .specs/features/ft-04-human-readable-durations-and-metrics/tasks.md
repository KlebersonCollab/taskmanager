# Tasks: Human-Readable Durations & Observability Metrics (ft-04)

| Status | ID | Type | Description | Target Files | Dependencies | Evidence |
|---|---|---|---|---|---|---|
| [x] | TASK-01 | feat | Implement `formatDuration` helper in `app.js` handling ms, sec, min, hour formatting with compact and detailed modes | `taskmanager/ui/app.js` | None | `5bdce31` Node test pass |
| [x] | TASK-02 | feat | Integrate `formatDuration` into Tempo Trace Timeline in LGTM Job Modal | `taskmanager/ui/app.js` | TASK-01 | `5bdce31` Spec drift pass |
| [x] | TASK-03 | feat | Integrate `formatDuration` into Observability KPI cards and History Table rows | `taskmanager/ui/app.js`, `taskmanager/ui/index.html` | TASK-01 | `5bdce31` Spec drift pass |
| [x] | TASK-04 | feat | Update WebSocket live event handlers to format duration human-readably | `taskmanager/ui/app.js` | TASK-01 | `5bdce31` Spec drift pass |
| [x] | TASK-05 | test | Verify all pytest tests and ensure UI static assets build and work seamlessly | `tests/test_api.py`, `tests/test_core.py` | TASK-01, TASK-02, TASK-03, TASK-04 | `5bdce31` Pytest 27/27 pass |
