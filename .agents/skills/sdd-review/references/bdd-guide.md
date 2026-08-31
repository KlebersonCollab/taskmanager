# BDD & Sensor Audit Guide

This guide defines the practical, empirical techniques used by the **Reviewer** to audit implementation code against feature specifications (`spec.md`), task records (`tasks.md`), and constitutional sensors.

---

## 1. Core Verification Principles

- **Contract vs. Reality**: The Reviewer compares the codebase reality directly against the contracts in `spec.md`.
- **Empirical Evidence Only**: Assertions like "looks good" or "should work" are prohibited. Every pass statement must cite a concrete command output or file/line reference.
- **Zero Tolerance for Spec Drift**: Code not mapped in `.specs/features/<id>/tasks.md` is an immediate failure.

---

## 2. Sensor Verification Gate Protocol

The Reviewer must execute all sensors in sequence and capture signal outputs:

```bash
# 1. Spec Drift Sensor (Constitutional SDD)
node .agents/scripts/check-spec-drift.js

# 2. Project Linter
npm run lint # or project-specific equivalent (cargo clippy, flake8, ruff, etc.)

# 3. Automated Test Suite
npm test # or project-specific test runner

# 4. Project Build
npm run build # or cargo build, tsc, etc.
```

If ANY sensor fails:
- Immediately stop the audit.
- Record the raw failure log in the Verification Report.
- Issue verdict `REQUESTS CHANGES`.

---

## 3. Test Integrity & Immutability Audit (Prohibition 9)

Before verifying acceptance criteria, audit the test diff against tampering:

```bash
# Inspect changes made to the test suite
git diff HEAD~1 -- tests/ # or diff against feature branch base
```

### Tampering Red Flags:
- Softened assertions (e.g., changing expected status codes or relaxed regexes).
- Commented-out test cases or skipped tests (`.skip()`, `@pytest.mark.skip`, `@ts-ignore`).
- Replaced functional assertions with trivial mocks (`expect(true).toBe(true)`).

If tampering is found, issue `REQUESTS CHANGES` citing **Prohibition 9: Test Immutability Violation**.

---

## 4. Acceptance Criteria & Invariant Mapping

Audit each contract element declared in `.specs/features/<feature-id>/spec.md`:

### A. Business Rules & Invariants (`BR-X`)
- Locate where the domain invariants are enforced in the production code.
- Verify guard clauses, state checks, and model validation logic.
- Cite the exact source line range: `[src/domain/service.ts#L45-L60](file:///path/to/src/domain/service.ts#L45-L60)`.

### B. BDD Scenarios (`AC-X`)
For each scenario category:
1. **Happy Path (Success)**: Locate the positive unit/integration test. Confirm that Given (preconditions), When (action), and Then (verifiable outcome) match the spec.
2. **Input & Validation**: Locate negative test cases. Confirm that invalid payloads or boundaries produce the exact error structure and status codes specified.
3. **Edge Cases & Resilience**: Locate exception tests. Confirm fallback, retry, or graceful error handling behaviors.

### C. Test Data & Boundary Matrix
- Check the `Test Data & Boundary Matrix` from `spec.md`.
- Verify that tests explicitly assert boundary values (e.g. `0`, `-1`, `max_length + 1`, `null`, `empty string`).

---

## 5. Tasks & MetaGPT SOP Evidence Verification

Inspect `.specs/features/<feature-id>/tasks.md`:
1. Check that all tasks are marked complete `[x]`.
2. Inspect the **Evidence** column:
   - Must contain a valid commit hash (`git rev-parse --short HEAD`).
   - Must contain a concise log snippet proving the sensor passed for that task.
3. Verify that the files edited across all commits strictly match the `Target Files` declared in `tasks.md`.

---

## 6. Frontend / Design System Audit (`DESIGN.md`)

If the feature touches UI components, HTML, CSS, or styling:
1. Open `DESIGN.md` at project root.
2. Verify:
   - Colors use defined tokens (e.g. `var(--color-primary)`, `{colors.primary}`) — no raw uncalibrated hex codes.
   - Typography, border radii, and spacing match standard design tokens.
   - Interactive component states (hover, active, disabled, focus) are fully styled.
3. Flag any arbitrary styling as `REQUESTS CHANGES`.

---

## 7. Hyperlink Formatting Standard

All evidence citations in the Verification Report MUST use clickable GitHub-flavored markdown links:
- Correct: `[item.ts#L12-L28](file:///F:/Projetos/ai-sdd-framework/src/models/item.ts#L12-L28)`
- Incorrect: `src/models/item.ts` or `line 12`
