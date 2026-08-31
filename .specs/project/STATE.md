# Project State & Context

## 🏁 Session Status
- **Current Task**: Completed Feature `ft-03-library-packaging-and-integrations` (Wheel package data for static SPA assets, `TaskManager` high-level class, `taskmanager.contrib.django` app & commands, FastAPI mount helper, subpath mount resilience in UI, sample reference projects in `samples/`, and updated `README.md`).
- **Progress**: 100% of ft-01, ft-02, and ft-03 tasks verified (27/27 tests passing, ruff clean, wheel build verified).
- **Next Steps**:
  1. Multi-node clustering / distributed scaling.
  2. PyPI publishing release pipeline.

## 💡 Decisions Log
- **2026-08-30 - UI Streamlining & Action Menu**: Replaced cluttered top navigation buttons with a single unified `+ Criar ▾` split dropdown and a discreet settings icon (`⚙️`) for Redis maintenance.
- **2026-08-30 - Queue Management**: Added explicit queue creation (`POST /api/queues`) and deletion (`DELETE /api/queues/{queue}`) with UI modal and instant Redis synchronization.
- **2026-08-30 - Linear Table Row Rhythm**: Replaced bulky table buttons with compact micro-action button groups (`.btn-action`) that reveal clean borders and hover highlights without cluttering dense tables.
- **2026-08-30 - Command Palette (`Ctrl+K`)**: Added keyboard-accessible command bar allowing instant navigation across tabs, modal triggers, and dynamic task enqueuing.
- **2026-08-30 - Tech Stack**: Selected Python 3.11+ (FastAPI + Asyncio Worker runtime) with Redis broker and a minimalist SPA Frontend adhering to `DESIGN.md`.
- **2026-08-30 - In-App Toast System**: Eliminated all browser `alert()` and `confirm()` dialogs in favor of a modern Linear Dark Toast notification system.

## 🚧 Active Blockers
- None.

## ❄️ Deferred Ideas / Icebox
- Distributed multi-node clustering with Raft leader election for scheduler (Single-leader Redis lock used for MVP).
- Persistent PostgreSQL audit archiving for long-term historical analytics.

## ⚠️ Known Technical Debts
- None.


