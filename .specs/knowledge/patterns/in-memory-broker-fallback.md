# Pattern: Automatic In-Memory Broker Fallback

## Context
Developers getting started with a project or running quick CLI commands may not have Redis installed or running (e.g., Docker virtualization unavailable on Windows/WSL). Failing with a hard connection crash degrades the developer onboarding experience.

## Solution Pattern
On application boot, probe the configured Redis connection URL with a short timeout (`asyncio.wait_for(client.ping(), timeout=0.8)`). If unreachable or if `--in-memory` is passed, automatically initialize `fakeredis.aioredis.FakeRedis(decode_responses=True)` and log a friendly reminder with the docker run command.

```python
import asyncio
import logging
import redis.asyncio as redis
import fakeredis.aioredis

logger = logging.getLogger(__name__)

async def get_redis_client(redis_url: str | None = None, force_in_memory: bool = False):
    if not force_in_memory:
        try:
            client = redis.from_url(redis_url or "redis://localhost:6379/0", decode_responses=True)
            await asyncio.wait_for(client.ping(), timeout=0.8)
            return client
        except Exception:
            logger.warning("⚠️ Redis server not accessible. Falling back to In-Memory Redis.")

    return fakeredis.aioredis.FakeRedis(decode_responses=True)
```

## Benefits
- Zero-configuration setup: runs out of the box with `uv run taskmanager dev`.
- Transparent transition to real Redis in production environments without changing application code.
