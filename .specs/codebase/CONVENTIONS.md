# Code Conventions & Invariants

## Python Standards
- **Type Annotations**: Strict typing using Python 3.11+ syntax (`str | None`, `list[str]`, etc.).
- **Async First**: Asyncio native coroutines for broker communication, worker loop, and API endpoints.
- **Pydantic Models**: All DTOs, API inputs/outputs, and serialization payloads validated with Pydantic v2.
- **Error Handling**: Custom domain exceptions inheriting from `TaskManagerError`. No bare `except:`.
- **Testing**:
  - Unit & Integration tests in `tests/` using `pytest` + `pytest-asyncio`.
  - Use `fakeredis` for headless isolated tests without requiring a live external Redis daemon.
  - Sensor test suites must pass 100% before approval.

## Frontend & Design Conventions
- **Token Compliance**: Strict adherence to tokens in `DESIGN.md`.
  - Background: `#010102` (Canvas)
  - Cards & Panels: `#0f1011` with `#23252a` hairline border.
  - Accent Color: `#5e6ad2` (hover `#828fff`, focus `#5e69d1`).
  - Text: Primary `#f7f8f8`, Muted `#d0d6e0`, Subtle `#8a8f98`.
  - Status Indicators: Success `#27a644`, Warning `#e59a24`, Error `#d14d42`.
- **Zero Heavy Bundler Friction**: Single clean lightweight SPA bundle served directly by FastAPI or static file server with WebSocket live stream.
