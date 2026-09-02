# Project State & Context

## 🏁 Session Status
- **Current Task**: Completed Feature `ft-08-rate-limiting-and-concurrency-control` (Distributed Token Bucket in Redis and cluster-wide max concurrency semaphore, bumped to v0.3.0).
- **Progress**: 100% of ft-01 through ft-08 tasks verified (42/42 tests passing, ruff clean, zero spec drift).
- **Next Steps**:
  - All requested architectural features and polish complete.

## 💡 Decisions Log
- **2026-09-01 - Distributed Rate Limiting & Concurrency Control**: Implemented `TokenBucketLimiter` with human-readable syntax (`"10/s"`, `"100/m"`, `"1000/h"`, `"5000/d"`) and `ConcurrencyLimiter` semaphore in Redis. Workers intercept limits and gracefully reschedule jobs into delayed zset without failing jobs or consuming retries. Bumped to v0.3.0.
- **2026-09-01 - Multi-Platform Webhook & Alert Engine**: Implemented `AlertChannel` with platform-specific payload formatters for Slack (attachments/blocks), Discord (rich embeds), Microsoft Teams (MessageCard/Connector), Telegram (Markdown bot API), and generic HTTP Webhooks with secret bearer authentication. Dispatches alerts asynchronously upon job failure and DLQ routing.
- **2026-09-01 - Native Observability & Canvas Time-Series**: Implemented zero-external-dependency time-series metrics (`GET /api/metrics/timeseries`) with throughput buckets (completed/failed area curves), latency histogram, P50/P90/P95/P99 percentiles, and per-task breakdown ranking, rendered via pure DPI-scaled HTML5 Canvas adhering to Linear Dark design system.
- **2026-09-01 - Native Observability & Canvas Time-Series**: Implemented zero-external-dependency time-series metrics (`GET /api/metrics/timeseries`) with throughput buckets (completed/failed area curves), latency histogram, P50/P90/P95/P99 percentiles, and per-task breakdown ranking, rendered via pure DPI-scaled HTML5 Canvas adhering to Linear Dark design system.
- **2026-09-01 - Real-Time Job Progress & Live Log Streaming**: Implemented `TaskContext` with `update_progress` and `append_log`, auto-injected into worker tasks. Subprocess `system.run_command` streams `stdout`/`stderr` line-by-line via async StreamReader. Linear Dark dashboard updates animated progress bars in History table and streams live logs directly into Loki modal.
- **2026-08-31 - Human-Readable Durations & Observability Metrics**: Implemented smart multi-scale duration conversion (`formatDuration`) across trace timelines, KPI cards, and history tables, ensuring large durations (seconds, minutes, hours) are intuitively parsed at a glance while retaining exact millisecond precision in detailed telemetry.
- **2026-08-31 - Human-Readable Durations & Observability Metrics**: Implemented smart multi-scale duration conversion (`formatDuration`) across trace timelines, KPI cards, and history tables, ensuring large durations (seconds, minutes, hours) are intuitively parsed at a glance while retaining exact millisecond precision in detailed telemetry.
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


