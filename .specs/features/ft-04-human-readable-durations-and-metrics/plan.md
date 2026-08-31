# Feature Plan: Human-Readable Durations & Observability Metrics (ft-04)

## 1. Problem Statement
In the Execution History and Observability pages, as well as the Tempo Trace Timeline modal, execution durations are currently displayed purely as raw millisecond or second numbers (e.g., `152503.0ms`). As task runtimes increase into dozens of seconds, minutes, or hours, raw millisecond representations become difficult for developers to quickly comprehend.

## 2. Goals & Scope
- **Human-Readable Formatting**: Convert duration values dynamically into appropriate units (milliseconds, seconds, minutes, hours) based on magnitude while retaining exact millisecond precision for auditing and diagnostics.
- **Trace Timeline Enhancement**: Update the Tempo Trace Timeline in the Job Details modal so completion and error duration displays are intuitive (e.g., `2m 32.5s (152503.0ms)`).
- **Observability Metric Cards**: Display human-readable primary values in `Duração Média` and `P95 Latência` KPI cards, paired with exact millisecond precision in the subtext/tooltip.
- **Execution History Table**: Render human-readable duration strings with two-line layout (or tooltip) showing the clean unit alongside the raw millisecond value according to `DESIGN.md` guidelines.
- **WebSocket Live Event Feed**: Format real-time job completion events with readable time scales.

## 3. High-Level Strategy
1. Introduce a robust, edge-case tested `formatDuration(ms, options)` JavaScript helper function supporting compact and verbose/precision modes.
2. Update `taskmanager/ui/app.js` to format durations in:
   - Observability KPI metric cards (`obs-avg-duration`, `obs-p95-duration`).
   - History table rows (`#history-table`).
   - Tempo Trace Timeline (`#lgtm-trace-timeline`).
   - Real-time WebSocket event logs (`handleLiveEvent`).
3. Update `taskmanager/ui/index.html` card labels to `Duração Média` and `P95 Latência` with flexible unit display.
4. Verify non-regression across test suite and validate UI rendering.
