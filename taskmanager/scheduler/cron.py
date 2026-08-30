from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from croniter import croniter
from pydantic import BaseModel, Field


class ScheduleType(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"


class Schedule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    task_name: str
    queue: str = "default"
    schedule_type: ScheduleType = ScheduleType.CRON
    cron_expression: str | None = None  # e.g. "*/5 * * * *"
    interval_seconds: float | None = None
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    last_run: float | None = None
    next_run: float | None = None
    total_runs: int = 0
    created_at: float = Field(default_factory=time.time)


def calculate_next_run(schedule: Schedule, from_timestamp: float | None = None) -> float:
    """Calculates the next unix timestamp for a given Schedule."""
    base_time = from_timestamp if from_timestamp is not None else time.time()

    if schedule.schedule_type == ScheduleType.CRON:
        if not schedule.cron_expression or not croniter.is_valid(schedule.cron_expression):
            raise ValueError(f"Invalid cron expression: {schedule.cron_expression}")
        base_dt = datetime.fromtimestamp(base_time, tz=UTC)
        iter_cron = croniter(schedule.cron_expression, base_dt)
        next_dt = iter_cron.get_next(datetime)
        return next_dt.timestamp()

    elif schedule.schedule_type == ScheduleType.INTERVAL:
        if not schedule.interval_seconds or schedule.interval_seconds <= 0:
            raise ValueError(f"Invalid interval seconds: {schedule.interval_seconds}")
        return base_time + schedule.interval_seconds

    raise ValueError(f"Unknown schedule type: {schedule.schedule_type}")
