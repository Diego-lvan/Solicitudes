---
name: verify
description: Use before any claim that work is complete, fixed, or passing — before checking off a task in status.md, before committing, before opening a PR, before saying "done". Requires running the verification command and reading its output before making the claim. Evidence before assertions, always.
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in the current message, you cannot claim it passes.

## The gate

Before claiming any status or expressing satisfaction:

1. **Identify** — what command proves this claim?
2. **Run** — execute the full command, fresh, complete
3. **Read** — full output, exit code, failure count
4. **Verify** — does the output confirm the claim?
   - If no → state the actual status with evidence
   - If yes → state the claim with evidence
5. **Only then** — make the claim

Skipping any step = lying, not verifying.

## Common claims and what they require

| Claim | Requires | Not sufficient |
|---|---|---|
| "Tests pass" | Test command output: 0 failures, current run | A previous run; "should pass" |
| "Linter clean" | Linter output: 0 errors, current run | Partial check, extrapolation |
| "Build succeeds" | Build command exits 0 | Linter passed, "logs look fine" |
| "Bug fixed" | Test that reproduced the bug now passes | Code changed, "should be fixed now" |
| "Regression test works" | Red→green cycle verified (revert fix, see fail; re-apply, see pass) | Test passes once |
| "Subagent completed" | VCS diff shows the actual changes | Subagent reported "success" |
| "Requirements met" | Line-by-line checklist against the spec | Tests pass |
| "Initiative section done" | All status.md tasks in section checked + tests + review | Last task checked |

## Red flags — STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", "Looks good!")
- About to commit / push / open a PR without running the verification
- Trusting a subagent's success report without checking the diff
- Relying on partial verification ("the package I touched compiles, so the build is fine")
- "Just this once"
- Tired and wanting to be done
- **Any wording that implies success without having run the verification in this message**

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "Should work now" | Run the verification. |
| "I'm confident" | Confidence ≠ evidence. |
| "Just this once" | No exceptions. |
| "Linter passed" | Linter ≠ compiler ≠ tests. |
| "Subagent said success" | Verify independently. |
| "I'm tired" | Exhaustion ≠ excuse. |
| "Partial check is enough" | Partial proves nothing. |
| "Different words so the rule doesn't apply" | Spirit over letter. |

## Key patterns

**Tests:**
```
✅ [run test command] [see: 34/34 pass, exit 0] → "All tests pass."
❌ "Should pass now" / "Looks correct"
```

**Regression tests (TDD red-green):**
```
✅ Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore fix → Run (pass)
❌ "I added a regression test" (without the red-green cycle verified)
```

**Build:**
```
✅ [run build] [see: exit 0] → "Build passes."
❌ "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
✅ Re-read the relevant plan/spec → list each acceptance criterion → verify each → report any gaps
❌ "Tests pass, must be done"
```

**Subagent delegation:**
```
✅ Subagent reports done → check the VCS diff → verify the changes match the brief → report actual state
❌ Trust the subagent's self-report
```

## Why this matters

Claims without evidence destroy trust. Once "I verified it" can mean "I assumed", every other status report becomes worthless. The user has to re-verify everything you said, which is worse than if you'd just said "I haven't run it yet."

Honesty is also faster: an admitted gap can be filled in 30 seconds; a false completion claim becomes a bug report later, then a debugging session, then a redirect, then rework.

## When to apply

Always, before:
- Any phrasing of "complete", "done", "fixed", "ready", "passing"
- Any expression of satisfaction
- Any positive statement about the state of the work
- Committing, pushing, opening a PR
- Marking a status.md task `[x]`
- Moving on to the next task
- Delegating to a subagent and claiming the subagent finished

The rule applies to:
- Exact phrases
- Paraphrases and synonyms
- Implications of success
- Any communication suggesting completion or correctness

## Bottom line

**No shortcuts.**

Run the command. Read the output. Then state the result.

This is non-negotiable.
