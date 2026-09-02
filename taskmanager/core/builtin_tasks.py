from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

from taskmanager.core.task import TaskContext, task

logger = logging.getLogger(__name__)


@task(name="system.run_command", queue="default", max_retries=1, timeout=300.0)
async def run_command(
    command: str, cwd: str | None = None, ctx: TaskContext | None = None
) -> dict[str, Any]:
    """Executes a shell command or script and streams stdout, stderr line-by-line in real time."""
    logger.info(f"Executing system command: {command}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    if ctx:
        await ctx.update_progress(0.0, f"Iniciando comando: {command[:50]}")
        await ctx.append_log(f"Comando disparado: {command}")

    # Normalize cwd: if invalid directory or placeholder, fallback to None (current workspace)
    if cwd and (cwd.startswith("valor_") or not os.path.exists(cwd) or not os.path.isdir(cwd)):
        logger.warning(f"Directory '{cwd}' is invalid or does not exist. Running in current working directory.")
        cwd = None

    process = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    async def _read_stream(stream: asyncio.StreamReader | None, is_stderr: bool = False):
        if stream is None:
            return
        while True:
            line_bytes = await stream.readline()
            if not line_bytes:
                break
            line_str = line_bytes.decode("utf-8", errors="replace").rstrip("\r\n")
            if is_stderr:
                stderr_lines.append(line_str)
                if ctx:
                    await ctx.append_log(f"[STDERR] {line_str}")
            else:
                stdout_lines.append(line_str)
                if ctx:
                    await ctx.append_log(line_str)

    await asyncio.gather(
        _read_stream(process.stdout, is_stderr=False),
        _read_stream(process.stderr, is_stderr=True),
    )
    exit_code = await process.wait()

    stdout_str = "\n".join(stdout_lines).strip()
    stderr_str = "\n".join(stderr_lines).strip()

    if ctx:
        if exit_code == 0:
            await ctx.update_progress(100.0, "Comando executado com sucesso.")
        else:
            await ctx.update_progress(100.0, f"Comando falhou (exit code {exit_code}).")

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
async def run_script(
    script_path: str, args: list[str] | None = None, ctx: TaskContext | None = None
) -> dict[str, Any]:
    """Executes a Python script file using the active python interpreter with real-time log streaming."""
    py_exec = sys.executable or "python"
    cmd = f'"{py_exec}" {script_path}'
    if args:
        cmd += " " + " ".join(args)
    return await run_command(command=cmd, ctx=ctx)

