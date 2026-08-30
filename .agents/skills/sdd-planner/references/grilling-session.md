# Grilling Session Protocol (Phase 0: ALIGN)

## Purpose
Stress-test requirements, resolve ambiguities, eliminate fuzzy terminology, and clarify user intent before drafting specs.

## Process
1. **Challenge Assumptions**:
   - What problem does this solve for the user?
   - What happens on failure or invalid input?
   - What are the non-obvious constraints (scaling, latency, security)?
2. **Resolve Fuzzy Language**:
   - Replace terms like "fast", "flexible", "intuitive" with exact metrics and invariants.
3. **Align Terminology with `CONTEXT.md`**:
   - Ensure every domain entity has a canonical name in the Domain Glossary.
4. **Identify ADR Triggers**:
   - Is this choice hard to reverse?
   - Is it surprising without context?
   - Is it the result of a significant trade-off?
