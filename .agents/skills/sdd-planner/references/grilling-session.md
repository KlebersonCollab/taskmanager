# Grilling Session Protocol (Phase 0: ALIGN)

## Purpose
Stress-test requirements, resolve ambiguities, eliminate fuzzy terminology, and clarify user intent before drafting specs (`plan.md`, `spec.md`, `tasks.md`).

---

## The 5-Step Grilling Protocol

### 1. One Question at a Time (Decision Tree Traversal)
- Ask focused questions addressing one branch of the decision tree at a time.
- For every question, always offer a **recommended default option** prefixed with `(Recommended)` and supported by technical rationale.

### 2. Codebase-First Exploration
- Before asking the user about existing behaviors, schemas, or dependencies, **explore the codebase first** (`grep_search`, `find_by_name`, `view_file`).
- Ground questions in verified facts: *"Source X does Y at `file:line`, do we want to extend this for Z?"*

### 3. Domain & Terminology Alignment (`CONTEXT.md`)
- Detect fuzzy or subjective words (e.g., "fast", "scalable", "flexible", "intuitive") and translate them into measurable invariants.
- Ensure all domain entities and terms are recorded in `.specs/project/CONTEXT.md` (Domain Glossary).

### 4. ADR Detection & Recording
- Proactively detect architectural choices meeting any of the 3 criteria:
  1. Hard to reverse.
  2. Surprising or non-obvious without context.
  3. The result of a real trade-off.
- Create or propose an Architectural Decision Record under `.specs/project/ADRs/000X-slug.md`.

### 5. Handoff to Specification Pipeline
- Once the decision tree is fully resolved, summarize the consensus and hand off to `sdd-planner` to create `plan.md`, `spec.md`, and `tasks.md`.
