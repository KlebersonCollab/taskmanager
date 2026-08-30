# Anti-Pattern: Passing Unverified Working Directory (CWD) to Subprocesses

## Problem Description
Blindly forwarding user-supplied or form-generated working directory parameters (`cwd`) to `subprocess.Popen` or `asyncio.create_subprocess_shell` without checking if the path exists on disk.

## Why This Fails
On Windows, passing a non-existent folder or placeholder string like `"valor_cwd"` causes `CreateProcess` to fail immediately with:
`NotADirectoryError: [WinError 267] O nome do diretório é inválido`.

## Correct Approach
Sanitize and validate `cwd` before invoking subprocesses:
```python
if cwd and (cwd.startswith("valor_") or not os.path.exists(cwd) or not os.path.isdir(cwd)):
    logger.warning(f"Invalid cwd '{cwd}'. Defaulting to current workspace directory.")
    cwd = None
```
