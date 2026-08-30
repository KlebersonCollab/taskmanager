# Project Vision: TaskManager

## Vision Statement
TaskManager is a modern, reliable, and high-performance background task execution engine and management dashboard. Inspired by the best of Celery (Python ecosystem) and BullMQ (Redis-native queues, delayed jobs, and repeatable cron), it combines a lightweight asynchronous Python worker runtime with a clean, responsive SPA management dashboard built to Linear-grade UI standards.

## Target Audience & Use Cases
- **Developers & DevOps**: Need a plug-and-play distributed job runner in Python with zero bloat, easy decorator-based task registration, and robust retry/DLQ semantics.
- **System Operators**: Need a single-pane-of-glass dashboard to monitor real-time worker heartbeats, pause/resume queues, inspect failed jobs, replay DLQ items, and dynamically configure cron/scheduled tasks.

## Core Pillars
1. **Developer Experience (DX)**: Simple `@task` decorator API, async/sync worker support, typed payloads with Pydantic.
2. **Reliability & Resilience**: Redis-backed persistence, heartbeats, automated orphan job recovery, exponential backoff, and DLQ.
3. **Observability & Real-Time Control**: WebSockets / Server-Sent Events (SSE) streaming live job progress, throughput metrics, and worker statuses directly into the SPA dashboard.
4. **Linear Design Polish**: Interface crafted with precision typography, dark canvas surfaces, and clear visual hierarchy defined in `DESIGN.md`.
