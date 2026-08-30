from __future__ import annotations

import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    redis_url: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    redis_prefix: str = Field(default_factory=lambda: os.getenv("REDIS_PREFIX", "tm"))
    default_queue: str = Field(default_factory=lambda: os.getenv("DEFAULT_QUEUE", "default"))
    worker_heartbeat_interval: float = 3.0
    worker_heartbeat_ttl: float = 10.0
    scheduler_poll_interval: float = 1.0


settings = Settings()
