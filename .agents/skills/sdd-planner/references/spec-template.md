# Specification Template (spec.md)

# Specification: [Feature Name]

## 1. User Stories
- **US-1**: As a `[role]`, I want `[action]`, so that `[benefit]`.

## 2. Business Rules & Invariants
- **BR-1**: [Core rule description and execution conditions]
- **BR-2**: [Boundary constraint, valid formats, or prohibited states]

## 3. Acceptance Criteria (BDD)

### Happy Path (Success Scenarios)
- **AC-1: [Primary Success Scenario]**
  - **Given** [initial state or preconditions]
  - **When** [trigger event occurs]
  - **Then** [expected verifiable outcome]

### Input & Validation Scenarios
- **AC-2: [Invalid Input Scenario]**
  - **Given** [field X with invalid or out-of-bounds value]
  - **When** [submission or action attempted]
  - **Then** [rejection with specific error code and message]

### Edge Cases & Exceptions (Resilience)
- **AC-3: [Error / Failure Scenario]**
  - **Given** [dependency failure, missing entity, or race condition]
  - **When** [action requested]
  - **Then** [graceful recovery, state rollback, or fallback response]

## 4. Test Data & Boundary Matrix
| Parameter / Field | Valid Inputs (Happy) | Invalid / Boundary Inputs (Edge) |
|---|---|---|
| `sample_field` | `["valid_value_1", "valid_value_2"]` | `["", null, "> max_length", -1]` |

## 5. Verification Sensors
| Sensor | Command / Target | Success Threshold |
|---|---|---|
| Linter | `npm run lint` | 0 errors, 0 warnings |
| Tests | `npm test -- feature.test.ts` | 100% pass |
| Build | `npm run build` | Clean exit 0 |

## 6. UI & Design System Tokens (If Frontend/UI in Scope)
- **Target Components**: Reference tokens from `DESIGN.md` (e.g. `button-primary`, `feature-card`).
- **Color Palette**: Use `{colors.primary}`, `{colors.surface-1}`, `{colors.ink}` (no uncalibrated hex values).
- **Typography & Spacing**: Conforming to `{typography.body}`, `{spacing.md}`, `{rounded.md}`.
