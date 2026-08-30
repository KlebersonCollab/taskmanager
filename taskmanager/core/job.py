from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    DELAYED = "delayed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_name: str
    queue: str = "default"
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    priority: int = 0
    max_retries: int = 3
    retry_count: int = 0
    retry_backoff: float = 2.0  # Multiplier in seconds for exponential backoff (e.g. 2s, 4s, 8s)
    timeout: float | None = None
    created_at: float = Field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    result: Any = None
    error: str | None = None
    traceback: str | None = None
    worker_id: str | None = None
    idempotency_key: str | None = None

    def calculate_next_backoff(self) -> float:
        """Calculate exponential backoff in seconds for the next retry attempt."""
        return self.retry_backoff * (2**self.retry_count)

    def can_retry(self) -> bool:
        """Check if job has remaining retry attempts."""
        return self.retry_count < self.max_retries
