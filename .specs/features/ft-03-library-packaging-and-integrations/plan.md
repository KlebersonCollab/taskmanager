# Feature Plan: Library Packaging & Framework Integrations (ft-03)

## 1. Problem Statement
Currently, TaskManager functions primarily as a standalone repository execution engine. To allow external Python developers to install it via `pip` or `uv` and seamlessly embed the task engine, workers, dynamic scheduler, and Linear-themed SPA dashboard into their own projects (e.g. FastAPI, Django, Flask, or standalone sidecar), the package must support proper static asset distribution, top-level convenience classes, framework adapters, and reproducible sample reference implementations.

## 2. Goals & Value
- **Plug-and-Play Distribution**: Configure `pyproject.toml` package data to include all static assets (`*.html`, `*.css`, `*.js`) in the wheel distribution.
- **Universal Mount Support**: Adapt the SPA dashboard and API to support subpath mounts (e.g. `/tasks/`, `/admin/tasks/`) dynamically without broken asset or WebSocket links.
- **Top-Level Convenience API**: Expose `TaskManager`, `@task`, and `create_app` directly at `taskmanager` root for concise 5-line integrations.
- **Django Framework Support (`taskmanager.contrib.django`)**: Provide an official `AppConfig` with automatic `tasks.py` discovery across `INSTALLED_APPS`, URL routing, and native `manage.py run_worker` / `manage.py run_scheduler` commands.
- **FastAPI / Starlette Mounting Helper**: Provide clean sub-application mounting patterns.
- **Practical Samples**: Provide ready-to-run sample applications in `samples/` for FastAPI, Django, and Standalone CLI.
- **Detailed Documentation**: Update `README.md` with complete, copy-pasteable guides for every integration pattern and PyPI distribution steps.

## 3. Scope Boundaries
- **In Scope**:
  - `pyproject.toml` package-data definitions.
  - `taskmanager/__init__.py` clean exports & `TaskManager` high-level manager class.
  - `taskmanager/ui/index.html` and `taskmanager/ui/app.js` relative path and subpath mount resilience.
  - `taskmanager/contrib/django` (apps, urls, management commands).
  - `taskmanager/contrib/fastapi.py` helper.
  - `samples/` directory with FastAPI, Django, and Standalone CLI examples.
  - Unit and integration tests in `tests/test_library.py` and `tests/test_contrib_django.py`.
  - Comprehensive `README.md` documentation.
- **Out of Scope**:
  - Rewriting Redis broker underlying schema or distributed lock primitives.
  - Altering core Task / Job execution lifecycle.
