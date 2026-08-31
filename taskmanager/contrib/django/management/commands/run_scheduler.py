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
from taskmanager.scheduler.scheduler import Scheduler


class Command(BaseCommand):  # type: ignore
    help = "Starts the TaskManager dynamic cron and scheduled job runner."

    def add_arguments(self, parser):
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

        redis_url = options.get("redis_url") or getattr(settings, "TASKMANAGER_REDIS_URL", None)

        async def _run():
            client = await get_redis_client(redis_url)
            broker = RedisBroker(client)
            scheduler = Scheduler(broker)
            await scheduler.start()

        asyncio.run(_run())
