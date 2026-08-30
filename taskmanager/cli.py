from __future__ import annotations

import argparse
import asyncio
import importlib
import logging

import redis.asyncio as redis
import uvicorn

from taskmanager.api.app import create_app
from taskmanager.config import settings
from taskmanager.core.broker import RedisBroker
from taskmanager.core.task import registry
from taskmanager.scheduler.scheduler import Scheduler
from taskmanager.worker.worker import Worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("taskmanager.cli")


def auto_discover_tasks(modules: list[str]) -> None:
    """Imports user modules to register decorated @task functions."""
    for mod in modules:
        try:
            importlib.import_module(mod)
            logger.info(f"Loaded tasks from module: {mod}")
        except Exception as err:
            logger.warning(f"Could not import module '{mod}': {err}")


async def run_worker(queues: list[str], concurrency: int, name: str | None) -> None:
    client = redis.from_url(settings.redis_url, decode_responses=True)
    broker = RedisBroker(client, prefix=settings.redis_prefix)
    worker = Worker(
        queues=queues, concurrency=concurrency, name=name, broker=broker, task_registry=registry
    )
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()


async def run_scheduler() -> None:
    client = redis.from_url(settings.redis_url, decode_responses=True)
    broker = RedisBroker(client, prefix=settings.redis_prefix)
    sched = Scheduler(broker)
    try:
        await sched.start()
    except KeyboardInterrupt:
        await sched.stop()


async def run_dev(host: str, port: int, queues: list[str], concurrency: int) -> None:
    """Runs API Server, Worker, and Scheduler in a single process for local dev."""
    client = redis.from_url(settings.redis_url, decode_responses=True)
    broker = RedisBroker(client, prefix=settings.redis_prefix)
    registry.set_broker(broker)

    worker = Worker(
        queues=queues,
        concurrency=concurrency,
        name="dev-worker",
        broker=broker,
        task_registry=registry,
    )
    sched = Scheduler(broker)
    app = create_app(broker=broker, task_reg=registry)

    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    logger.info(f"🚀 TaskManager Dev Environment running at http://{host}:{port}")

    await asyncio.gather(
        server.serve(),
        worker.start(),
        sched.start(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="taskmanager",
        description="TaskManager: Celery/BullMQ-like background task manager and Linear dark SPA dashboard",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Server Command
    server_parser = subparsers.add_parser("server", help="Start the FastAPI dashboard & API server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    server_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    server_parser.add_argument(
        "--app-module", nargs="*", default=[], help="Python modules containing @task definitions"
    )

    # 2. Worker Command
    worker_parser = subparsers.add_parser("worker", help="Start an async worker process")
    worker_parser.add_argument(
        "-q", "--queues", default="default", help="Comma-separated queue names (default: default)"
    )
    worker_parser.add_argument(
        "-c", "--concurrency", type=int, default=5, help="Worker concurrency (default: 5)"
    )
    worker_parser.add_argument("-n", "--name", default=None, help="Custom worker name")
    worker_parser.add_argument(
        "-m", "--modules", nargs="*", default=[], help="Python modules to import for tasks"
    )

    # 3. Scheduler Command
    sched_parser = subparsers.add_parser("scheduler", help="Start the dynamic cron scheduler")
    sched_parser.add_argument(
        "-m", "--modules", nargs="*", default=[], help="Python modules to import for tasks"
    )

    # 4. Dev Command (All-in-one)
    dev_parser = subparsers.add_parser(
        "dev", help="Start Server, Worker, and Scheduler in one command"
    )
    dev_parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    dev_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    dev_parser.add_argument("-q", "--queues", default="default", help="Comma-separated queue names")
    dev_parser.add_argument("-c", "--concurrency", type=int, default=5, help="Worker concurrency")
    dev_parser.add_argument(
        "-m", "--modules", nargs="*", default=[], help="Python modules to import"
    )

    args = parser.parse_args()

    if args.command == "server":
        auto_discover_tasks(args.app_module)
        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port)

    elif args.command == "worker":
        auto_discover_tasks(args.modules)
        queues = [q.strip() for q in args.queues.split(",") if q.strip()]
        asyncio.run(run_worker(queues=queues, concurrency=args.concurrency, name=args.name))

    elif args.command == "scheduler":
        auto_discover_tasks(args.modules)
        asyncio.run(run_scheduler())

    elif args.command == "dev":
        auto_discover_tasks(args.modules)
        queues = [q.strip() for q in args.queues.split(",") if q.strip()]
        asyncio.run(
            run_dev(host=args.host, port=args.port, queues=queues, concurrency=args.concurrency)
        )


if __name__ == "__main__":
    main()
