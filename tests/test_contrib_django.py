from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

from taskmanager.contrib.django.apps import autodiscover_tasks
from taskmanager.contrib.django.management.commands.run_scheduler import (
    Command as RunSchedulerCommand,
)
from taskmanager.contrib.django.management.commands.run_worker import Command as RunWorkerCommand


def test_autodiscover_tasks_empty():
    with patch("taskmanager.contrib.django.apps.DJANGO_AVAILABLE", False):
        discovered = autodiscover_tasks()
        assert discovered == []


def test_autodiscover_tasks_mock_django_settings():
    mock_settings = types.SimpleNamespace(
        INSTALLED_APPS=["myapp", "django.contrib.auth", "taskmanager.contrib.django"]
    )
    with (
        patch("taskmanager.contrib.django.apps.DJANGO_AVAILABLE", True),
        patch("taskmanager.contrib.django.apps.settings", mock_settings),
        patch("importlib.import_module") as mock_import,
    ):
        discovered = autodiscover_tasks()
        assert "myapp.tasks" in discovered
        mock_import.assert_called_once_with("myapp.tasks")


def test_django_management_commands_arguments():
    worker_cmd = RunWorkerCommand()
    parser_mock = MagicMock()
    worker_cmd.add_arguments(parser_mock)
    # Check that --queues, --concurrency, and --name arguments were added
    arg_names = [call.args[0] for call in parser_mock.add_argument.call_args_list]
    assert "--queues" in arg_names
    assert "--concurrency" in arg_names
    assert "--name" in arg_names

    sched_cmd = RunSchedulerCommand()
    parser_mock_sched = MagicMock()
    sched_cmd.add_arguments(parser_mock_sched)
    sched_args = [call.args[0] for call in parser_mock_sched.add_argument.call_args_list]
    assert "--redis-url" in sched_args
