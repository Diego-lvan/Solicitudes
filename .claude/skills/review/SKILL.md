---
name: review
description: Validate implementation against plan.md. Compares what was built vs what was specified, checks test coverage, architecture compliance, and reports issues by severity.
argument-hint: "[optional: section name or 'full' for entire initiative]"
allowed-tools: Bash, Read, Glob, Grep
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
- [ ] **Shared infra in `apps/_shared/`**, not in feature packages, and not named `utils`/`common`/`helpers`
- [ ] **Custom exceptions** subclass `apps._shared.exceptions.AppError`; repositories raise feature exceptions, never let `Model.DoesNotExist` leak
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

## Rules

- **plan.md is the source of truth** — if code differs from plan.md, it's the code that's wrong (unless plan.md was explicitly updated).
- **Don't nitpick style** — only report structural/behavioral issues.
- **Be specific** — include file paths, line numbers, and what plan.md says.
- **CRITICAL means blocking** — only use for missing functionality, wrong behavior, or broken tests.
- **If everything passes** — say so clearly. Don't invent issues.
- **Never modify code** — this skill only reads and reports. Use `/implement` to fix issues.
