---
paths:
  - "apps/**/*.py"
  - "config/**/*.py"
---

# Django Conventions — Sistema de Solicitudes (Quick Reference)

Concise summary of the project's Django conventions. **For the canonical, deep architectural rules, read `.claude/rules/django-code-architect.md`.** For test conventions, read `.claude/rules/django-test-architect.md`. For full code examples, consult the `django-patterns` skill.

## Stack

- Python 3.12+, Django 5.x, server-side templates (no DRF)
- PostgreSQL (prod) / SQLite (dev) via Django ORM
- Pydantic v2 for DTOs at every layer boundary
- WeasyPrint for PDF generation
- Bootstrap 5 templates

## Architecture (one-liner)

**View → Service → Repository.** ORM stays inside repository. Pydantic DTOs at every boundary. ABC + implementation split. Constructor DI via `dependencies.py` factory functions. Custom exceptions inherit from `_shared.exceptions.AppError`.

## Layout

```
apps/<app>/
├── models/                  # ORM models at app level
├── <feature>/
│   ├── schemas.py           # Pydantic DTOs
│   ├── exceptions.py        # Feature exceptions (subclass _shared)
│   ├── repositories/<x>/{interface,implementation}.py
│   ├── services/<x>/{interface,implementation}.py
│   ├── views/<actor>.py
│   ├── forms/
│   ├── dependencies.py      # DI factories
│   ├── permissions.py
│   ├── constants.py
│   └── tests/
_shared/                # Cross-cutting infra (exceptions, middleware, auth)
config/settings/{base,dev,prod}.py
templates/                   # base.html + per-app
```

## Hard rules

- One public class per file
- ABCs for repositories and services; concrete classes injected via constructor
- Repositories return Pydantic DTOs, never models or querysets
- Forms convert `cleaned_data` to a Pydantic DTO before crossing into the service
- Cross-feature dependency: service → service of another feature, NEVER service → repository of another feature
- English identifiers; Spanish only in user-facing copy (templates, form labels, choices labels, exception `user_message`)
- `request` never reaches a service or repository
- All exceptions raised in services/repos inherit from `AppError`; middleware maps them uniformly
- No business logic in models; models are data + simple invariants only
- Templates receive Pydantic DTOs, never querysets

## Settings

- Split: `config/settings/base.py`, `dev.py`, `prod.py`
- Secrets via env vars
- `INSTALLED_APPS` uses `apps.<app>` prefix

## Testing

- `pytest` + `pytest-django`, NOT `manage.py test`
- One test file per layer per feature: `test_views.py`, `test_services.py`, `test_repositories.py`, `test_forms.py`
- Repositories tested against real DB; services tested with in-memory fake repositories
- Factories: `model_bakery` per feature in `tests/factories.py`
- Time, randomness, network, email all controlled

## URL routing

- `config/urls.py` includes per-app `urls.py`; per-app includes per-feature
- Namespaced: `app_name = "solicitudes"` → `{% url 'solicitudes:create' %}`
- Path converters preferred (`<int:pk>`, `<uuid:id>`, `<slug:folio>`)

## Forbidden

- ORM call outside repository (`Solicitud.objects.filter(...)` in a view or service)
- Returning a model instance from a repository
- `cleaned_data` crossing into a service — convert to typed DTO first
- `request` parameter on a service or repository method
- `from django.http import HttpRequest` imported in service or repository
- `except Exception:` (use the specific exception type or feature exception)
- Catching `Model.DoesNotExist` outside the repository (the repo raises a feature exception)
- Multiple public classes in one file
- Modules named `utils`, `common`, or `helpers`
- Spanish identifiers in code

## When in doubt

Read the deep rule file: `.claude/rules/django-code-architect.md`. Read the canonical code patterns in the `django-patterns` skill (`features.md`, `errors.md`, `forms.md`, `platform.md`).
