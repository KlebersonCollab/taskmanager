from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

import redis.asyncio as redis

logger = logging.getLogger("taskmanager.limiter")


@dataclass(frozen=True)
class RateLimitSpec:
    """Specification of a rate limit (rate count per period in seconds)."""

    rate: int
    period: float
    capacity: float | None = None

    def get_capacity(self) -> float:
        return float(self.capacity if self.capacity is not None else self.rate)

    def get_refill_rate(self) -> float:
        return float(self.rate) / self.period


def parse_rate_limit(spec_str: str) -> RateLimitSpec:
    """Parses human-friendly rate limit strings like '10/s', '100/m', '1000/h', '5000/d'."""
    if not isinstance(spec_str, str):
        raise ValueError(f"Rate limit must be a string, got {type(spec_str)}")

    pattern = r"^\s*(\d+)\s*/\s*(s|sec|seconds?|m|min|minutes?|h|hr|hours?|d|days?)\s*$"
    match = re.match(pattern, spec_str.strip(), re.IGNORECASE)
    if not match:
        raise ValueError(
            f"Invalid rate limit format '{spec_str}'. Expected format like '10/s', '100/m', '1000/h', '5000/d'."
        )

    rate_count = int(match.group(1))
    if rate_count <= 0:
        raise ValueError(f"Rate count must be greater than 0, got {rate_count}")

    unit = match.group(2).lower()
    if unit in ("s", "sec", "second", "seconds"):
        period = 1.0
    elif unit in ("m", "min", "minute", "minutes"):
        period = 60.0
    elif unit in ("h", "hr", "hour", "hours"):
        period = 3600.0
    elif unit in ("d", "day", "days"):
        period = 86400.0
    else:
        raise ValueError(f"Unsupported rate limit unit: '{unit}'")

    return RateLimitSpec(rate=rate_count, period=period)


class TokenBucketLimiter:
    """Distributed Token Bucket Rate Limiter backed by Redis."""

    def __init__(self, redis_client: redis.Redis, prefix: str = "taskmanager"):
        self.redis = redis_client
        self.prefix = prefix

    def _key(self, task_name: str) -> str:
        return f"{self.prefix}:ratelimit:{task_name}"

    async def acquire(self, task_name: str, spec: RateLimitSpec) -> tuple[bool, float]:
        """Attempts to acquire 1 token from the bucket.

        Returns (allowed: bool, retry_after: float).
        """
        key = self._key(task_name)
        now = time.time()
        capacity = spec.get_capacity()
        refill_rate = spec.get_refill_rate()
        ttl = max(60, int(spec.period * 2 + 10))

        # Atomic token bucket update using redis hash
        try:
            data = await self.redis.hmget(key, ["tokens", "last_updated"])
            raw_tokens, raw_last_updated = data[0], data[1]

            if raw_tokens is None or raw_last_updated is None:
                current_tokens = capacity
                last_updated = now
            else:
                current_tokens = float(raw_tokens)
                last_updated = float(raw_last_updated)

            elapsed = max(0.0, now - last_updated)
            current_tokens = min(capacity, current_tokens + elapsed * refill_rate)

            if current_tokens >= 1.0:
                current_tokens -= 1.0
                pipe = self.redis.pipeline()
                pipe.hset(key, mapping={"tokens": str(current_tokens), "last_updated": str(now)})
                pipe.expire(key, ttl)
                await pipe.execute()
                return True, 0.0
            else:
                retry_after = (1.0 - current_tokens) / refill_rate
                pipe = self.redis.pipeline()
                pipe.hset(key, mapping={"tokens": str(current_tokens), "last_updated": str(now)})
                pipe.expire(key, ttl)
                await pipe.execute()
                return False, max(0.01, retry_after)

        except Exception as err:
            logger.warning(f"Error checking rate limit for {task_name}: {err}. Allowing execution as fail-safe.")
            return True, 0.0


class ConcurrencyLimiter:
    """Distributed Concurrency Semaphore backed by Redis Sorted Sets."""

    def __init__(self, redis_client: redis.Redis, prefix: str = "taskmanager"):
        self.redis = redis_client
        self.prefix = prefix

    def _key(self, task_name: str) -> str:
        return f"{self.prefix}:concurrency:{task_name}"

    async def acquire(
        self, task_name: str, max_concurrency: int, job_id: str, lock_ttl: float = 300.0
    ) -> bool:
        """Attempts to acquire a concurrency slot for the task.

        Returns True if acquired, False if max concurrency reached.
        """
        if max_concurrency <= 0:
            return True

        key = self._key(task_name)
        now = time.time()
        expiry = now + lock_ttl

        try:
            # 1. Clean expired slots (stale jobs)
            await self.redis.zremrangebyscore(key, "-inf", now)

            # 2. Check current active count
            active_count = await self.redis.zcard(key)
            if active_count >= max_concurrency:
                return False

            # 3. Add slot
            await self.redis.zadd(key, {job_id: expiry})
            await self.redis.expire(key, int(lock_ttl * 2))
            return True

        except Exception as err:
            logger.warning(f"Error checking concurrency limit for {task_name}: {err}. Allowing execution.")
            return True

    async def release(self, task_name: str, job_id: str) -> None:
        """Releases the concurrency slot for the given job."""
        key = self._key(task_name)
        try:
            await self.redis.zrem(key, job_id)
        except Exception as err:
            logger.debug(f"Error releasing concurrency slot for {task_name} (job {job_id}): {err}")
