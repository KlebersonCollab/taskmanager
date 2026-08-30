<!-- QUALITY_ENFORCEMENT:START -->
# Quality Enforcement Rules

**CRITICAL**: These rules are NON-NEGOTIABLE and MUST be followed without exception.

## Absolute Prohibitions

### Test Bypassing - STRICTLY FORBIDDEN
- NEVER use .skip(), .only(), or .todo() to bypass failing tests
- NEVER comment out failing tests
- NEVER use @ts-ignore, @ts-expect-error, or similar to hide test errors
- NEVER mock/stub functionality just to make tests pass without fixing root cause
- FIX the actual problem causing test failures

### Git Hook Bypassing - STRICTLY FORBIDDEN  
- NEVER use --no-verify flag on git commit
- NEVER use --no-verify flag on git push
- NEVER disable or skip pre-commit hooks
- NEVER disable or skip pre-push hooks
- FIX the issues that hooks are detecting

### Test Implementation - STRICTLY FORBIDDEN
- NEVER create boilerplate tests that don't actually test behavior
- NEVER write tests that always pass regardless of implementation
- NEVER write tests without assertions
- NEVER mock everything to avoid testing real behavior
- WRITE meaningful tests that verify actual functionality

### Problem Solving Approach - REQUIRED
- DO NOT seek the simplest bypass or workaround
- DO NOT be creative with shortcuts that compromise quality
- DO solve problems properly following best practices
- DO use proven, established solutions from decades of experience
- DO fix root causes, not symptoms

### Temporary Files and Scripts - STRICTLY CONTROLLED
- **NEVER** create temporary test files, log dumps, or ad-hoc debug files in the project root or source directories.
- **NEVER** leave temporary files after use — all agent-generated ephemeral files MUST be cleaned up immediately.
- **ALWAYS** store ephemeral scratch scripts in the agent's artifact `scratch/` directory or inside `/scripts` if the project uses a dedicated scripts directory.
- **ALWAYS** remove temporary debug files before completing a task or marking work as complete.

**Why This Matters:**
LLM assistants often create temporary files for debugging but forget to remove them, accumulating junk files that pollute the repository. All scratch work MUST be done in isolated scratch/scripts paths and cleaned up immediately.

**Examples:**
- ❌ Creating `test.js`, `debug.log`, `temp.json` in project root or src/
- ❌ Leaving test files after debugging
- ✅ Using the agent's `scratch/` directory for ephemeral experiments
- ✅ Cleaning up all temporary scratch files immediately after verification

### Spec-Code Drift Prevention (Constitutional SDD) - STRICTLY ENFORCED
- **NEVER** commit production code modifications, new source files, or route handlers that are not explicitly declared in an active feature specification under `.specs/features/<feature-id>/tasks.md`.
- **NEVER** bypass the Pre-Commit Spec Drift Sensor (`check-spec-drift.js`) using `--no-verify` or manual hook disabling.
- **ALWAYS** declare target file boundaries in `tasks.md` before executing implementation changes.
- **ALWAYS** ensure the pre-commit hook passes with 0 orphaned/drifting files.

## Enforcement

These rules apply to ALL implementations:
- Bug fixes
- New features  
- Refactoring
- Documentation changes
- Any code modifications

**Violation = Implementation Rejected**

<!-- QUALITY_ENFORCEMENT:END -->