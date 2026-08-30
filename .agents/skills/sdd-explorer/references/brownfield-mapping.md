# Brownfield Mapping Guide & Templates

This guide details the standard structure for artifacts generated under `.specs/codebase/`.

---

## 1. STACK.md

```markdown
# Technology Stack

## Core Language & Runtime
- **Language**: [e.g., TypeScript 5.4, Python 3.12, Rust 1.77]
- **Runtime / Framework**: [e.g., Node.js 20 LTS, FastAPI 0.110, Axum]
- **Package Manager**: [e.g., pnpm, pip/uv, cargo]

## Dependencies
- **Production**:
  - `package-name`: `version` — Purpose
- **Development & Tooling**:
  - `linter-name`: `version` — Configuration
  - `formatter-name`: `version`

## Testing Infrastructure
- **Framework**: [e.g., Vitest, Pytest, Cargo Test]
- **Sensor Commands**:
  - Lint: `npm run lint` / `flake8` / `cargo clippy`
  - Test: `npm test` / `pytest` / `cargo test`
  - Build: `npm run build` / `cargo build`
```

---

## 2. ARCHITECTURE.md

```markdown
# System Architecture

## Directory Organization
- `src/core/`: Domain models and business invariants
- `src/services/`: Application services and orchestration
- `src/adapters/`: External integrations, DB clients, HTTP routers

## Architectural Patterns
- **Pattern**: [e.g., Clean Architecture, Modular Monolith, Hexagonal]
- **Data Flow**: Request -> Controller -> Service -> Repository -> Storage

## Boundary Rules
- Services must not access external APIs directly without adapters.
- Domain models have zero external dependencies.
```

---

## 3. CONVENTIONS.md

```markdown
# Code Conventions & Idioms

## Naming Standards
- Files: `kebab-case.ts`
- Classes / Types: `PascalCase`
- Functions / Methods: `camelCase`
- Constants: `SCREAMING_SNAKE_CASE`

## Error Handling
- Use typed error classes or Result types; avoid unhandled throws.
- Always attach context to error messages.

## Formatting & Imports
- Group imports: standard library -> 3rd-party -> internal absolute paths.
```

---

## 4. CONCERNS.md

```markdown
# Critical Risks & Technical Debt

## High-Risk Areas (Mandatory Caution Paths)
- `path/to/legacy-file`: High cyclomatic complexity, lack of test coverage.

## Fragile Integrations
- Third-party API rate limits and retry policies.

## Technical Debt Items
- [ ] Item 1: Missing transaction boundaries in module X.
```

---

## 5. TECHNICAL-MAP.md

Consolidated overview combining the high-level summary of Stack, Architecture, Conventions, and Critical Concerns into a single executive technical map.
