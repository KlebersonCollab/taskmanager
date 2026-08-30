# Implementation & Coding Principles

## 1. Safety Valve Protocol
- **Stop & Replan**: If an atomic task unexpectedly touches >3 files, hits legacy risk areas, or requires changing architectural boundaries, PAUSE immediately and request replanning from `sdd-planner`.

## 2. Test-Driven Implementation (TDD & AgentCoder Decoupling)
1. Write or run the failing test matching the Acceptance Criteria (AC).
2. Run test sensor to observe the exact failure reason.
3. **Test Immutability Rule**: Never alter test assertions or remove test cases to bypass failures. The bug is always in the production code.
4. Write the minimal clean implementation to make the test pass.
5. Refactor if needed while keeping tests green.

## 3. Atomic Commits & Evidence
- Keep commits small, descriptive, and linked to task IDs:
  `feat(auth): validate session token before renewal (TASK-02)`
- Record the commit hash or test sensor output in the `Evidence` column of `tasks.md`.

## 4. Design System Fidelity (UI / Frontend Tasks)
- When implementing UI components, CSS, or templates, load `DESIGN.md`.
- Strictly use defined tokens (colors, typography, spacing, border radii, components). Never hardcode arbitrary visual values.

## 5. Agent-Computer Interface (ACI) Protocol (SWE-agent SOTA)
- **Bounded Reading**: Always read localized slices (100–300 lines via `view_file`) immediately before editing.
- **Contiguous Block Replacement**: Use `replace_file_content` targeting verified line numbers.
- **No Blind Overwriting**: Never use whole-file overwrites on existing project files.
- **Bounded Shell Output**: When running terminal commands, filter or paginate output to avoid polluting context windows.
