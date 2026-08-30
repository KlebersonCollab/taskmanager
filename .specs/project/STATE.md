# Project State & Context

## 🏁 Session Status
- **Current Task**: Completed Feature `ft-01-taskmanager-core` (MVP Core Engine, Worker Runtime, Cron Scheduler, REST/WebSocket API, Linear Dark SPA Dashboard, Dynamic Worker Spawner, and Redis Maintenance Flush)
- **Progress**: 100% of Milestone 1–5 core MVP tasks verified (20/20 unit/integration tests passing).
- **Next Steps**:
  1. Production telemetry monitoring and multi-node scaling.
  2. Optional extensions (distributed worker cluster deployment via Docker Compose / Helm / Kubernetes).

## 💡 Decisions Log
- **2026-08-30 - Tech Stack**: Selected Python 3.11+ (FastAPI + Asyncio Worker runtime) with Redis broker and a minimalist SPA Frontend adhering to `DESIGN.md`.
- **2026-08-30 - Architecture Model**: Decoupled async Redis worker runtime with live heartbeat registration, dynamic cron scheduler with distributed locking, and WebSocket telemetry streaming.
- **2026-08-30 - In-App Toast System**: Eliminated all browser `alert()` and `confirm()` dialogs in favor of a modern Linear Dark Toast notification system.
- **2026-08-30 - In-App Worker Manager**: Enabled dynamic worker runtime spawning, pausing, resuming, and stopping directly from the Web UI with CPU/RAM backpressure guardrails.
- **2026-08-30 - Redis Maintenance**: Implemented atomic flush operations (Flush Queues, Flush History, Flush All) accessible via Web UI and REST API.
- **2026-08-30 - Windows Subprocess Encoding**: Enforced `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` on all subprocess executions to prevent `UnicodeEncodeError` with emojis on Windows.

## 🚧 Active Blockers
- None.

## ❄️ Deferred Ideas / Icebox
- Distributed multi-node clustering with Raft leader election for scheduler (Single-leader Redis lock used for MVP).
- Persistent PostgreSQL audit archiving for long-term historical analytics.

## ⚠️ Known Technical Debts
- None.

