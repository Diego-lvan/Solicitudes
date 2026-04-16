---
name: debug
description: Use when encountering any bug, test failure, or unexpected behavior — before proposing any fix. Forces root-cause investigation before fix attempts. Especially required under time pressure, after a previous fix failed, or when "just one quick patch" feels obvious.
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask real issues.

**Core principle:** always find the root cause before attempting a fix. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT-CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to use

For any technical issue: test failure, production bug, unexpected behavior, performance problem, build failure, integration issue.

**Especially when:**
- Under time pressure (emergencies make guessing tempting)
- A "just one quick fix" feels obvious
- A previous fix didn't work
- Multiple fixes have already been attempted
- You don't fully understand the issue

**Don't skip when:**
- The issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed *now* (systematic is faster than thrashing)

## The four phases

You MUST complete each phase before moving to the next.

---

### Phase 1 — Root cause investigation

**Before attempting any fix:**

**1. Read the error carefully.**
Don't skim. Stack traces and error messages often contain the exact answer. Note line numbers, file paths, error codes.

**2. Reproduce consistently.**
Can you trigger it reliably? What are the exact steps? Does it happen every time? If not reproducible → gather more data, don't guess.

**3. Check what changed.**
Recent commits, recent dependency upgrades, config changes, environment differences. The cause is usually in the diff.

**4. Gather evidence at component boundaries.**
When the system has multiple layers (request → handler → service → repository → DB; build → packager → signer; producer → queue → consumer), the bug lives at one boundary. Add diagnostic instrumentation at *each* boundary:

- Log what enters each component
- Log what exits each component
- Verify config / env / context propagates correctly
- Capture state at each layer

Run once. Read the evidence. Identify *which* boundary fails. Then investigate that specific boundary. Don't propose fixes until you know where the break is.

**5. Trace data flow backward.**
When the symptom is deep in the call stack: where does the bad value originate? What called this with the bad value? Keep tracing up until you find the source. Fix at the source, not at the symptom.

---

### Phase 2 — Pattern analysis

**1. Find a working example.**
Locate similar code in the same codebase that works. What works that resembles what's broken?

**2. Read the reference completely.**
If you're applying a pattern (an existing one in the codebase or an external reference), read it fully — don't skim. Partial understanding guarantees bugs.

**3. List every difference.**
Between working and broken. However small. Don't pre-dismiss differences as "couldn't possibly matter."

**4. Understand dependencies.**
What other components, settings, env vars, or invariants does the working code rely on?

---

### Phase 3 — Hypothesis and minimal test

**1. Form one hypothesis.**
State it explicitly: "I think *X* is the cause because *Y*." Write it down. Be specific.

**2. Test it minimally.**
The smallest possible change that would prove or disprove the hypothesis. One variable at a time. Don't bundle.

**3. Verify before continuing.**
Did it work? → Phase 4.
Didn't work? → form a *new* hypothesis. Don't pile fixes on top of fixes.

**4. When you don't know, say so.**
"I don't understand X." Don't pretend. Ask, or research more.

---

### Phase 4 — Fix at the root cause

**1. Create a failing test that reproduces the bug.**
Smallest reproduction possible. Automated if the framework allows; a one-off script if not. The test must exist before the fix.

**2. Implement a single fix.**
Address the root cause. One change. No "while I'm here" cleanups, no bundled refactors.

**3. Verify.**
The test now passes. Nothing else broke. The user-reported symptom is actually gone.

**4. If the fix doesn't work — STOP.**
Count: how many fix attempts have you made?
- < 3 → return to Phase 1, re-analyze with the new information
- ≥ 3 → **stop and question the architecture** (next step)

Do not attempt fix #4 without an explicit architectural conversation.

**5. If 3+ fixes failed — question the design.**
Pattern signs of an architectural problem:
- Each fix uncovers a new shared-state / coupling / leaky-abstraction problem somewhere else
- "The fix would require massive refactoring"
- Each fix creates new symptoms in a different place

**Stop and discuss with the user.** This isn't a failed hypothesis — it's wrong architecture. Continuing to patch is sunk-cost behaviour.

---

## Red flags — STOP and follow the process

If you catch yourself thinking:

- "Quick fix for now, I'll investigate later"
- "Just try changing X and see what happens"
- "Add multiple changes and run the tests"
- "Skip the test, I'll verify manually"
- "It's probably X, let me fix that"
- "I don't fully understand it but this might work"
- "The pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when 2+ have already failed)**
- **Each fix uncovers a new problem somewhere else**

**All of these mean: STOP, return to Phase 1.**

## User signals you're doing it wrong

- "Is that not happening?" — you assumed without verifying
- "Will it show us…?" — you should have added evidence-gathering
- "Stop guessing" — you're proposing fixes without understanding
- "Think harder about this" — question fundamentals, not just symptoms
- "We're stuck?" (frustrated) — your approach isn't working

**When you see these → return to Phase 1.**

## Common rationalizations

| Excuse | Reality |
|---|---|
| "Issue is simple, no need for process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is *faster* than guess-and-check thrashing. |
| "Just try this first, then investigate" | The first fix sets the pattern. Do it right from the start. |
| "I'll write a test after the fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the gist" | Partial understanding guarantees bugs. Read it fully. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't patch again. |

## Quick reference

| Phase | Activities | Done when |
|---|---|---|
| **1. Root cause** | Read errors, reproduce, check diff, instrument boundaries, trace backward | You understand WHAT and WHY |
| **2. Pattern** | Find working examples, read references fully, list differences | You can articulate every relevant difference |
| **3. Hypothesis** | One theory, minimal test | Confirmed or new hypothesis |
| **4. Fix** | Failing test → single fix → verify | Bug gone, tests pass |

## When investigation reveals "no root cause"

If systematic investigation genuinely shows the issue is environmental, timing-dependent, or external (not in your code), you've completed the process. Document what you investigated, implement appropriate handling (retry, timeout, clearer error message), and add monitoring.

But: 95% of "no root cause" claims are incomplete investigation. Be honest about which case you're in.

## Integration with this project's flow

- A bug reproduced as a failing test (Phase 4 step 1) follows the `/tdd` discipline.
- If the bug belongs to an active initiative, append findings and the fix to that initiative's `changelog.md`.
- If the investigation reveals the design itself is wrong, stop and update `plan.md` (or surface a new initiative) before patching further.
