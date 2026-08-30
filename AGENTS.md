# AGENTS.md

## Purpose

This document defines the mandatory execution workflow for all agents and skills used during task execution.
The objective is to enforce a **Spec Driven Development (SDD)** lifecycle and prevent uncontrolled execution.

---

# CRITICAL: Project Context Loading — BLOCKING GATE

**This is a HARD GATE. No implementation action may proceed until context is established.**

**MANDATORY**: At the START of every session, execute this sequence:

1. **Memory Recall**: Load persistent memory via `sdd-memory` from `.agents/memory/memory_graph.jsonl`.
2. **Read Project Context**: Check `.specs/project/CONTEXT.md` (Domain Glossary / Project Context) and `.specs/codebase/` (Technical Map).
3. **Check Knowledge Base**: Read `.specs/knowledge/<type>s/<slug>.md` for known patterns/anti-patterns.
4. **Check Design System (Frontend/UI)**: If the project or task involves Frontend, UI, CSS, or UX, read `DESIGN.md` at the project root for design tokens, typography, colors, and component styles.
5. **Evaluate Context State**:
   - **If `.specs/project/CONTEXT.md` does not exist or has empty placeholders `<!-- PREENCHER ...`**:
     → Trigger **Auto-Discovery Protocol** (read-only discovery, generate context, confirm with user).
   - **If context is complete**:
     → Proceed with standard SDD lifecycle.

---

## Auto-Discovery Protocol (MANDATORY when context is missing/incomplete)

When `.specs/project/CONTEXT.md` is missing or contains unfilled placeholders, execute this sequence:

### Step A: Discover (Read-Only)
1. **Detect Project Type**: Check for lock files (`package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, etc.).
2. **Map Directory Structure**: Inspect folder organization and entry points.
3. **Identify Tech Stack**: Read config files to determine language, framework, linters, and test runners.
4. **Extract Conventions**: Analyze existing code for naming conventions, import patterns, and error handling.

### Step B: Fill & Populate Context
5. **Populate Context**: Create or update `.specs/project/CONTEXT.md` and codebase artifacts under `.specs/codebase/` (`STACK.md`, `ARCHITECTURE.md`, `CONVENTIONS.md`, `TECHNICAL-MAP.md`).

### Step C: Validate with User
6. **Present Discovery Summary**: Show the user what was discovered and confirm domain/technical assumptions before proceeding.

---

## Specification & Artifact Architecture

Artifacts are strictly partitioned across 4 distinct layers:

```
.
├── .agents/
│   ├── memory/
│   │   └── memory_graph.jsonl      # Cross-session recall (entities, relations, observations)
│   ├── rules/                      # System rules (Tier 1 Prohibitions, Quality Enforcement, Token Opt)
│   ├── scripts/                    # Governance & sensor scripts (check-spec-drift.js, install-hooks.js)
│   └── skills/                     # Specialized agent capabilities
├── .specs/
│   ├── codebase/                   # Brownfield reality (STACK, ARCHITECTURE, CONVENTIONS, TECHNICAL-MAP)
│   ├── project/                    # Vision & domain context (PROJECT, ROADMAP, STATE, CONTEXT, ADRs/)
│   ├── features/<feature-id>/      # Active feature specs (plan.md, spec.md, tasks.md)
│   └── knowledge/                  # Curated patterns/ and anti-patterns/
```

---

# Complete Capabilities & Skill Routing Matrix

Use this matrix to route every user request to the appropriate skill:

| Intent / Request Type | Primary Skill | Supporting Skills & Tools | Target Artifacts |
| :--- | :--- | :--- | :--- |
| **Cross-Session Memory** | `sdd-memory` | `view_file`, `replace_file_content` | `.agents/memory/memory_graph.jsonl` |
| **Codebase Mapping & Research** | `sdd-explorer` | `search`, `arxiv`, `read_url_content` | `.specs/codebase/` (`STACK.md`, `ARCHITECTURE.md`, `CONVENTIONS.md`, `TECHNICAL-MAP.md`) |
| **Feature Planning & Scoping** | `sdd-planner` | `grill-me` (Phase 0 Align) | `.specs/features/<id>/` (`plan.md`, `spec.md`, `tasks.md`), `.specs/project/ADRs/` |
| **Stress-testing Requirements** | `grill-me` | `ask_question`, `view_file` | Direct interactive interview → Feeds `sdd-planner` |
| **Feature Implementation (TDD)** | `sdd-executor` | `refactor`, `debug`, run sensors | Source code, test files, `tasks.md` (Evidence column) |
| **Bug Investigation / Diagnosis** | `debug` | `search`, `run_command` | Root cause analysis → Feeds `sdd-planner` if replan needed |
| **Code Restructuring / Clean Code** | `refactor` | `sdd-executor` | Source code with non-regression tests |
| **Specification & Quality Audit** | `sdd-review` | Test runner, linter, build sensors, drift sensor | Formal Verification Report with Verdict in chat |
| **UI / Frontend / Design System** | `sdd-executor` / `sdd-planner` | `DESIGN.md`, `view_file` | Source code matching `DESIGN.md` tokens |
| **Symbol & Pattern Lookup** | `search` | `grep_search`, `find_by_name` | Direct file:line references |
| **Scientific / Algorithmic Papers** | `arxiv` | `read_url_content`, curl | Paper summaries and BibTeX |
| **Skill Authoring & Extension** | `write-a-skill` | — | `.agents/skills/<skill-name>/SKILL.md` |

---

# Global Execution Rules (Strict SDD Lifecycle)

## Priority Order & Execution Flow

```text
0. sdd-memory   (Load at session start; persist insights at session end)
1. sdd-explorer (Brownfield discovery & codebase mapping)
2. sdd-planner  (Feature planning: plan.md, spec.md, tasks.md with MetaGPT 7-column schema)
3. sdd-executor (Atomic TDD implementation, SWE-agent ACI & AgentCoder test immutability)
4. sdd-review   (Sensor audit, Spec Drift check, AC verification & verdict)
```

---

## Rule 1 — Exploration and Knowledge Tasks
If a task involves research, investigation, comparative analysis, or architecture exploration:
* **MUST USE**: `skill: sdd-explorer` (supported by `search` or `arxiv`).
* **Responsibilities**: Map code reality, produce findings in `.specs/codebase/`, reduce uncertainty.
* **Reference Guide**: Consult [Brownfield Mapping Guide](.agents/skills/sdd-explorer/references/brownfield-mapping.md).
* **Forbidden**: Writing production code or modifying project implementation files during exploration.

---

## Rule 2 — Planning is Mandatory Before Development (MetaGPT SOP)
If a task involves writing code, refactoring, feature implementation, bug fixing, or API changes:
* **MUST FIRST USE**: `skill: sdd-planner` (supported by `grill-me` in Phase 0).
* **Responsibilities**: Define scope (`plan.md`), BDD acceptance criteria with sensors (`spec.md`), and strict 7-column atomic tasks with dependency mapping (`tasks.md`) under `.specs/features/<feature-id>/`. Create numbered ADRs in `.specs/project/ADRs/` for structural choices.
* **Reference Templates**: Consult [plan-template.md](.agents/skills/sdd-planner/references/plan-template.md), [spec-template.md](.agents/skills/sdd-planner/references/spec-template.md), [task-template.md](.agents/skills/sdd-planner/references/task-template.md), [grilling-session.md](.agents/skills/sdd-planner/references/grilling-session.md).
* **Forbidden**: Direct execution without approved planning (`User Request → sdd-executor` is strictly invalid).

---

## Rule 3 — Execution Requires Approved Planning (SWE-agent ACI & AgentCoder Decoupling)
Only after planning is established may implementation proceed:
* **MUST USE**: `skill: sdd-executor` (supported by `refactor` and `debug`).
* **Responsibilities**: Follow `tasks.md` sequentially, apply TDD cycle, use surgical contiguous block replacement (`replace_file_content`), run sensors (lint, test, build), record commit/test evidence.
* **Test Immutability**: The executor is strictly forbidden from weakening, altering, or commenting out test assertions to pass failing tests (Prohibition 9).
* **Reference Principles**: Consult [Coding Principles](.agents/skills/sdd-executor/references/coding-principles.md).
* **Safety Valve**: If a task touches >3 files unexpectedly or hits critical risk paths, PAUSE and request a replan from `sdd-planner`.
* **Forbidden**: Modifying `plan.md` or `spec.md` directly; blind-overwriting entire files (Prohibition 8); marking tasks complete without sensor evidence.

---

## Rule 4 — Review is Mandatory After Development (Pre-Commit Spec Drift Sensor)
After any implementation activity:
* **MUST USE**: `skill: sdd-review`.
* **Responsibilities**: Run sensors (Spec Drift Sensor, Linter, Test Suite, Build), audit test diff integrity against assertion tampering, audit each AC against concrete code lines (`file:///...`), generate formal Verification Report with Verdict (`APPROVED` / `REQUESTS CHANGES`).
* **Reference Standards**: Consult [BDD Guide](.agents/skills/sdd-review/references/bdd-guide.md).
* **Forbidden**: Approving work without sensor evidence, approving when spec drift is detected, or skipping edge-case checks.

---

# Subagent Delegation Strategy

When handling complex tasks, use subagents strategically:

1. **Subagent `research` (Read-only)**:
   - Use for extensive codebase exploration, searching external documentation, or surveying large modules.
   - Keeps the main context clean from intermediate search dumps.
2. **Subagent `self` (Full capability)**:
   - Use for isolated iterative TDD loops in `sdd-executor` or heavy refactoring sub-tasks.
3. **Main Context Execution**:
   - Use for planning alignment (`sdd-planner`, `grill-me`), interactive review verdicts (`sdd-review`), and user communications.

---

# Core Directives & Quality Standards

1. **Research Before Implementing — Never Guess**:
   - State what you KNOW, what you DON'T KNOW, research the unknown, and only then implement.
   - *"Source X does Y at file:line, we do Z, the difference causes W"* is the required standard.
2. **Zero Code Duplication**: Search existing modules before implementing new logic.
3. **No Shortcuts, Stubs, or Placeholders**: Never write TODOs, stubs, or mock assertions to pass tests.
4. **Governed Deletions**: Never delete project files without explicit user approval (see `.agents/rules/TIER1_PROHIBITIONS.md`).
5. **Clean Scripts & Scratchpad**: Use isolated scratch directories for ephemeral tests and clean them up immediately.
6. **Design System Invariance**: Whenever writing UI code, CSS, or frontend components, strictly adhere to tokens, typography, colors, and layout scales defined in `DESIGN.md`. Never invent arbitrary hex codes or uncalibrated styles.
7. **Constitutional Spec Drift Invariance**: Every production code modification must be explicitly mapped in an active `.specs/features/<id>/tasks.md` and validated by the pre-commit spec drift sensor (`check-spec-drift.js`).
