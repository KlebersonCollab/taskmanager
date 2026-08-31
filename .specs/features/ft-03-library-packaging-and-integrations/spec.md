# Feature Specification: Library Packaging & Framework Integrations (ft-03)

## 1. User Stories & Acceptance Criteria

### User Story 1: Package Data & Wheel Asset Bundling
- **As a** developer installing `taskmanager` via pip/uv in another project,
- **I want** the static SPA assets (`index.html`, `styles.css`, `app.js`) to be bundled inside the package wheel,
- **So that** the dashboard runs without missing frontend assets in production.

#### BDD Acceptance Criteria (AC-1)
- **Given** `pyproject.toml` with `tool.setuptools.package-data`,
- **When** `taskmanager` is built or packaged,
- **Then** all files in `taskmanager/ui/` (`*.html`, `*.css`, `*.js`) are included in the package distribution.

---

### User Story 2: Subpath Mount & URL Resilience in SPA Dashboard
- **As a** developer embedding TaskManager in an existing FastAPI application at `/tasks` or `/admin/tasks`,
- **I want** the dashboard API fetch calls, WebSockets, and static asset links to automatically resolve relative to the mounted subpath,
- **So that** there are no 404 errors or broken WebSocket connections when mounted under a prefix.

#### BDD Acceptance Criteria (AC-2)
- **Given** TaskManager mounted at `/tasks` in a parent FastAPI app,
- **When** a user visits `http://host:port/tasks/`,
- **Then** CSS and JS assets load correctly via relative paths,
- **When** `app.js` initializes,
- **Then** API requests target `/tasks/api/...` and WebSocket connects to `ws://host:port/tasks/ws/events`.

---

### User Story 3: High-Level `TaskManager` Class & Public API
- **As a** developer using TaskManager in Python,
- **I want** a clean `TaskManager` wrapper class and top-level exports,
- **So that** I can initialize broker, registry, scheduler, and FastAPI sub-app with minimal boilerplate.

#### BDD Acceptance Criteria (AC-3)
- **Given** `from taskmanager import TaskManager, task, create_app`,
- **When** `tm = TaskManager(redis_url="memory://", prefix="myapp")` is created,
- **Then** `tm.broker`, `tm.registry`, `tm.scheduler`, and `tm.get_app()` are accessible and properly configured.

---

### User Story 4: Django Contrib Framework Adapter (`taskmanager.contrib.django`)
- **As a** Django developer,
- **I want** to add `'taskmanager.contrib.django'` to `INSTALLED_APPS` and include its URLs in `urls.py`,
- **So that** all `tasks.py` across Django apps are automatically discovered, and I can run workers via `python manage.py run_worker`.

#### BDD Acceptance Criteria (AC-4)
- **Given** a Django project with `'taskmanager.contrib.django'` in `INSTALLED_APPS`,
- **When** Django initializes (`AppConfig.ready()`),
- **Then** `autodiscover()` imports `tasks.py` from all installed apps,
- **When** `python manage.py run_worker` is executed,
- **Then** the worker process runs consuming jobs from configured queues.

---

### User Story 5: Complete Samples & README Integration Guide
- **As a** new developer adopting TaskManager,
- **I want** reference sample applications in `samples/` (FastAPI, Django, CLI) and a detailed guide in `README.md`,
- **So that** I have working templates and instructions for every deployment scenario.

#### BDD Acceptance Criteria (AC-5)
- **Given** the `samples/` directory,
- **When** inspecting `samples/fastapi_sample`, `samples/django_sample`, and `samples/standalone_cli`,
- **Then** each directory contains self-contained executable code and instructions,
- **When** viewing `README.md`,
- **Then** comprehensive sections for Installation, FastAPI Sub-App, Django Contrib, Standalone CLI, and PyPI publishing are clearly documented.
