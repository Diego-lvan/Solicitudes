---
name: review
description: Validate implementation against plan.md. Compares what was built vs what was specified, checks test coverage, architecture compliance, and reports issues by severity. When the full initiative passes clean, prompts for the SDD closeout (requirements.md for new feature folders + design.md updates + roadmap flip).
argument-hint: "[optional: section name or 'full' for entire initiative]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# SDD Implementation Review

You are reviewing implemented code against the initiative's plan.md to catch deviations, missing pieces, and quality issues.

---

## Step 1 — Load context

1. Read `CLAUDE.md` at the project root.
2. Read `specs/global/roadmap.md` — identify the active initiative.
3. Read the initiative's `plan.md` — the spec you're reviewing against.
4. Read the initiative's `status.md` — know what's been checked off.
5. Read the initiative's `changelog.md` — understand what was done and when.

---

## Step 2 — Determine review scope

- If `$ARGUMENTS` specifies a section → review only that section's tasks.
- If `$ARGUMENTS` says "full" → review the entire initiative.
- If `$ARGUMENTS` is empty → review all checked-off tasks that haven't been reviewed yet (compare changelog.md entries vs last review entry).

---

## Step 3 — Spec compliance check

For each completed task, verify against plan.md:

### Endpoints & APIs
- [ ] All endpoints in plan.md exist with correct method, path, request/response bodies
- [ ] Status codes match specification
- [ ] Auth/middleware requirements applied

### Database
- [ ] Schema matches plan.md (tables, columns, types, constraints)
- [ ] Migrations exist and are runnable
- [ ] Indexes specified in plan.md are created

### File structure
- [ ] All files mentioned in plan.md exist at the specified paths
- [ ] No unexpected files created outside the plan's scope

### Configuration
- [ ] Env vars from plan.md are defined with correct defaults
- [ ] Docker/infrastructure changes match plan.md

### Behavior
- [ ] Business logic matches plan.md's description
- [ ] Error handling follows the specified patterns
- [ ] Edge cases mentioned in plan.md are handled

---

## Step 4 — Architecture compliance

Read `.claude/rules/django-code-architect.md` and verify:

- [ ] **3-layer flow**: View → Service → Repository
- [ ] **One public class per file** (no `models.py` with three models, no `services.py` with five services)
- [ ] **Interface-driven**: every repository and service has an ABC + concrete implementation
- [ ] **Constructor DI**: dependencies injected via `__init__`, never instantiated inside the class
- [ ] **`request` never reaches service or repository** — view extracts what's needed and passes primitives or DTOs
- [ ] **ORM stays in repository**: no `Model.objects.*` outside `repositories/implementation.py`
- [ ] **Repositories return Pydantic DTOs**, never models or querysets
- [ ] **Forms convert `cleaned_data` to a Pydantic DTO** before crossing into the service
- [ ] **Templates receive DTOs**, never querysets or model instances
- [ ] **Cross-feature deps: service → service**, never service → another feature's repository
- [ ] **Feature has `dependencies.py`** wiring its repositories → services as factory functions
- [ ] **Shared infra in `_shared/`**, not in feature packages, and not named `utils`/`common`/`helpers`
- [ ] **Custom exceptions** subclass `_shared.exceptions.AppError`; repositories raise feature exceptions, never let `Model.DoesNotExist` leak
- [ ] **English identifiers**; Spanish only in user-facing copy (templates, form labels, exception `user_message`)

---

## Step 5 — Test coverage check

Read `.claude/rules/django-test-architect.md` and verify:

- [ ] **Per-layer files exist** for each affected feature: `test_views.py`, `test_services.py`, `test_repositories.py`, `test_forms.py`
- [ ] **Repository tests** use real DB (`pytest.mark.django_db`) and assert returned **Pydantic DTOs**, not model instances
- [ ] **Service tests** use **in-memory fake repositories** (no DB) and assert behavior + raised feature exceptions
- [ ] **View tests** use the test `Client`, assert on status/template/context — not on service internals
- [ ] **Form tests** cover both valid input AND each invalid case (with expected `form.errors`)
- [ ] **Permission paths tested**: anonymous, wrong-role, right-role for each protected view
- [ ] **State transitions**: every allowed transition has a test; every forbidden transition raises the feature exception
- [ ] **Determinism**: time controlled (`freezegun`), email captured (`mail.outbox`), HTTP mocked (`responses`) — no flaky tests
- [ ] **E2E coverage** (per `plan.md`'s `## E2E coverage` section, if present):
  - In-process integration (`Client` multi-step) tests for cross-feature flows the initiative introduces
  - Browser tests (`pytest-playwright`) for the golden paths the initiative is responsible for, in `tests-e2e/`
- [ ] **Tests run and pass**: `pytest` exits 0 with no skipped/xfailed tests except those explicitly marked. For the browser tier: `pytest -m e2e` exits 0
- [ ] **Tests assert behavior**, not framework calls (no `mock.called == True` and stop)

---

## Step 6 — Report

Present findings in this format:

```
## Review: {initiative name} — {scope reviewed}

### CRITICAL (must fix before continuing)
- {issue}: {what's wrong} → {what plan.md says it should be}

### WARNING (fix before initiative ends)
- {issue}: {what's wrong} → {suggestion}

### PASS
- {what was verified and is correct}

### Summary
{1-2 sentences: overall status, next action}
```

---

## Step 7 — Initiative closeout (only when scope is full AND no CRITICAL issues)

Per CLAUDE.md's SDD lifecycle, an initiative is **not done** when the review passes — four more spec updates have to land. Skip this step if scope was a single section, or if any CRITICAL issue is open.

If all of the above hold, **announce** the closeout list to the user and ask for confirmation before editing:

> Review passed clean. Per the SDD lifecycle, four closeout edits are due:
>   1. For each new feature folder under `specs/apps/<app>/<feature>/` introduced by this initiative: write `requirements.md` (WHAT + WHY, no implementation details — distilled from the initiative's plan.md and the user-visible behavior).
>   2. Update `design.md` for each module in plan.md's "Affected Apps / Modules" — promote stable details out of plan.md. For new feature folders, write the file alongside the new `requirements.md`.
>   3. Update `flows/*.md` for any cross-app flow this initiative introduced or changed.
>   4. Flip `specs/global/roadmap.md` row from `In Progress` to `Done`, and the `Status:` line in the initiative's `status.md`.
>
> Want me to do these now, or wait?

If the user confirms, perform the edits in this order:

1. **requirements.md** — for each *new* feature folder this initiative introduced under `specs/apps/<app>/<feature>/`, write a `requirements.md` BEFORE the matching `design.md`. Source material: the initiative's `plan.md` (its summary, scope, acceptance criteria, open questions) and `requirements.md` if one exists at the global or initiative level. Keep it WHAT/WHY only — user-visible behavior, success criteria, scope boundaries. **No** code, no DTOs, no layer wiring (those belong in `design.md`). Existing feature folders that already have a `requirements.md` get updated only if the initiative materially changed user-visible behavior; otherwise leave them alone.
2. **design.md** — for each app/area in plan.md's `## Affected Apps / Modules`, locate the matching `design.md` (typically `specs/apps/<app>/<feature>/design.md` or `specs/shared/<area>/design.md`). Promote the now-stable bits of `plan.md` that future code should follow (data shapes, layer wiring, contracts, env vars, exception types). Do not duplicate plan.md verbatim — only the parts that won't change in the next initiative. Keep the `## Related Specs` section intact (or add it if missing).
3. **flows/*.md** — only if the initiative crosses ≥ 2 apps or touches an end-to-end path described in `specs/flows/`. For pure infra/bootstrap initiatives, skip and say so explicitly in the report.
4. **roadmap.md** — flip the initiative's `Status` cell to `Done`. Do not delete the row.
5. **status.md** — flip the top-of-file `Status:` line to `Done`. Bump `Last updated:`.

Then **report** what was changed in one paragraph and stop. Do **not** run `/commit` and do not suggest a commit message — `/commit` is always user-invoked.

If the user declines closeout (or asks to defer), append a TODO note at the bottom of the review report (`### Closeout pending`) listing the four edits that still need to happen. The next session picks them up.

---

## Rules

- **plan.md is the source of truth** — if code differs from plan.md, it's the code that's wrong (unless plan.md was explicitly updated).
- **Don't nitpick style** — only report structural/behavioral issues.
- **Be specific** — include file paths, line numbers, and what plan.md says.
- **CRITICAL means blocking** — only use for missing functionality, wrong behavior, or broken tests.
- **If everything passes** — say so clearly. Don't invent issues.
- **Never modify implementation code** — this skill only reads and reports for code. The Step 7 edits are scoped to spec/planning files (`specs/**/requirements.md`, `specs/**/design.md`, `specs/global/roadmap.md`, the initiative's `status.md`) and only after the user confirms.
- **Never run `/commit`** — the closeout edits leave the working tree dirty for the user to commit when they choose.
