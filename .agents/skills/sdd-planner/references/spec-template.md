# Specification Template (spec.md)

# Specification: [Feature Name]

## 1. User Stories
- **US-1**: As a `[role]`, I want `[action]`, so that `[benefit]`.

## 2. Acceptance Criteria (BDD)
### AC-1: [Scenario Name]
- **Given** [initial state or preconditions]
- **When** [trigger event occurs]
- **Then** [expected verifiable outcome]

### AC-2: [Error Scenario]
- **Given** [invalid input or network error]
- **When** [action attempted]
- **Then** [graceful error response with specific code/message]

## 3. Verification Sensors
| Sensor | Command / Target | Success Threshold |
|---|---|---|
| Linter | `npm run lint` | 0 errors, 0 warnings |
| Tests | `npm test -- feature.test.ts` | 100% pass |
| Build | `npm run build` | Clean exit 0 |

## 4. UI & Design System Tokens (If Frontend/UI in Scope)
- **Target Components**: Reference tokens from `DESIGN.md` (e.g. `button-primary`, `feature-card`).
- **Color Palette**: Use `{colors.primary}`, `{colors.surface-1}`, `{colors.ink}` (no uncalibrated hex values).
- **Typography & Spacing**: Conforming to `{typography.body}`, `{spacing.md}`, `{rounded.md}`.
