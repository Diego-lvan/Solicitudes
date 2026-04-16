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

## Step 4 — Architecture compliance (backend only)

Read `.claude/rules/django-code-architect.md` and verify:

- [ ] 4-layer flow: Router → Handler → Service → Repository
- [ ] One struct per file
- [ ] Interface-driven dependencies (constructor injection)
- [ ] `*gin.Context` never passed to service/repository
- [ ] Cross-feature deps: service → service, never service → repo
- [ ] Feature has `dependencies/` folder with container wiring
- [ ] Shared infra in `internal/infra/`, not in feature packages
- [ ] Errors use `apperror` sentinels + feature `errors/` package

---

## Step 5 — Test coverage check

- [ ] Every endpoint has at least one happy-path test
- [ ] Error paths mentioned in plan.md have tests
- [ ] Tests actually assert behavior (not just "no error")
- [ ] Tests run and pass (`go test ./...` or appropriate command)

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
