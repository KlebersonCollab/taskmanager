# Anti-Pattern: Unpinned Subprocess Codepage on Windows

## Problem Description
Spawning child processes on Windows using `subprocess` or `asyncio.create_subprocess_shell` without explicitly configuring UTF-8 variables causes child processes to default to legacy DOS/Windows code pages (e.g., `cp1252`, `cp850`).

## Anti-Pattern Example
```python
# ❌ VULNERABLE TO UnicodeEncodeError ON WINDOWS
process = await asyncio.create_subprocess_shell(
    command,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

## Why This Fails
When a Python script or CLI outputs emojis (`📦`, `⚡`, `✅`), non-ASCII names, or international characters, the parent/child stream fails with:
`UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f4e6' in position 0: character maps to <undefined>`.

## Correct Approach
Always pass `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` in `env` and decode streams with `errors="replace"` (see [windows-subprocess-utf8.md](../patterns/windows-subprocess-utf8.md)).
