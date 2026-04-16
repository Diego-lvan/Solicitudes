---
name: django-patterns
description: Use when writing Python/Django code in this project — views, services, repositories, forms, schemas, exceptions, dependency wiring, middleware. Contains full code examples to adapt. Consult the file matching the layer you're touching; don't load all files. Defers to .claude/rules/django-code-architect.md for the architectural rules these patterns implement.
---

# Django Pattern Reference

Full code examples for the layered Django architecture (View → Service → Repository, Pydantic DTOs at boundaries, custom exceptions, server-side templates) defined in `.claude/rules/django-code-architect.md`. The rule file defines the architecture; this skill has the canonical code patterns that satisfy it.

## Reference files

| File | What it covers |
| ---- | -------------- |
| `features.md` | Feature package layout: schemas, exceptions, repository (interface + impl), service (interface + impl), view, form, dependencies — full working example |
| `platform.md` | Shared infra: `apps/_shared/` modules, base templates, middleware (request ID, error handler), settings split, URL roots |
| `errors.md` | Exception hierarchy: `_shared/exceptions.py` base classes, feature-specific subclasses, view-level error handling, middleware fallback |
| `forms.md` | Form-to-DTO conversion: Django `Form`/`ModelForm` validation → Pydantic DTO → service; multi-step forms; file uploads |

## When to consult these files

| Situation | Read |
| --------- | ---- |
| Writing or modifying a feature package (view, service, repo, form, schema) | `features.md` |
| Adding/changing middleware, base templates, request-id propagation, error handler middleware, or settings layout | `platform.md` |
| Defining new exception types, feature `exceptions.py`, or handling errors at the view/middleware boundary | `errors.md` |
| Wiring a Django Form/ModelForm to a Pydantic DTO that crosses into the service | `forms.md` |

**Read only the file you need.** These files are large; loading all four wastes context.

## When NOT to consult this skill

- **During `/plan` or `/brainstorm`** — design docs (`requirements.md`, `plan.md`, `design.md`) describe layering and structure but do not embed full code. The rule under `.claude/rules/django-code-architect.md` is sufficient at that stage.
- **For pure template/CSS work** — see the user-level `frontend-design` skill instead.
- **For one-off scripts or migrations** that don't follow the layered pattern by design.

## How this skill relates to other skills

- `/implement` is the primary caller — when a task touches Python code, the implementer reads the relevant pattern file before writing.
- The `code-reviewer` agent uses these files implicitly: it consults `django-code-architect.md` for rules and may refer here for the canonical implementation of those rules.
- `/tdd` does not change which file you consult — it changes the order (test first, then pattern, then code).
- `frontend-design` (user-level) covers Bootstrap 5 + Django templates UI patterns; orthogonal to this skill, which is purely Python-side.
