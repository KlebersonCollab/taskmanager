# Tasks Template (tasks.md) — MetaGPT SOP Schema Contract

# Task List: [Feature Name]

## Sequence Guidelines (MetaGPT SOP)
- **Strict Sequential Order**: Tasks must be executed top-to-bottom without reordering or cherry-picking.
- **Atomic File Boundaries**: Each task must modify at most 1–3 specific target files.
- **Decoupled Test Setup**: Test definition / scaffolding tasks (`Type: test`) MUST precede implementation tasks (`Type: feat`).
- **Sensor Evidence Gate**: Mark complete `[x]` ONLY after passing build, lint, and test sensors with recorded evidence.

## Implementation Tasks

| Status | ID | Type | Description | Target Files | Dependencies | Evidence |
|---|---|---|---|---|---|---|
| [ ] | TASK-01 | test | [Scaffold unit tests & BDD acceptance test cases] | `tests/unit/item.test.ts` | None | |
| [ ] | TASK-02 | feat | [Define domain models and types] | `src/models/item.ts` | TASK-01 | |
| [ ] | TASK-03 | feat | [Implement service logic to pass test suite] | `src/services/item.ts` | TASK-01, TASK-02 | |
| [ ] | TASK-04 | feat | [Expose API endpoint and connect route handler] | `src/routes/item.ts` | TASK-03 | |
| [ ] | TASK-05 | review | [Audit acceptance criteria and run full sensor suite] | `src/`, `tests/` | TASK-04 | |

## Schema Dictionary
- **Status**: `[ ]` (Pending) | `[x]` (Verified Complete).
- **ID**: `TASK-01`, `TASK-02`, etc.
- **Type**: `test` | `feat` | `fix` | `refactor` | `docs` | `rules` | `skill` | `review`.
- **Target Files**: Concrete comma-separated file paths (relative to workspace root).
- **Dependencies**: Comma-separated list of preceding task IDs or `None`.
- **Evidence**: Commit hash (`git rev-parse --short HEAD`) + sensor output snippet.
