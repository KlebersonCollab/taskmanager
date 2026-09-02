# Specification: Native Rich Observability Dashboards & Time-Series Charts (ft-06)

## 1. User Stories
- **US-1**: As an operator or developer, I want to see a live time-series chart of job throughput (executions/min, success vs failed) in the dashboard, so that I can detect traffic spikes and error patterns over time.
- **US-2**: As an engineer optimizing task performance, I want to inspect a latency histogram and multi-tier percentiles (P50, P75, P90, P95, P99), so that I can identify long-tail outliers without configuring Prometheus/Grafana.
- **US-3**: As a system administrator, I want to see a breakdown of executions, success rates, and average durations grouped by task name, so that I can immediately spot which background tasks are failing or consuming the most time.

## 2. Business Rules & Invariants
- **BR-1**: Metrics must be computed strictly on-demand or cached efficiently from Redis execution history, without requiring external database processes.
- **BR-2**: Time-series buckets must divide the requested time window (e.g. 30 minutes) into equal intervals (e.g. 1-minute slices) ordered chronologically from oldest to newest.
- **BR-3**: Latency percentiles (P50, P75, P90, P95, P99) must be mathematically accurate based on sorted duration arrays.
- **BR-4**: The UI charts must be rendered using pure native Canvas/SVG without third-party CDN scripts, maintaining 100% offline capability and strict compliance with `DESIGN.md` tokens.

## 3. Acceptance Criteria (BDD)

### Happy Path (Success Scenarios)
- **AC-1: Time-Series Metrics Calculation**
  - **Given** completed and failed jobs recorded in Redis history
  - **When** `GET /api/metrics/timeseries?window_minutes=30` is requested
  - **Then** the response returns `throughput_series` with chronological time buckets, `latency_histogram` buckets, `latency_percentiles` (P50, P75, P90, P95, P99), and `task_breakdown`.

- **AC-2: Canvas Throughput Chart Rendering**
  - **Given** the user navigates to the "📊 Execuções & Métricas" tab
  - **When** the time-series data loads
  - **Then** an interactive Canvas chart renders with completed and failed area curves, hairline grid, time labels, and tooltip on hover.

- **AC-3: Latency Histogram & Task Breakdown Table**
  - **Given** time-series metrics loaded in the UI
  - **When** viewing the latency card and task breakdown table
  - **Then** distribution bars reflect exact percentages for `<50ms`, `50-200ms`, `200-500ms`, `500ms-1s`, `1s-5s`, `>5s`, and each task displays total runs, success rate %, and average duration.

### Input & Validation Scenarios
- **AC-4: Time Window Parameter Clamping**
  - **Given** a request to `/api/metrics/timeseries` with invalid or negative `window_minutes` (e.g. `-5` or `0` or `100000`)
  - **When** the endpoint processes the request
  - **Then** `window_minutes` is clamped to valid boundaries (`5` to `1440` minutes) with default `30`.

### Edge Cases & Exceptions (Resilience)
- **AC-5: Zero Executions State**
  - **Given** an empty Redis history (no executions yet)
  - **When** `/api/metrics/timeseries` is fetched and rendered in the dashboard
  - **Then** the endpoint returns zeroed arrays without error, and charts render a clean, subtle "Sem execuções no período" state.

## 4. Test Data & Boundary Matrix
| Window Minutes | Bucket Interval | Total Buckets |
|---|---|---|
| `15` | 1 min | 15 buckets |
| `30` | 1 min | 30 buckets |
| `60` (1h) | 2 min | 30 buckets |
| `1440` (24h) | 30 min | 48 buckets |

## 5. Verification Sensors
| Sensor | Command / Target | Success Threshold |
|---|---|---|
| Linter | `uv run ruff check taskmanager tests` | 0 errors |
| Test Suite | `uv run pytest` | 100% pass |
| Spec Drift | `node .agents/scripts/check-spec-drift.js` | 0 drift violations |

## 6. UI & Design System Tokens
- Area Fill Completed: `rgba(94, 106, 210, 0.18)` gradient to `rgba(94, 106, 210, 0.0)`.
- Line Stroke Completed: `var(--brand-primary, #5e6ad2)` (2px width).
- Area Fill Failed: `rgba(239, 68, 68, 0.25)`.
- Line Stroke Failed: `var(--semantic-error, #ef4444)`.
- Grid Lines: `var(--hairline, rgba(255, 255, 255, 0.08))`.
- Font: `var(--font-mono)` for metrics and time labels.
