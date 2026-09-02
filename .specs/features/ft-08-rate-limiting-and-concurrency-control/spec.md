# Specification: Rate Limiting & Concurrency Control (ft-08)

## Acceptance Criteria (BDD)

### Scenario 1: Parse Rate Limit Specs
- **Given** rate limit strings `"10/s"`, `"100/m"`, `"1000/h"`, `"5000/d"`,
- **When** `parse_rate_limit(spec)` is executed,
- **Then** it must return `RateLimitSpec(rate=10, period=1.0)`, `RateLimitSpec(rate=100, period=60.0)`, etc.
- **And** invalid strings (e.g. `"invalid"`, `"-5/s"`, `"10/xyz"`) must raise `ValueError`.

### Scenario 2: Distributed Token Bucket Execution in Redis
- **Given** a task with rate limit `2/s` and capacity `2.0`,
- **When** 2 rapid acquire requests arrive within the same millisecond,
- **Then** both must return `allowed=True, retry_after=0.0`.
- **When** a 3rd rapid acquire arrives immediately without waiting,
- **Then** it must return `allowed=False, retry_after > 0.0` (approx `0.5s`).
- **When** time advances by `0.5s`,
- **Then** the next acquire must return `allowed=True`.

### Scenario 3: Distributed Concurrency Semaphore
- **Given** a task with `max_concurrency=2`,
- **When** 2 concurrent workers acquire execution slots for this task,
- **Then** both acquisitions succeed.
- **When** a 3rd worker attempts to acquire a slot for the same task simultaneously,
- **Then** the acquisition fails (`acquired=False`), signaling the worker to delay the job.
- **When** one of the running workers finishes and releases its slot,
- **Then** subsequent slot acquisitions succeed.

### Scenario 4: Worker Job Execution Interception
- **Given** a worker dequeuing a job whose task has exceeded its rate limit,
- **When** the rate limit check fails,
- **Then** the job must be placed back into the delayed set with `delay=retry_after` without incrementing its `retry_count` or marking it as failed.

### Scenario 5: Dashboard UI Introspection & Badges
- **Given** registered tasks with `rate_limit` or `max_concurrency` defined,
- **When** the user views the "Filas & Tarefas" tab,
- **Then** the UI renders badges showing `⚡ 10/s` and `🔒 Max 2` next to task details.
