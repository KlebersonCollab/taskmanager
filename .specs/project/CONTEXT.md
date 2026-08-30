# Domain Glossary & Context

## 1. Core Domain Concepts

- **Task**: A registered executable function/handler with a unique identifier and payload definition that can be invoked asynchronously.
- **Job**: An instance of a Task queued for execution with specific input arguments, priority, delay, unique execution ID, and lifecycle state (`pending`, `active`, `completed`, `failed`, `delayed`, `retrying`, `cancelled`).
- **Worker**: An independent process or thread instance that consumes jobs from specified queues, reports heartbeats periodically, and handles graceful pause, resume, and shutdown.
- **Queue**: A prioritized Redis data structure (FIFO / Priority heap) containing jobs waiting to be processed by workers.
- **Cron / Schedule**: A recurring or delayed job definition configured using standard cron expressions or intervals that automatically enqueues jobs into targeted queues.
- **Heartbeat**: A periodic TTL-based signal sent by an active worker to Redis to declare vitality, concurrency capacity, active jobs, and CPU/memory usage.
- **Dead Letter Queue (DLQ)**: A dedicated queue holding jobs that failed persistently after exhausting all configured retry attempts, preserving full stack trace and execution context for manual inspection or replay.
- **Exponential Backoff**: A retry strategy where delay between attempts grows exponentially with optional jitter to prevent thundering herd problems.
- **Broker**: The message transport and coordination store (Redis) managing state, job queues, lock primitives, and Pub/Sub event streams for real-time telemetry.

## 2. Invariants & Rules

1. **Job Immutability**: Once enqueued, job payload arguments cannot be mutated; execution results and error stack traces are appended as state metadata.
2. **Worker Liveness**: A worker without a heartbeat within 3x heartbeat interval (e.g. 15s) is declared `dead` (orphaned), and its active jobs are reclaimed or marked failed according to retry policy.
3. **At-Least-Once Delivery**: Jobs are held in an active set/hash with visibility timeout or ack confirmation until the worker successfully finishes or errors.
4. **Idempotency Support**: Jobs can optionally supply an idempotency key to prevent duplicate enqueueing within a given TTL window.
5. **Design System Adherence**: The UI dashboard strictly adheres to `DESIGN.md` (Linear Dark token palette `#010102`, `#0f1011`, `#5e6ad2`, precise typography and hairline borders).
