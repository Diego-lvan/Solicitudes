---
name: receive-review
description: Use when receiving code review feedback (from /review, the code-reviewer agent, or a human reviewer) before implementing the suggestions — especially if any feedback seems unclear, technically wrong, or feels like style preference. Requires verification and rigor, not performative agreement or blind compliance.
---

# Receiving Code Review

## Overview

Code review feedback is input, not orders. Your job is to evaluate each item on its merits, agree where it's right, push back where it's wrong, and never pretend to agree just to make the conversation end.

**Core principle:** evidence over deference.

## What this skill is for

Reviewers — whether the `code-reviewer` agent, the `/review` skill, or a human — make claims about your code. Some are right. Some are wrong. Some are style preferences dressed as bugs. Treat all of them the same way: as hypotheses to verify, not commands to execute.

## What this skill is **not** for

This is not "how to argue with reviewers." If a reviewer is correct, fix it immediately and thank them. The discipline here is preventing two failure modes:
- **Performative agreement** — "Good catch! Fixing now." → fix something that wasn't broken → introduce a real bug
- **Defensive dismissal** — rejecting valid feedback because the reviewer's tone was abrasive

Both are dishonest. The first is more common.

## Process

### 1. Read every comment in full before doing anything

Don't start fixing as you scroll. Read the whole review. Group items mentally:
- **Clearly correct** (real bug, missing edge case, requirement not met) → fix
- **Plausible but unverified** (might be a bug, might be a misunderstanding) → verify before deciding
- **Stylistic / preference** (would-prefer-this-name, would-prefer-this-pattern) → judgement call
- **Wrong** (reviewer misread the code or misunderstood the requirement) → push back with evidence

### 2. For each item, verify before agreeing or disagreeing

The default move on receiving feedback is to *check the claim*, not act on it.

- The reviewer says "this throws on empty input" → write a test that passes empty input. Does it actually throw?
- The reviewer says "this is O(n²)" → trace the call graph. Is it?
- The reviewer says "this doesn't match the plan" → re-read the relevant section of `plan.md`. Does it?

Verification answers the disagreement. You don't need rhetoric.

### 3. Categorize the response

After verification, every item ends up in one of three buckets:

| Bucket | Action |
|---|---|
| **Reviewer was right** | Fix it. Add a test if there isn't one. Note in the changelog what changed. |
| **Reviewer was wrong** | Push back with the evidence (test output, file:line, spec quote). Don't be defensive — just show the artifact that proves it. |
| **It's a judgement call** | State your reasoning, ask the reviewer to weigh in, and be willing to change your mind either way. |

### 4. Severity ordering

Fix in this order, regardless of the order comments arrived in:

1. **Critical** — broken behavior, security, data loss, requirement not met. Fix before anything else.
2. **Important** — missing tests, missing edge cases, deviations from the plan that aren't justified. Fix before merging or moving on.
3. **Minor / suggestions** — style, naming, micro-optimization. Fix if cheap; otherwise note and move on. Don't let minor items stall a PR.

### 5. Don't bundle the response

When fixing review feedback, one logical change per commit. "Address review" as a single commit message hides what changed and makes follow-up review impossible. Group commits by issue, name them clearly.

### 6. Update tracking

If the review surfaced something that should be in the spec rather than just in the code:
- New acceptance criterion → update the relevant `requirements.md` (or `plan.md` if the initiative is in flight)
- Change to canonical behavior → note for the post-initiative `design.md` update
- New flow or invariant → update `flows/*.md` if applicable
- Append the round of review and what changed to `changelog.md`

## Red flags — you're doing it wrong

- **"Good catch!"** before you've verified the claim
- Fixing a comment by changing code without writing a test that proves the change is right
- Agreeing to a refactor that wasn't asked for, because the reviewer's adjacent comment made you self-conscious
- Pushing back without evidence ("I think it's fine") — that's deference's mirror image
- Treating a single reviewer disagreement as license to ignore the rest of the review
- Bundling 8 items into one commit titled "address review"
- Dismissing a comment because the reviewer "always nitpicks" — read it on its merits anyway
- Quietly fixing everything the reviewer flagged including the things you think are wrong, because pushing back feels uncomfortable

## Common rationalizations

| Excuse | Reality |
|---|---|
| "Easier to just fix it than argue" | If the reviewer is wrong, fixing introduces a bug. The argument is the cheap path. |
| "They're more senior, they must be right" | Seniority isn't evidence. Verify the claim. |
| "I don't want to seem defensive" | Pushing back with evidence isn't defensive. Pushing back with feelings is. |
| "It's just a style preference, fine, whatever" | If it's preference, say so explicitly: "Stylistic — happy to change if you feel strongly." Don't pretend it was a real bug. |
| "I'll address it later" | Critical and Important issues get fixed before moving on. "Later" is where bugs hide. |
| "The reviewer didn't run the code" | Then run it yourself and reply with the output. Don't dismiss without verifying. |

## How to push back well

When the reviewer is wrong, push back with **artifacts**, not opinions:

- A failing test that demonstrates the current code is correct under the reviewer's claimed input
- A line-and-file reference to the spec that defines the behavior
- A trace or log showing the actual control flow

> "I read this as `X`. The reviewer suggested it can do `Y`. I added a test for the `Y` case — see `pkg/foo/foo_test.go:42`. The test passes with the current code, so I think the original review comment was based on a misread. Happy to be wrong if I missed something."

Short, evidence-led, and explicitly open to being wrong. That's the tone.

## When to ask for clarification instead

If a comment is ambiguous, don't guess at what the reviewer meant. Ask. Examples of when to ask:

- The comment says "this is wrong" without saying why
- The reviewer suggests a refactor without saying what problem it solves
- Two comments on the same code seem to contradict each other
- The fix the reviewer suggests would break a different requirement you know about

A 30-second clarification beats a wrong fix.

## Integration with this project's flow

- After `/review` or the `code-reviewer` agent returns feedback: walk this process before touching code
- Append the review round + what changed + what you pushed back on to the active initiative's `changelog.md`
- If the review surfaces a spec gap, update `requirements.md` or `plan.md` rather than just patching code
- After fixes land, re-verify per `/verify` before claiming the review is addressed

## Bottom line

```
Receive → verify each claim → categorize → fix what's right, push back on what's wrong
```

Performative agreement looks polite and is dishonest. Evidence-led pushback looks blunt and is respectful. Choose the second.
