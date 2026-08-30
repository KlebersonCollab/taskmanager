---
trigger: always_on
---

<!-- TOKEN_OPTIMIZATION:START -->
# Token Optimization Rules

Output verbosity rules calibrated by model capability tier.
These rules ensure cost-efficient use of AI models without sacrificing quality.

> **Governance Exception**: These brevity rules apply to conversational responses in chat. Formal SDD governance artifacts (such as `Verification Report` in `sdd-review`, `STATE.md` in `sdd-planner`, and AC tables) MUST preserve their full contract structure.

## Output Rules by Tier

### Research Tier (cheapest — maximize context for work, not chatter)
- Output code or diffs directly, avoid excessive narrative
- Minimal conversational status: concise summaries instead of verbose preamble
- No decorative markdown or emoji abuse in conversational chat
- Combine outputs into one response
- No unnecessary "Next Steps" sections in plain chat
- No repeating back what was asked

### Standard Tier (balanced — brief summaries)
- Brief summaries (2-3 sentences max) for status updates
- Code with inline comments (no separate redundant explanation blocks)
- Report only: what changed, what passed, what failed
- Skip conversational preamble and transitions

### Core Tier (most capable — full reasoning when needed)
- Full explanations welcome for complex decisions and architectural trade-offs
- Document reasoning for non-obvious choices
- Detailed analysis for bug investigations
- Maintain high precision without conversational filler

<!-- TOKEN_OPTIMIZATION:END -->