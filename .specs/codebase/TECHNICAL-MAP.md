# Technical Map

## Directory Layout
```
.
├── .agents/                    # SDD governance, memory, and skills
├── .specs/                     # Spec Driven Development specification documents
│   ├── codebase/               # STACK, ARCHITECTURE, CONVENTIONS, TECHNICAL-MAP
│   ├── project/                # CONTEXT, PROJECT, ROADMAP, STATE, ADRs/
│   └── features/               # Feature plans, specs, tasks
├── taskmanager/                # Main Python package
│   ├── __init__.py
│   ├── config.py               # Redis and broker configuration settings
│   ├── core/                   # Core task definitions, registration, and models
│   │   ├── __init__.py
│   │   ├── task.py             # @task decorator & Task registry
│   │   ├── job.py              # Job model, status enum, payload handling
│   │   └── broker.py           # Redis broker interface & operations
│   ├── worker/                 # Worker runtime & execution
│   │   ├── __init__.py
│   │   ├── worker.py           # Worker loop, concurrency semaphore, signal handling
│   │   └── heartbeat.py        # Worker heartbeat manager & orphan reaper
│   ├── scheduler/              # Cron & delayed job scheduler
│   │   ├── __init__.py
│   │   ├── cron.py             # Cron expression calculator & evaluator
│   │   └── scheduler.py        # Dynamic scheduler process with Redis locking
│   ├── api/                    # FastAPI REST & WebSocket API
│   │   ├── __init__.py
│   │   ├── app.py              # FastAPI app setup, routes, static mount
│   │   ├── routes/             # REST endpoints (queues, jobs, workers, cron)
│   │   └── events.py           # WebSocket manager for live telemetry
│   ├── ui/                     # Frontend SPA Dashboard (DESIGN.md tokens)
│   │   ├── index.html          # Single page layout
│   │   ├── app.js              # Client dashboard state & WebSocket subscriber
│   │   └── styles.css          # Linear dark styling
│   └── cli.py                  # CLI commands (worker, scheduler, server, run-all)
├── tests/                      # Automated test suite
│   ├── conftest.py             # Pytest fixtures & fake redis client setup
│   ├── test_core.py            # Task and job lifecycle tests
│   ├── test_worker.py          # Worker execution, retries, and heartbeats
│   ├── test_scheduler.py       # Cron and delayed task scheduling tests
│   └── test_api.py             # API endpoints and WebSocket tests
├── DESIGN.md                   # Linear UI design tokens and rules
├── pyproject.toml              # Dependencies & build configuration
└── README.md                   # Getting started and usage guide
```
