"""
TaskManager: Modern background task execution engine with dynamic cron scheduling
and real-time management dashboard.
"""

import taskmanager.core.builtin_tasks as builtin_tasks  # Auto-registers system tasks
from taskmanager.core.task import task

__version__ = "0.1.0"
__all__ = ["task", "builtin_tasks", "__version__"]
