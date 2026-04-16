---
name: tdd
description: Use when implementing any feature or bugfix where correctness must be provable — security-sensitive code, business logic with subtle invariants, anything where "looks right" isn't enough. Stricter than /implement's flexible mode; enforces RED-GREEN-REFACTOR with no exceptions. Invoke explicitly when the work warrants the discipline.
---

# Test-Driven Development (Strict)

## Overview

Write the test first. Watch it fail. Write the minimum code to pass it. Refactor.

**Core principle:** if you didn't watch the test fail, you don't know that it tests the right thing.

**Violating the letter of these rules is violating the spirit of these rules.**

This is the strict variant. The project's `/implement` skill allows flexible TDD (test-first OR code-first as long as both exist before the task is marked done). Invoke `/tdd` when you want the iron law: no production code without a failing test first, period.

## When to use this skill (over flexible /implement)

- Anything security- or correctness-critical
- Bug fixes — always (the test reproduces the bug, then proves the fix)
- Refactors of logic with non-obvious invariants
- Code where "compiles and looks reasonable" is not sufficient evidence

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Wrote code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from the test.

## Red-Green-Refactor

```
RED      → write the failing test
verify   → it fails for the right reason
GREEN    → minimal code to pass
verify   → it passes; nothing else broke
REFACTOR → clean up while staying green
NEXT     → next failing test
```

### RED — write the failing test

One behavior. Clear name. Real code paths (no mocks unless unavoidable).

A test should *demonstrate the desired API* — if writing the test feels awkward, the design is probably wrong, not the test.

### Verify RED — watch it fail

**MANDATORY. Never skip.**

Run the specific test. Confirm:
- It **fails** (not errors out from a typo or import problem)
- The failure message matches what you expected
- It fails because the feature is missing, not because of an unrelated compile error

Test passed on first run? You're testing existing behavior — fix the test.
Test errored from a typo? Fix the typo and re-run until it fails for the *right* reason.

### GREEN — minimal code

Smallest code that makes the test pass. No flags, no options, no "while I'm here" features. Resist the urge to add parameters, configurability, or generality the test doesn't demand.

### Verify GREEN — watch it pass

**MANDATORY.**

Run the test. Run the rest of the suite. Confirm:
- The new test passes
- Nothing else broke
- Output is pristine — no warnings, no leftover debug prints

### REFACTOR — clean up

Only after green. Remove duplication, improve names, extract helpers. Don't add behavior. Tests stay green throughout.

### Repeat

Next failing test for the next slice of behavior.

## Good tests

| Quality | Good | Bad |
|---|---|---|
| **Minimal** | One thing. "and" in the name? Split it. | Asserts five unrelated things |
| **Clear name** | Describes the behavior under test | `test1`, `it_works` |
| **Shows intent** | Demonstrates the API a reader would want | Obscures what the code should do |
| **Real code** | Exercises real paths with real inputs | Asserts on mock call counts |

## Bug-fix workflow (the canonical case)

1. **Reproduce as a test.** The smallest test that exhibits the reported bug.
2. **Run it.** It must fail with the same symptom the user reported. If it doesn't, you haven't reproduced the bug — go back.
3. **Fix.** Minimal change to make the test pass.
4. **Verify.** Test passes. Other tests still pass.
5. **Optional: regression check.** Revert the fix, watch the test fail, re-apply, watch it pass. This proves the test actually catches the regression.

Never fix a bug without a test. The test is what stops it from coming back.

## Why test order matters

**"I'll write tests after to verify it works."**
Tests written after pass immediately. Passing immediately proves nothing — they could test the wrong thing, the implementation rather than the behavior, or skip the edge cases you forgot. You never saw them catch anything.

**"I already manually tested all the edge cases."**
Manual testing is ad-hoc. No record, can't re-run on every change, easy to forget cases under pressure.

**"Deleting hours of code is wasteful."**
Sunk cost. The time is gone. The choice now is: delete and rewrite with TDD (high confidence), or keep it and bolt on tests (low confidence, likely bugs).

**"Tests-after achieve the same goal — it's spirit not ritual."**
No. Tests-after answer "what does this do?" Tests-first answer "what should this do?" Tests-after are biased by the implementation: you test what you built, not what was required.

## Common rationalizations

| Excuse | Reality |
|---|---|
| "Too simple to test" | Simple code breaks. The test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "I already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "Deleting hours is wasteful" | Sunk cost. Keeping unverified code is debt. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing-after. Delete means delete. |
| "Need to explore first" | Fine — throw the spike away, then start with TDD. |
| "Test hard to write = unclear design" | Listen to the test. Hard to test = hard to use. Fix the design. |
| "TDD will slow me down" | TDD is faster than debugging in production. |
| "Existing code has no tests" | You're improving it. Add tests for the parts you touch. |
| "Manual is faster" | Manual misses edge cases and re-runs forever every change. |

## Red flags — STOP and start over

- Production code written before a test
- Test written after implementation
- Test passed on first run
- Can't explain why the test failed
- "I'll add tests later"
- "Just this once"
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "It's spirit not ritual"
- "Keep as reference / adapt existing code"
- "Already spent N hours, deleting is wasteful"
- "TDD is dogmatic, I'm being pragmatic"
- "This case is different because…"

**All of these mean: delete the production code, start over from RED.**

## When stuck

| Problem | Action |
|---|---|
| Don't know how to test it | Write the test you wish you could write — let it drive the API. |
| Test has 50 lines of setup | Design is too coupled. Use dependency injection, narrow the interface. |
| Need to mock everything | Same — too coupled. Listen to the test. |
| Can't decide what to test first | The simplest case that could possibly fail. Build from there. |

## Verification checklist

Before claiming a task done:

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for the right reason (missing feature, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass — full package, not just the one file
- [ ] Output pristine (no warnings, no leftover debug output)
- [ ] Real code in tests; mocks only where unavoidable (network, time, randomness)
- [ ] Edge cases and error paths covered

Can't check all boxes? You skipped TDD. Start over.

## Integration with this project's flow

- `/implement` is the default execution skill and uses *flexible* TDD. Use `/tdd` when you want strict.
- After completing the strict cycle for a task, update `status.md` and append to `changelog.md` per the SDD flow.
- For bug fixes that aren't part of an active initiative, the test still goes in first, the fix follows, and the change is logged in the relevant initiative's `changelog.md` if there is one.

## Final rule

```
Production code → test exists and was watched failing first
Otherwise → not TDD
```

No exceptions without explicit user permission.
