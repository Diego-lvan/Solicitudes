# CLAUDE.md — Sistema de Solicitudes

## Project Overview

Sistema de Solicitudes for the Universidad Autónoma de Zacatecas. Monolithic Django application with server-side templates (Bootstrap 5, no DRF). Lets students and faculty file academic and administrative requests with dynamic forms, state-machine tracking, PDF generation from templates, and role-based management. See `specs/global/requirements.md` for full context.

> **Note:** `code_example/` at the project root is the deprecated old code. It is reference material only — do not extend it. New code follows the layered architecture described below and lives at `apps/`, `config/`, `templates/`.

## Architectural Style

**View → Service → Repository**, with Pydantic v2 DTOs at every layer boundary and Django ORM contained inside the repository. Server-side templates render Pydantic DTOs (no DRF, no JSON API by default). All exceptions inherit from `apps._shared.exceptions.AppError` and are mapped to HTTP responses by middleware.

**The full architectural rules live in `.claude/rules/django-code-architect.md`. Read it before any code change.** The accompanying `django-patterns` skill (`.claude/skills/django-patterns/`) holds canonical code examples (`features.md`, `errors.md`, `forms.md`, `platform.md`).

## Project Structure

```
solicitudes/
├── .claude/                          # Claude Code config
│   ├── skills/                       # Workflow + reference skills
│   │   ├── brainstorm/               # Design exploration before /plan
│   │   ├── plan/                     # plan.md + status.md + changelog.md
│   │   ├── implement/                # Execute tasks from status.md
│   │   ├── tdd/                      # Strict RED-GREEN-REFACTOR
│   │   ├── debug/                    # Systematic root-cause investigation
│   │   ├── verify/                   # Evidence-before-claims gate
│   │   ├── receive-review/           # Process review feedback rigorously
│   │   ├── review/                   # Final initiative validation
│   │   ├── commit/                   # Manual conventional commits
│   │   └── django-patterns/          # Canonical Django code examples
│   ├── agents/
│   │   └── code-reviewer.md          # Fresh-context reviewer at section boundaries
│   └── rules/
│       ├── django.md                 # Concise summary
│       ├── django-code-architect.md  # Deep architectural rules (canonical)
│       └── django-test-architect.md  # Test conventions and stack
├── specs/                            # SDD specs (source of truth)
│   ├── global/
│   │   ├── requirements.md
│   │   ├── architecture.md
│   │   ├── roadmap.md
│   │   └── explorations/             # In-flight brainstorm drafts
│   ├── planning/                     # Initiative dirs: 00N-name/{plan,status,changelog}.md
│   ├── apps/                         # Per-app feature specs (requirements.md + design.md)
│   │   ├── usuarios/
│   │   ├── solicitudes/
│   │   ├── notificaciones/
│   │   ├── mentores/
│   │   └── reportes/
│   ├── shared/                       # Cross-cutting concerns
│   │   ├── infrastructure/
│   │   └── best-practices/
│   └── flows/                        # End-to-end flows that span apps
├── config/                           # Django project settings + URL root
│   ├── settings/{base,dev,prod}.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                             # Django apps (layered per-feature)
│   ├── _shared/                      # Cross-cutting infra (exceptions, middleware, auth)
│   ├── usuarios/                     # JWT validation, roles, profile
│   ├── solicitudes/                  # Core: tipos, formularios, lifecycle, archivos, PDF
│   ├── notificaciones/               # Email dispatch
│   ├── mentores/                     # Mentor catalog
│   └── reportes/                     # Dashboard + exports
├── templates/                        # base.html + components/ + per-app
├── static/                           # CSS, JS, images
├── media/                            # Uploaded files (gitignored)
├── code_example/                     # DEPRECATED — old code, reference only
├── srs/                              # Formal SRS (LaTeX)
├── requerimientos_solicitudes.md     # Original written requirements
├── manage.py
├── requirements.txt
└── CLAUDE.md
```

## SDD (Spec-Driven Development) Workflow

Specs are the source of truth, not code.

### File types

**Feature specs** (long-lived reference, per app/feature):
- `requirements.md` — WHAT + WHY. No implementation details.
- `design.md` — HOW. Canonical reference. Updated *after* an initiative completes, not during. Must include a `## Related Specs` section.

**Flows** (cross-app data flows):
- `flows/<flow-name>.md` — End-to-end paths spanning multiple apps. Sequence diagrams, step-by-step breakdowns, failure modes, references back to feature specs.

**Planning** (work tracking, scoped to one initiative):
- `roadmap.md` — Single source of truth for project status; lists all initiatives with dependencies.
- `planning/<NNN-name>/plan.md` — Implementation blueprint. Models, schemas, exception types, layer structure, sequencing. Disposable; can get detailed and messy.
- `planning/<NNN-name>/status.md` — Operational checklist. Task checkboxes grouped by concern, `[P]` for parallelizable work, blockers.
- `planning/<NNN-name>/changelog.md` — Append-only log of what actually happened.

### Lifecycle

```
/brainstorm  →  draft requirements.md (or specs/global/explorations/...)
/plan        →  plan.md + status.md + changelog.md, extends requirements.md
/implement   →  executes tasks; flexible TDD (or /tdd for strict); /debug on failures; /verify before checking off
code-reviewer →  dispatched at section boundaries; output processed via /receive-review
/review      →  final initiative validation
(initiative complete)
design.md updated — promote stable details from plan.md
flows/*.md updated if cross-app behavior changed
roadmap.md status updated
```

`/commit` is **never** triggered automatically — the user invokes it manually.

### Reading order (mandatory, sequential — do not skip)

1. Read `roadmap.md` — know the initiative, its status, dependencies.
2. Read the initiative's `plan.md` — your primary implementation guide.
3. Read the initiative's `status.md` — know what's done, what's next.
4. Read `design.md` of every app referenced in `plan.md`.
5. Read `.claude/rules/django-code-architect.md` — never skip; this is the architectural law.
6. Read relevant `flows/*.md` if the initiative touches cross-app behavior.

### Execution rules

- Implement from `plan.md`; track in `status.md`.
- `requirements.md` = WHAT/WHY only — no implementation details there.
- If `plan.md` doesn't cover something, stop and update it first — don't improvise.
- If implementation reveals `plan.md` is wrong, update `plan.md` *before* continuing.
- Check off tasks in `status.md` only after `/verify` produced evidence in the current message.
- Update `roadmap.md` status when an initiative's state changes.
- Append to `changelog.md` after every session; never edit existing entries.
- After initiative completes: update `design.md` — promote stable implementation details from `plan.md`.

### Conflict resolution

- `plan.md` references work not in `design.md`? Fine — `plan.md` is the source during the initiative.
- `plan.md` contradicts `design.md`? `plan.md` wins during the initiative. Update `design.md` after completion.

## Skills, Agents, and Rules — at a glance

**Skills** (`.claude/skills/`) drive the workflow:
| Skill | When |
|---|---|
| `/brainstorm` | Before `/plan`, for any creative/architectural work. Produces draft `requirements.md`. |
| `/plan` | Consumes brainstorm output → writes `plan.md`/`status.md`/`changelog.md`, updates roadmap. |
| `/implement` | Executes tasks from `status.md`; flexible TDD; dispatches `code-reviewer` at section boundaries. |
| `/tdd` | Strict mode for bug fixes, security/correctness-critical code. |
| `/debug` | Forced root-cause investigation before any fix attempt. |
| `/verify` | Evidence-before-claims gate. Run before any "done" claim. |
| `/receive-review` | Process feedback from `/review` or `code-reviewer` rigorously. |
| `/review` | Final validation against `plan.md` at initiative end. |
| `/commit` | **Manual only.** User-invoked. |
| `django-patterns` | Reference skill — full code examples for views, services, repos, forms, exceptions. |

**Agents** (`.claude/agents/`):
| Agent | When |
|---|---|
| `code-reviewer` | Dispatched by `/implement` at section boundaries; runs in fresh context. |

**Rules** (`.claude/rules/`, path-scoped to Python source):
| Rule | What |
|---|---|
| `django.md` | Concise summary; defers to the architects below |
| `django-code-architect.md` | Canonical architectural rules (READ before any code change) |
| `django-test-architect.md` | Canonical test conventions |

## Tech Stack

- **Python 3.12+**, **Django 5.x** (server-side templates, no DRF)
- **Pydantic v2** — DTOs at every layer boundary
- **PostgreSQL** (prod) / **SQLite** (dev) via Django ORM (contained in repositories)
- **Bootstrap 5** templates (see user-level `frontend-design` skill for UI conventions)
- **WeasyPrint** for PDF generation
- JWT validation in middleware (external auth provider)
- **Celery + Redis** for async email (optional)
- **pytest + pytest-django** + `model_bakery`, `freezegun`, `responses` for tests

## Language Convention

- **Code identifiers** (variables, functions, classes, modules) in **English**
- **User-facing copy** (templates, form labels, choices labels, exception `user_message`) in **Spanish**
- Comments may be in either; prefer English for technical comments, Spanish for domain-explanation comments
