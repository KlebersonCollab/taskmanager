from __future__ import annotations

import importlib
import logging

try:
    from django.apps import AppConfig
    from django.conf import settings
    DJANGO_AVAILABLE = True
except ImportError:
    AppConfig = object  # type: ignore
    settings = None  # type: ignore
    DJANGO_AVAILABLE = False

logger = logging.getLogger("taskmanager.contrib.django")


def autodiscover_tasks() -> list[str]:
    """Scans all INSTALLED_APPS for <app>.tasks modules and imports them."""
    if not DJANGO_AVAILABLE or not settings:
        return []

    discovered: list[str] = []
    installed_apps = getattr(settings, "INSTALLED_APPS", [])

    for app_path in installed_apps:
        if app_path.startswith("taskmanager") or app_path.startswith("django."):
            continue
        try:
            mod_name = f"{app_path}.tasks"
            importlib.import_module(mod_name)
            discovered.append(mod_name)
            logger.debug("Discovered tasks module: %s", mod_name)
        except (ImportError, AttributeError):
            pass

    return discovered


class TaskManagerConfig(AppConfig):  # type: ignore
    name = "taskmanager.contrib.django"
    verbose_name = "TaskManager Background Engine"

    def ready(self) -> None:
        if DJANGO_AVAILABLE:
            autodiscover_tasks()
