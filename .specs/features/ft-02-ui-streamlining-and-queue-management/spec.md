# Feature Specification: UI Streamlining & Queue Management (ft-02)

## 1. User Stories & Acceptance Criteria

### User Story 1: Unified Quick Create Menu (Navbar)
- **As a** developer managing background tasks,
- **I want** a single `+ Criar ▾` action dropdown in the navigation header,
- **So that** I can trigger any creation action (Task, Cron, Queue, Worker) from anywhere without cluttering the screen.

#### BDD Acceptance Criteria (AC-1)
- **Given** the TaskManager dashboard is open,
- **When** the user clicks `+ Criar ▾` in the navbar,
- **Then** a dropdown menu appears showing: `⚡ Nova Tarefa`, `⏰ Novo Cron`, `📦 Nova Fila`, `🤖 Novo Worker`.
- **When** the user clicks any option or clicks outside,
- **Then** the corresponding modal opens and the dropdown closes smoothly.

---

### User Story 2: Explicit Queue Management
- **As a** developer,
- **I want** to register and delete queues directly from the API and UI,
- **So that** I can organize queues before dispatching workloads.

#### BDD Acceptance Criteria (AC-2)
- **Given** a valid queue name `reports-asia`,
- **When** `POST /api/queues` is called with `{"name": "reports-asia"}`,
- **Then** `tm:queues` in Redis contains `reports-asia`, a `queue:created` event is published, and `200 OK` is returned.
- **When** `DELETE /api/queues/reports-asia` is called and the queue is empty,
- **Then** `reports-asia` is removed from `tm:queues` and `200 OK` is returned.

---

### User Story 3: Micro-Action Icon Buttons & Row Hover in Tables
- **As a** user viewing tables of tasks, schedules, workers, and DLQ,
- **I want** compact, intuitive icon action buttons with tooltips that highlight on row hover,
- **So that** tables are calm, readable, and non-cluttered.

#### BDD Acceptance Criteria (AC-3)
- **Given** a table row in Tasks, Schedules, DLQ, or Workers,
- **When** rendered,
- **Then** actions appear as micro-icon buttons (`⚡`, `⏰`, `⏸`, `▶`, `🗑`, `🔍`) styled with hairline borders (`#23252a`), surface `#0f1011`, and hover states matching `DESIGN.md`.

---

### User Story 4: Command Palette (`Ctrl+K` / `⌘K`)
- **As a** power user,
- **I want** to press `Ctrl+K` or `Cmd+K` to search actions, navigate tabs, and launch modals,
- **So that** I can navigate the application at lightning speed.

#### BDD Acceptance Criteria (AC-4)
- **Given** the dashboard is focused,
- **When** the user presses `Ctrl+K` or `Cmd+K`,
- **Then** a command palette modal opens with a search input and list of instant actions.
