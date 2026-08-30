from __future__ import annotations

import asyncio
import logging
from typing import Any

from taskmanager.core.task import task

logger = logging.getLogger(__name__)


@task(name="system.run_command", queue="default", max_retries=1, timeout=300.0)
async def run_command(command: str, cwd: str | None = None) -> dict[str, Any]:
    """Executes a shell command or script and captures stdout, stderr, and exit code."""
    logger.info(f"Executing system command: {command}")
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    exit_code = process.returncode

    if exit_code != 0:
        err_msg = stderr.decode().strip() or f"Command failed with exit code {exit_code}"
        raise RuntimeError(f"Command '{command}' failed (exit {exit_code}): {err_msg}")

    return {
        "command": command,
        "exit_code": exit_code,
        "stdout": stdout.decode().strip(),
        "stderr": stderr.decode().strip(),
    }


@task(name="system.run_script", queue="default", max_retries=1, timeout=300.0)
async def run_script(script_path: str, args: list[str] | None = None) -> dict[str, Any]:
    """Executes a Python script file using the active python interpreter."""
    cmd = f"python {script_path}"
    if args:
        cmd += " " + " ".join(args)
    return await run_command(command=cmd)
