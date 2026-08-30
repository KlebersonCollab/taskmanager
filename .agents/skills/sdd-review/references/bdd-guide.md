# BDD & Sensor Audit Guide

## 1. Audit Principles
- The Reviewer validates reality against contract specifications (`spec.md`).
- Evaluation is strictly empirical, never subjective.

## 2. Sensor Verification Gate
Run all 3 mandatory sensors:
1. **Linter**: Verify zero errors / warnings.
2. **Test Suite**: Verify all feature tests pass.
3. **Build**: Verify clean build without compilation errors.

## 3. Acceptance Criteria Mapping
For each scenario in `spec.md`:
- Locate the concrete code lines (`file:///path/to/file#L10-L30`).
- Validate that Given/When/Then conditions are satisfied.
- Document the exact evidence in the Verification Report.

## 4. UI & Design System Audit (Frontend Features)
- If UI is involved, verify adherence to `DESIGN.md`:
  - Check color palette, typography scale, spacing, and border radius against design tokens.
  - Verify interactive states (hover, focus, pressed) match component specs.
  - Flag any hardcoded off-palette styles as `REQUESTS CHANGES`.
