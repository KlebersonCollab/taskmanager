from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

from taskmanager.core.task import task

logger = logging.getLogger(__name__)


@task(name="system.run_command", queue="default", max_retries=1, timeout=300.0)
async def run_command(command: str, cwd: str | None = None) -> dict[str, Any]:
    """Executes a shell command or script and captures stdout, stderr, and exit code."""
    logger.info(f"Executing system command: {command}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    process = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    exit_code = process.returncode

    stdout_str = stdout.decode("utf-8", errors="replace").strip()
    stderr_str = stderr.decode("utf-8", errors="replace").strip()

    if exit_code != 0:
        err_msg = stderr_str or f"Command failed with exit code {exit_code}"
        raise RuntimeError(f"Command '{command}' failed (exit {exit_code}): {err_msg}")

    return {
        "command": command,
        "exit_code": exit_code,
        "stdout": stdout_str,
        "stderr": stderr_str,
    }


@task(name="system.run_script", queue="default", max_retries=1, timeout=300.0)
async def run_script(script_path: str, args: list[str] | None = None) -> dict[str, Any]:
    """Executes a Python script file using the active python interpreter."""
    py_exec = sys.executable or "python"
    cmd = f'"{py_exec}" {script_path}'
    if args:
        cmd += " " + " ".join(args)
    return await run_command(command=cmd)
