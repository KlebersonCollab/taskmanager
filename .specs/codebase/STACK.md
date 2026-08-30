# Tech Stack Specification

## Backend Engine & API
- **Language**: Python 3.11+
- **Package & Environment Manager**: `uv` (Fast Python package installer, resolver, and virtual environment runner)
- **API Framework**: FastAPI & Starlette (Uvicorn ASGI server)
- **Broker & Key-Value Store**: Redis 7+ (via `redis-py` async client)
- **Data Validation & Schemas**: Pydantic v2
- **Cron Parsing**: `croniter` (standard 5-part cron syntax with timezone support)
- **Testing**: `pytest`, `pytest-asyncio`, `fakeredis` (for fast deterministic in-memory integration testing)
- **Linting & Formatting**: `ruff` / `flake8`

## Frontend Dashboard
- **Paradigm**: Minimalist Single Page Application (SPA)
- **Styling & Tokens**: Design System adhering to `DESIGN.md` (Linear Dark theme: Canvas `#010102`, Cards `#0f1011`, Accent `#5e6ad2`, Hairline `#23252a`)
- **Real-time Protocol**: Native WebSockets / Server-Sent Events (SSE)
- **Components**: Metric cards, Worker status table, Live job stream, Cron schedule editor, DLQ inspector modal.
