# Pattern: Windows Subprocess UTF-8 Enforcement

## Context
When running shell commands, python scripts, or external tools via `asyncio.create_subprocess_shell` or `subprocess.Popen` on Windows, Python defaults to the active OEM code page (typically `cp1252` or `cp850`). If the spawned command outputs Unicode characters (such as emojis `📦`, `✅`, or non-ASCII accents), Python raises a fatal `UnicodeEncodeError: 'charmap' codec can't encode character...`.

## Solution Pattern
Always inject `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` into the subprocess environment dictionary, and decode output streams with `errors="replace"`:

```python
import asyncio
import os
import sys
from typing import Any

async def run_safe_subprocess(command: str, cwd: str | None = None) -> dict[str, Any]:
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
    
    return {
        "exit_code": process.returncode,
        "stdout": stdout.decode("utf-8", errors="replace").strip(),
        "stderr": stderr.decode("utf-8", errors="replace").strip(),
    }
```

## Benefits
- Prevents random crashes when scripts print status emojis or multi-language text.
- Works consistently across Windows, macOS, and Linux without platform branching.
