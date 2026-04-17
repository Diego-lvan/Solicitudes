---
name: implement
description: Execute the next task(s) from status.md. Defaults to flexible TDD; switches to strict /tdd for bug fixes and security-sensitive code; routes failures through /debug; verifies via /verify before checking tasks off; dispatches the code-reviewer agent at section boundaries and runs /receive-review on the response.
argument-hint: "[optional: specific task or section to work on]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# SDD Implementation Engine

You are executing tasks from a planning initiative using flexible TDD with built-in review checkpoints.

---

## Step 1 — Load context (mandatory, sequential)

1. Read `CLAUDE.md` at the project root.
2. Read `specs/global/roadmap.md` — identify the active initiative.
3. Read the initiative's `plan.md` — your implementation blueprint.
4. Read the initiative's `status.md` — find what's next.
5. Read `design.md` of all modules referenced in plan.md.
6. If `$ARGUMENTS` specifies a task or section, locate it in status.md. Otherwise, take the first unchecked task.

---

## Step 2 — Determine work scope

Look at status.md and determine:

- **Single task**: one unchecked item without `[P]` marker → execute sequentially.
- **Parallel group**: multiple unchecked items with `[P]` in the same section → dispatch subagents (one per task, max 4 concurrent).
- **Section boundary**: if the next unchecked task is in a new section and the previous section has all items checked → trigger review of completed section first.

---

## Step 3 — Execute each task (flexible TDD)

For each task, follow this cycle:

### 3a. Understand
- Read plan.md's implementation details for this specific task.
- Read existing code that will be modified (Glob, Read).
- Identify what needs to change and what the test should verify.

### 3b. Implement + Test (flexible by default; strict when warranted)

You may write code first OR test first, but both MUST exist before marking done.

**Switch to strict TDD (`/tdd`) for these — flexible mode is not appropriate:**
- Bug fixes — the failing test that reproduces the bug must exist *before* the fix, no exceptions
- Auth, crypto, signing, federated-protocol code, anything security-sensitive
- Refactors of business logic with subtle invariants
- Anything where "looks right" is insufficient evidence of correctness

If the task falls in any of those, invoke `/tdd` for this task and follow its red-green-refactor discipline.

**Otherwise, flexible TDD applies:**

**Preferred flow (test-first when natural):**
1. Write a failing test that captures the expected behavior.
2. Run the test — confirm it fails for the right reason.
3. Write the minimal implementation to make it pass.
4. Run the test — confirm it passes.

**Acceptable flow (code-first when test-first is awkward):**
1. Write the implementation.
2. Write a test that exercises the implementation.
3. Run the test — confirm it passes.
4. Verify the test actually validates behavior (not just "doesn't crash").

**When tests are NOT required:**
- Pure config changes (env vars, docker-compose, nginx conf)
- Spec/doc file updates
- Migration files (tested by running them)

### 3c. Verify (apply `/verify` discipline)

Evidence before claims. Do not check `[x]` based on a previous run, a hunch, or "the linter passed."

- Run the test command **fresh, in this message** — full package/marker, not just the one file
- For tasks under `### E2E` in status.md, the right command depends on the tier:
  - **Tier 1 (in-process integration)** — runs as part of normal `pytest` (no marker required); the test files are inside `apps/<app>/<feature>/tests/test_views.py` (or `tests-integration/` if it grew)
  - **Tier 2 (browser, Playwright)** — `pytest -m e2e` (or the project's E2E pytest config); needs `playwright install chromium` once and a live server
- Read the full output: exit code, failure count, any warnings or skipped tests
- Confirm no regressions: tests outside what you touched still pass
- Confirm the output is pristine — no leftover debug prints, no warnings introduced by your change
- For Tier 2 failures, capture the artifacts: trace zip, video, HTML report. Cite their paths in the failure analysis. View traces with `playwright show-trace <path>`.
- If verification fails:
  - **Trivial cause** (typo, obvious mistake) → fix and re-verify
  - **Non-trivial failure** (unexpected behavior, intermittent failure, mysterious diff) → STOP. Invoke `/debug` to find the root cause before attempting any fix. Do not guess.
- Do NOT mark the task done until verification produces evidence in this message.

### 3d. Update tracking (only after Step 3c produced evidence)

- Check the task in `status.md`: `- [ ]` → `- [x]`
- Append to `changelog.md`:
  ```
  ## {YYYY-MM-DD}
  - Implemented: {brief description of what was done}
  - Tests: {what was tested + evidence of passing}
  ```

---

## Step 4 — Parallel execution (for [P] tasks)

When you encounter multiple `[P]` tasks in the same section:

1. Confirm they are truly independent (no shared state, no ordering dependency). If you can't confirm, run them sequentially.
2. Dispatch one subagent per task (max 4) using the Agent tool.
3. Each subagent prompt must include:
   - The full task description from status.md
   - Relevant implementation details from plan.md
   - File paths to read and modify
   - Test requirements
   - Instruction to apply the same flexible-TDD-or-strict-`/tdd` rule from Step 3b
4. Wait for all subagents to complete.
5. **Trust but verify** — do not assume subagents succeeded because they said so. Check the diff (`git diff`) and confirm the changes match the brief, per `/verify`.
6. Run the full test suite once to catch integration issues.
7. Update status.md and changelog.md for all completed tasks (one entry per task).

---

## Step 5 — Section review checkpoint (dispatch `code-reviewer`, then `/receive-review`)

After ALL tasks in a section are checked off:

1. **Announce**: `Section '{section name}' complete. Dispatching code-reviewer agent.`
2. **Get the git range:**
   ```bash
   BASE_SHA=$(git rev-parse HEAD~N)   # N = number of commits made for this section
   HEAD_SHA=$(git rev-parse HEAD)
   ```
3. **Dispatch the `code-reviewer` agent** (Agent tool, `subagent_type: code-reviewer`) with:
   - **What was implemented:** one-paragraph summary of the section
   - **What it should do:** path to `plan.md` and the specific section name; path to relevant `requirements.md`, `design.md`, and `flows/*.md`
   - **Git range:** `BASE_SHA` and `HEAD_SHA`
   - **Architecture rules to consult:** `.claude/rules/django-code-architect.md` (and `.claude/rules/django-test-architect.md` for test concerns)
   - **Initiative number** so the agent can locate planning files
4. **Do NOT do this review in your own context.** The agent runs in fresh context and produces a structured report (Critical / Important / Suggestion + Assessment line). That separation is the point — it prevents marking your own homework.
5. **When the agent returns, run `/receive-review`** on its output. That skill governs how to evaluate each item, what to fix, what to push back on with evidence, and how to sequence the response.
6. **Action by severity:**
   - **Critical** → fix before proceeding. Re-run `/verify`. Append fix + reasoning to `changelog.md`.
   - **Important** → fix before this section is considered done, OR push back with evidence per `/receive-review` and document the disagreement in `changelog.md`.
   - **Suggestion** → fix if cheap, otherwise note and move on.
7. **If you fixed issues** → re-dispatch the `code-reviewer` agent on the new range to confirm the assessment is now "Ready to proceed" before moving on.
8. Only when the assessment is "Ready to proceed" with no unaddressed Critical/Important: proceed to the next section.

---

## Step 6 — Continue or stop

After review passes:
- If more sections remain → go to Step 2 for the next section.
- If all sections complete → announce "All tasks complete. Run `/review` for final validation when you're ready." Stop. Do not run `/commit`, do not suggest committing — the user invokes commits manually.

---

## Rules

- **Never skip Step 1** — context loading prevents wrong implementations.
- **Never mark a task done without `/verify`** — fresh test run, full output, in this message. No "should pass."
- **Never implement something not in plan.md** — if you think something is missing, stop. Either kick back to `/plan` to update the blueprint, or kick back further to `/brainstorm` if the design itself shifted.
- **If plan.md is ambiguous** — ask the user; do not guess. Update plan.md with the clarification before continuing.
- **For bug fixes and security-sensitive code, switch to `/tdd`** — flexible mode is not appropriate.
- **For non-trivial test failures, route through `/debug`** — do not guess fixes.
- **Section review goes through the `code-reviewer` agent, not your own context** — then handle the response with `/receive-review`.
- **Never commit automatically** — `/commit` is invoked manually by the user. Do not call it from `/implement`, do not suggest "I'll commit now," do not run `git commit` on your own. After a section is "Ready to proceed," stop and wait.
- **changelog.md is append-only** — never edit existing entries.
