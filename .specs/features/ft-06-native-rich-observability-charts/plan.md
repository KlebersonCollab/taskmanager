# Plan: Native Rich Observability Dashboards & Time-Series Charts (ft-06)

## 1. Problem Statement & Motivation
Users need deep operational visibility into background task performance (throughput over time, latency distribution, failure heatmaps, task volume breakdown) without the operational burden, resource overhead, or complexity of setting up external monitoring stacks like Prometheus, Grafana, or OpenTelemetry collectors.

This feature implements a self-contained, native observability suite directly in TaskManager: aggregating time-series metrics from Redis execution history and rendering interactive, lightweight Canvas/SVG throughput and latency distribution charts in the Linear Dark dashboard with zero external dependencies.

## 2. Scope & Boundaries
- **In Scope**:
  - Redis time-series and distribution aggregations in `RedisBroker` (1-min/5-min throughput buckets, latency histogram buckets, P50/P75/P90/P95/P99 percentiles, and per-task performance breakdown).
  - Dedicated REST endpoint `GET /api/metrics/timeseries` supporting customizable time windows (15m, 30m, 1h, 24h).
  - Lightweight Canvas/SVG interactive chart components in `app.js` with hover tooltips, smooth area fills, and grid lines conforming to `DESIGN.md`.
  - Latency distribution histogram and Top Tasks performance ranking table in the History & Observability tab.
  - Live auto-refresh synchronized with WebSocket events.
- **Out of Scope**:
  - Multi-year long-term cold storage analytics (focused on operational window: recent 15m to 24h).
  - External Grafana plugin packaging.

## 3. High-Level Approach
1. **Broker Aggregation**: Build `get_timeseries_metrics(window_minutes)` in `RedisBroker` extracting completed/failed timestamps and durations from `tm:jobs:history`.
2. **API Endpoint**: Expose `GET /api/metrics/timeseries` in `api/app.py`.
3. **Canvas/SVG Charting Engine**: Implement lightweight pure-JS rendering routines in `app.js` for throughput area chart and latency histogram without third-party chart libraries.
4. **UI Layout**: Update `index.html` and `styles.css` with a responsive two-column observability grid in `tab-history`.

## 4. Dependencies & Prerequisites
- Existing `RedisBroker`, `JobStatus`, FastAPI, and Linear Dark design system tokens.
- Zero external charting or server dependencies.

## 5. Architectural Decision Records (ADRs)
- Complements `0001-python-fastapi-redis-task-manager.md` (Native Zero-Dependency Observability).
