from __future__ import annotations

import asyncio
import sys

try:
    from django.conf import settings
    from django.core.management.base import BaseCommand
    DJANGO_AVAILABLE = True
except ImportError:
    BaseCommand = object  # type: ignore
    settings = None  # type: ignore
    DJANGO_AVAILABLE = False

from taskmanager.cli import get_redis_client
from taskmanager.core.broker import RedisBroker
from taskmanager.core.task import registry
from taskmanager.worker.worker import Worker


class Command(BaseCommand):  # type: ignore
    help = "Starts a TaskManager background worker instance consuming from designated queues."

    def add_arguments(self, parser):
        parser.add_argument(
            "--queues",
            type=str,
            default="default",
            help="Comma-separated list of queue names to consume (default: 'default').",
        )
        parser.add_argument(
            "--concurrency",
            type=int,
            default=5,
            help="Number of concurrent task execution slots (default: 5).",
        )
        parser.add_argument(
            "--name",
            type=str,
            default=None,
            help="Worker identification name (defaults to hostname-worker-<uuid>).",
        )
        parser.add_argument(
            "--redis-url",
            type=str,
            default=None,
            help="Redis connection URI (defaults to TASKMANAGER_REDIS_URL in settings or env).",
        )

    def handle(self, *args, **options):
        if not DJANGO_AVAILABLE:
            sys.stderr.write("Django is required to run this command.\n")
            sys.exit(1)

        queues = [q.strip() for q in options["queues"].split(",") if q.strip()]
        concurrency = options["concurrency"]
        name = options["name"]
        redis_url = options.get("redis_url") or getattr(settings, "TASKMANAGER_REDIS_URL", None)

        async def _run():
            client = await get_redis_client(redis_url)
            broker = RedisBroker(client)
            worker = Worker(
                broker=broker,
                registry=registry,
                queues=queues,
                concurrency=concurrency,
                name=name,
            )
            await worker.start()

        asyncio.run(_run())
