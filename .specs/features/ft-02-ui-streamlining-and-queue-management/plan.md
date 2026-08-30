# Feature Plan: UI Streamlining & Queue Management (ft-02)

## 1. Problem Statement
The TaskManager Dashboard currently suffers from button clutter across the top navigation bar and dense table rows. Furthermore, users lack a direct UI mechanism to explicitly create empty custom queues in Redis before dispatching tasks to them.

## 2. Goals & Value
- **Clean Linear-Dark Visual Hierarchy**: Replace cluttered top navbar buttons with a unified `+ Criar ▾` Action Menu and a settings/maintenance icon button.
- **Explicit Queue Management**: Add `POST /api/queues` and `DELETE /api/queues/{queue}` to allow manual queue registration in Redis.
- **Calm Table Rhythm**: Replace heavy multi-button rows in tables with compact, tooltip-enabled micro-action icon buttons with subtle hover-reveal effects (`DESIGN.md`).
- **Command Palette (`Ctrl+K`)**: Fast keyboard-driven search and action execution for power users.

## 3. Scope Boundaries
- **In Scope**:
  - `POST /api/queues` and `DELETE /api/queues/{queue}` REST endpoints.
  - Navbar redesign with unified `+ Criar ▾` dropdown and `⚙️` maintenance button.
  - New Queue modal in UI with validation.
  - Streamlined row action groups across Overview, Tasks, Schedules, DLQ, and Workers tables.
  - Command palette modal (`Ctrl+K` / `Cmd+K`).
  - Strict compliance with `DESIGN.md` tokens.
- **Out of Scope**:
  - Modifying the core async broker execution engine.
  - Changing Redis storage data schemas.
