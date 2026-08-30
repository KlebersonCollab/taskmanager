from __future__ import annotations

import argparse
import asyncio
import importlib
import importlib.util
import logging
import sys
from pathlib import Path

import fakeredis.aioredis
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

_shared_fake_server = fakeredis.FakeServer()


async def get_redis_client(redis_url: str | None = None, force_in_memory: bool = False) -> redis.Redis:
    """Provides a connected Redis client with graceful fallback to in-memory FakeRedis."""
    url = redis_url or settings.redis_url
    if force_in_memory or (url and url.startswith("memory://")):
        logger.info("🧠 Usando Redis In-Memory integrado (fakeredis).")
        return fakeredis.aioredis.FakeRedis(server=_shared_fake_server, decode_responses=True)

    try:
        client = redis.from_url(url, decode_responses=True)
        # Test connection vitality
        await asyncio.wait_for(client.ping(), timeout=1.5)
        return client
    except Exception:
        logger.warning(
            f"⚠️ Servidor Redis em '{url}' não está acessível. "
            "Iniciando automaticamente com Redis In-Memory integrado para desenvolvimento!"
        )
        logger.info("💡 Dica: Para conectar a um Redis real, execute: docker run -d -p 6379:6379 redis:alpine")
        return fakeredis.aioredis.FakeRedis(server=_shared_fake_server, decode_responses=True)


def auto_discover_tasks(modules: list[str]) -> None:
    """Imports user modules or file paths to register decorated @task functions."""
    cwd = str(Path.cwd().resolve())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    for mod in modules:
        try:
            # If path to a python file was passed directly (e.g. 'example_tasks.py')
            if mod.endswith(".py") or "/" in mod or "\\" in mod:
                path = Path(mod).resolve()
                if path.exists():
                    mod_name = path.stem
                    spec = importlib.util.spec_from_file_location(mod_name, str(path))
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[mod_name] = module
                        spec.loader.exec_module(module)
                        logger.info(f"Loaded tasks from file: {mod}")
                        continue

            # Standard python module import (e.g. 'example_tasks')
            importlib.import_module(mod)
            logger.info(f"Loaded tasks from module: {mod}")
        except Exception as err:
            logger.warning(f"Could not import module '{mod}': {err}")


async def run_worker(
    queues: list[str],
    concurrency: int,
    name: str | None,
    redis_url: str | None = None,
    in_memory: bool = False,
) -> None:
    client = await get_redis_client(redis_url, force_in_memory=in_memory)
    broker = RedisBroker(client, prefix=settings.redis_prefix)
    registry.set_broker(broker)
    worker = Worker(
        queues=queues, concurrency=concurrency, name=name, broker=broker, task_registry=registry
    )
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()


async def run_scheduler(redis_url: str | None = None, in_memory: bool = False) -> None:
    client = await get_redis_client(redis_url, force_in_memory=in_memory)
    broker = RedisBroker(client, prefix=settings.redis_prefix)
    sched = Scheduler(broker)
    try:
        await sched.start()
    except KeyboardInterrupt:
        await sched.stop()


async def run_server(
    host: str,
    port: int,
    redis_url: str | None = None,
    in_memory: bool = False,
) -> None:
    client = await get_redis_client(redis_url, force_in_memory=in_memory)
    broker = RedisBroker(client, prefix=settings.redis_prefix)
    registry.set_broker(broker)
    app = create_app(broker=broker, task_reg=registry)
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def run_dev(
    host: str,
    port: int,
    queues: list[str],
    concurrency: int,
    redis_url: str | None = None,
    in_memory: bool = False,
) -> None:
    """Runs API Server, Worker, and Scheduler in a single process with shared broker."""
    client = await get_redis_client(redis_url, force_in_memory=in_memory)
    broker = RedisBroker(client, prefix=settings.redis_prefix)
    registry.set_broker(broker)

    # In dev mode, auto-listen to all registered queues if default was selected
    active_queues = list(queues)
    if queues == ["default"]:
        for t_name in registry.list_tasks():
            t_obj = registry.get(t_name)
            if t_obj and t_obj.queue not in active_queues:
                active_queues.append(t_obj.queue)

    worker = Worker(
        queues=active_queues,
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
    server_parser.add_argument("--redis-url", default=None, help="Redis connection URL")
    server_parser.add_argument("--in-memory", action="store_true", help="Force in-memory Redis")
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
    worker_parser.add_argument("--redis-url", default=None, help="Redis connection URL")
    worker_parser.add_argument("--in-memory", action="store_true", help="Force in-memory Redis")
    worker_parser.add_argument(
        "-m", "--modules", nargs="*", default=[], help="Python modules to import for tasks"
    )

    # 3. Scheduler Command
    sched_parser = subparsers.add_parser("scheduler", help="Start the dynamic cron scheduler")
    sched_parser.add_argument("--redis-url", default=None, help="Redis connection URL")
    sched_parser.add_argument("--in-memory", action="store_true", help="Force in-memory Redis")
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
    dev_parser.add_argument("--redis-url", default=None, help="Redis connection URL")
    dev_parser.add_argument("--in-memory", action="store_true", help="Force in-memory Redis")
    dev_parser.add_argument(
        "-m", "--modules", nargs="*", default=[], help="Python modules to import"
    )

    args = parser.parse_args()

    if args.command == "server":
        auto_discover_tasks(args.app_module)
        asyncio.run(
            run_server(
                host=args.host,
                port=args.port,
                redis_url=args.redis_url,
                in_memory=args.in_memory,
            )
        )

    elif args.command == "worker":
        auto_discover_tasks(args.modules)
        queues = [q.strip() for q in args.queues.split(",") if q.strip()]
        asyncio.run(
            run_worker(
                queues=queues,
                concurrency=args.concurrency,
                name=args.name,
                redis_url=args.redis_url,
                in_memory=args.in_memory,
            )
        )

    elif args.command == "scheduler":
        auto_discover_tasks(args.modules)
        asyncio.run(
            run_scheduler(
                redis_url=args.redis_url,
                in_memory=args.in_memory,
            )
        )

    elif args.command == "dev":
        auto_discover_tasks(args.modules)
        queues = [q.strip() for q in args.queues.split(",") if q.strip()]
        asyncio.run(
            run_dev(
                host=args.host,
                port=args.port,
                queues=queues,
                concurrency=args.concurrency,
                redis_url=args.redis_url,
                in_memory=args.in_memory,
            )
        )


if __name__ == "__main__":
    main()
