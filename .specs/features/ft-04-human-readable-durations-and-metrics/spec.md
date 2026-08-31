# Feature Specification: Human-Readable Durations & Observability Metrics (ft-04)

## 1. Domain Requirements & Invariants

- **FR-01**: The system must provide a helper function `formatDuration(ms, options)` in JavaScript to format any millisecond duration into human-readable representation:
  - `< 1000ms`: displayed in milliseconds (e.g., `45.2 ms` or `450 ms`).
  - `1000ms <= ms < 60000ms`: displayed in seconds with millisecond decimal precision (e.g., `2.50s` or `45.10s`). If `includeExact` is enabled, append exact ms `(2500.0ms)`.
  - `60000ms <= ms < 3600000ms`: displayed in minutes and seconds (e.g., `2m 32.5s` or `15m 04s`). If `includeExact` is enabled, append exact ms `(152503.0ms)`.
  - `>= 3600000ms`: displayed in hours, minutes, and seconds (e.g., `1h 14m 20s`). If `includeExact` is enabled, append exact ms.
- **FR-02**: Tempo Trace Timeline step "Finalizado" and "Falhou" must use `formatDuration` with exact ms preservation (e.g., `Concluído com sucesso em 2m 32.5s (152503.0ms)` or `Erro: Timeout (Duração: 2m 32.5s [152503.0ms])`).
- **FR-03**: Observability KPI metric cards (`obs-avg-duration`, `obs-p95-duration`) must show human-readable primary values (e.g., `2m 32s` or `3.50s` or `150.0ms`) and display exact millisecond telemetry in the subtitle/tooltip (`152503.0 ms — Média de execução`).
- **FR-04**: Execution History table (`#history-table`) `Duração` column must display the smart human-readable value with a secondary subtle line showing the raw milliseconds (e.g., `2m 32.5s` on top and `152503.0 ms` below in `var(--ink-subtle)`).
- **FR-05**: Real-time WebSocket event logs for `job:completed` must format the duration human-readably (e.g., `(2m 32.5s)`).
- **FR-06**: All changes must strictly follow `DESIGN.md` Linear Dark design tokens, typography, and contrast rules.

## 2. Acceptance Criteria (BDD)

### AC-01: Millisecond Range Formatting (< 1000ms)
- **Given** a job with duration `0.0452` seconds (`45.2ms`)
- **When** `formatDuration(45.2)` is executed
- **Then** it returns `"45.2 ms"`.

### AC-02: Seconds Range Formatting (1s to 60s)
- **Given** a job with duration `3.45` seconds (`3450ms`)
- **When** `formatDuration(3450, { includeExact: true })` is executed
- **Then** it returns `"3.45s (3450.0ms)"` (or `"3.45s"` in compact mode).

### AC-03: Minutes Range Formatting (1m to 60m)
- **Given** a job with duration `152.503` seconds (`152503.0ms`)
- **When** `formatDuration(152503.0, { includeExact: true })` is executed
- **Then** it returns `"2m 32.5s (152503.0ms)"` (or `"2m 32s"` in compact mode).

### AC-04: Hours Range Formatting (>= 1h)
- **Given** a job with duration `4500.0` seconds (`4500000ms` / 1h 15m)
- **When** `formatDuration(4500000, { includeExact: true })` is executed
- **Then** it returns `"1h 15m 00s (4500000.0ms)"`.

### AC-05: Edge cases & Null Handling
- **Given** a duration that is `null`, `undefined`, or `0`
- **When** `formatDuration(val)` is executed
- **Then** it returns `"0.0 ms"` or `"--"` gracefully without exceptions.

### AC-06: Tempo Trace Timeline Integration
- **Given** a finished job with duration `152.503` seconds
- **When** the LGTM Trace Modal is opened
- **Then** the timeline step displays `"Concluído com sucesso em 2m 32.5s (152503.0ms)"`.
