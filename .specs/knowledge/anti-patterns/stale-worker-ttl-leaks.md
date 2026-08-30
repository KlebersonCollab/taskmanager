# Anti-Pattern: Stale Worker Registration Without TTL Cleanup

## Problem Description
Tracking active workers in a shared Redis set (`SADD tm:workers <worker_id>`) while storing worker details with a key TTL (`SET tm:worker:<id> ... EX 10`).

## Why This Fails
When a worker crashes, is killed ungracefully (`SIGKILL`, `Ctrl+C`), or network disconnects:
1. The detail key (`tm:worker:<id>`) expires after 10 seconds.
2. The ID remains forever in the set `tm:workers`.
3. Over repeated restarts, queries to `SMEMBERS tm:workers` return hundreds of dead ghost worker IDs with `None` payloads, slowing down dashboards and polluting cluster metrics.

## Correct Approach
When reading workers in `get_all_workers()`, if `await broker.redis.get(key)` returns `None`, immediately clean up the dead ID from the set using `await broker.redis.srem(broker._key_workers(), wid)`.
