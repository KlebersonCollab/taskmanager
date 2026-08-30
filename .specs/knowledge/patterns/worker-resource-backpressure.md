# Pattern: Worker Resource Backpressure & Guardrails

## Context
High-concurrency workers can easily exhaust system resources (RAM and CPU), triggering Linux Out-Of-Memory (OOM) killer or freezing Windows system responsiveness when multiple heavy tasks are executed simultaneously.

## Solution Pattern
Implement active hardware guardrails within the worker dispatch loop using `psutil` sampling. When CPU or RSS RAM reaches configured thresholds:
1. Switch worker state to `throttled`.
2. Pause polling new jobs from the Redis queue.
3. Allow active in-flight jobs to complete and free memory before resuming consumption.

```python
import asyncio
import psutil

class Worker:
    async def loop(self):
        while self._running:
            # 1. Backpressure Check
            if self.max_memory_mb and self.info.memory_mb >= self.max_memory_mb:
                self.info.status = "throttled"
                await asyncio.sleep(2.0)
                continue

            if self.max_cpu_percent and self.info.cpu_percent >= self.max_cpu_percent:
                self.info.status = "throttled"
                await asyncio.sleep(1.0)
                continue

            # 2. Concurrency Slot Acquisition
            await self.semaphore.acquire()
            job = await self.broker.fetch_next_job(self.queues, worker_id=self.id)
            if job:
                asyncio.create_task(self._process_job(job))
            else:
                self.semaphore.release()
                await asyncio.sleep(0.2)
```

## Benefits
- Prevents OOM crashes under sudden traffic spikes.
- Gracefully balances workloads across multiple workers in a cluster.
