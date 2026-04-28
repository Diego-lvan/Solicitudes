# 013 — User Directory (admin read-only)

## Summary

Ship an admin-only, read-only directory for `usuarios.User`. A paginated list at `/usuarios/` with role + free-text filters, and a detail page at `/usuarios/<matricula>/` that surfaces cached identity, academic profile, mentor status, and audit timestamps. Zero mutation paths — SIGA + the auth provider own user data.

This is the production replacement for the DEBUG-only dev-login enumeration; `UserRepository.list_all()` keeps its narrowed contract and is **not** reused.

## Depends on

- **002** — `usuarios.User` model, `AdminRequiredMixin`, `UserDTO`, `JwtAuthenticationMiddleware`.
- **008** — `mentores.services.mentor_service.MentorService.is_mentor(matricula)`; consumed via service interface for the detail page.

## Affected Apps / Modules

- `usuarios/directory/` — **new** feature package (schemas, repository, service, views, forms, templates, urls, tests).
- `usuarios/urls.py` — include the new feature urls under namespace `usuarios:directory:`.
- `templates/components/sidebar.html` — add "Usuarios" link in the Admin section, before "Reportes".
- `templates/usuarios/directory/` — **new** templates (`list.html`, `detail.html`, `_filter_form.html`).
- `_shared/pagination.py` — consumed (no changes).

## References

- [apps/usuarios/directory/requirements.md](../../apps/usuarios/directory/requirements.md) — WHAT/WHY.
- [apps/usuarios/requirements.md](../../apps/usuarios/requirements.md) — parent (RF-USR-07).
- [apps/usuarios/design.md](../../apps/usuarios/design.md) — `User` model, `UserRepository.list_all` (DEBUG-only), `AdminRequiredMixin`, cross-feature contract.
- [apps/mentores/catalog/design.md](../../apps/mentores/catalog/design.md) — `MentorService.is_mentor`.
- [apps/reportes/dashboard/design.md](../../apps/reportes/dashboard/design.md) — reference for permissive querystring parsing (RF-REP-06) and admin sidebar wiring.
- [global/requirements.md](../../global/requirements.md) — RNF-01, RNF-02.
- [.claude/rules/django-code-architect.md](../../../.claude/rules/django-code-architect.md) — architectural law (interface-driven, cross-feature service-to-service, one class per file).

## Implementation Details

### 1. Feature package layout

```
app/usuarios/directory/
├── __init__.py
├── constants.py                 # PAGE_SIZE = 25
├── schemas.py                   # UserListFilters, UserListItem, UserDetail
├── urls.py                      # /usuarios/ and /usuarios/<matricula>/
├── dependencies.py              # factory functions
├── forms/
│   ├── __init__.py
│   └── filter_form.py           # DirectoryFilterForm (GET-bound)
├── repositories/
│   └── user_directory/
│       ├── __init__.py
│       ├── interface.py         # UserDirectoryRepository(ABC)
│       └── implementation.py    # OrmUserDirectoryRepository
├── services/
│   └── user_directory/
│       ├── __init__.py
│       ├── interface.py         # UserDirectoryService(ABC)
│       └── implementation.py    # DefaultUserDirectoryService
├── views/
│   ├── __init__.py
│   ├── _helpers.py              # safe_return_path, build_filter_querystring
│   ├── list.py                  # DirectoryListView
│   └── detail.py                # DirectoryDetailView
└── tests/
    ├── __init__.py
    ├── test_repositories.py
    ├── test_services.py
    ├── test_forms.py
    └── test_views.py
```

> No `models/` — this feature has zero new tables. No `exceptions.py` — reuses `usuarios.exceptions.UserNotFound` (404) and `_shared.exceptions.Unauthorized` (403).

### 2. Pydantic DTOs (`schemas.py`)

```python
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from usuarios.constants import Role

class UserListFilters(BaseModel):
    """Parsed querystring → repository input."""
    model_config = {"frozen": True}
    role: Optional[Role] = None         # None = all roles
    q: str = ""                         # already trimmed; "" = no search
    page: int = Field(default=1, ge=1)

class UserListItem(BaseModel):
    """One row in the list. Built by the repository."""
    model_config = {"frozen": True}
    matricula: str
    full_name: str
    role: Role
    programa: str
    email: str
    last_login_at: Optional[datetime]

class UserDetail(BaseModel):
    """Full read-only detail. Built by the service (combines repo + mentor service)."""
    model_config = {"frozen": True}
    matricula: str
    full_name: str
    email: str
    role: Role
    programa: str
    semestre: Optional[int]
    gender: str                          # "H" / "M" / ""
    is_mentor: Optional[bool]            # None when MentorService failed
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
```

### 3. Repository — `UserDirectoryRepository`

`repositories/user_directory/interface.py`:

```python
from abc import ABC, abstractmethod
from _shared.pagination import Page
from usuarios.directory.schemas import UserListFilters, UserListItem, UserDetail

class UserDirectoryRepository(ABC):
    @abstractmethod
    def list(self, filters: UserListFilters, page_size: int) -> Page[UserListItem]: ...

    @abstractmethod
    def get_detail(self, matricula: str) -> UserDetail:
        """Return the full detail (without is_mentor — service overlays that).
        Raises usuarios.exceptions.UserNotFound when the matrícula is unknown."""
```

`repositories/user_directory/implementation.py` — `OrmUserDirectoryRepository`:

- `list(...)`:
  - Build a queryset over `usuarios.User`.
  - Apply `role` filter when set.
  - Apply `q` filter when non-empty: `Q(matricula__icontains=q) | Q(full_name__icontains=q) | Q(email__icontains=q)`.
  - Order by `("role", "matricula")` for stable pagination.
  - Compute `total = qs.count()`; slice `qs[offset:offset + page_size]` where `offset = (page - 1) * page_size`.
  - Map each row to `UserListItem`. Return `Page[UserListItem](items=..., total=..., page=..., page_size=...)`.
- `get_detail(matricula)`:
  - `User.objects.get(matricula=matricula)` — catch `User.DoesNotExist` and raise `UserNotFound(matricula)` (existing exception). The model `is_mentor` is **not** populated here; service overlays it.

### 4. Service — `UserDirectoryService`

`services/user_directory/interface.py`:

```python
from abc import ABC, abstractmethod
from _shared.pagination import Page
from usuarios.directory.schemas import UserListFilters, UserListItem, UserDetail

class UserDirectoryService(ABC):
    @abstractmethod
    def list(self, filters: UserListFilters) -> Page[UserListItem]: ...

    @abstractmethod
    def get_detail(self, matricula: str) -> UserDetail: ...
```

`services/user_directory/implementation.py` — `DefaultUserDirectoryService`:

- Constructor: `(directory_repo: UserDirectoryRepository, mentor_service: MentorService, page_size: int, logger: logging.Logger)`.
- `list(filters)` → delegates to `directory_repo.list(filters, page_size)`.
- `get_detail(matricula)`:
  1. `detail = directory_repo.get_detail(matricula)` (may raise `UserNotFound`).
  2. Try `is_mentor = mentor_service.is_mentor(matricula)`; on **any** exception, log at WARNING with the matrícula + request id (best-effort) and set `is_mentor = None`.
  3. Return `detail.model_copy(update={"is_mentor": is_mentor})`.

> **Cross-feature dep is service-to-service** — `MentorService` (interface), never the mentor repository.

### 5. Form — `DirectoryFilterForm` (`forms/filter_form.py`)

GET-bound, permissive parsing (matches RF-REP-06 posture):

```python
class DirectoryFilterForm(forms.Form):
    role = forms.ChoiceField(
        required=False,
        choices=[("", "Todos los roles")] + [(r.value, r.label) for r in Role],
    )
    q = forms.CharField(required=False, max_length=200, strip=True)
    page = forms.IntegerField(required=False, min_value=1)

    def to_filters(self) -> UserListFilters:
        # Bad/missing role → None; bad page → 1; q stripped, "" when blank.
        role_raw = (self.cleaned_data.get("role") or "").strip()
        try:
            role = Role(role_raw) if role_raw else None
        except ValueError:
            role = None
        page = self.cleaned_data.get("page") or 1
        q = self.cleaned_data.get("q") or ""
        return UserListFilters(role=role, q=q, page=page)
```

The view calls `form.is_valid()` for parsing but treats invalid input as "no filter" — never returns 400.

### 6. Views (`views/list.py`, `views/detail.py`)

Per the One-Class-Per-File rule, the two views live in separate files:
`views/list.py::DirectoryListView` and `views/detail.py::DirectoryDetailView`.
Both use `AdminRequiredMixin` (which itself extends `LoginRequiredMixin` —
applying both is redundant). All non-admin users → 403 via the existing
middleware. URLs accept GET only.

```python
# views/list.py
class DirectoryListView(AdminRequiredMixin, View):
    def get(self, request):
        form = DirectoryFilterForm(request.GET or None)
        form.is_valid()           # populate cleaned_data; never blocks
        filters = form.to_filters()
        page = get_user_directory_service().list(filters)
        ctx = {
            "page": page, "filters": filters, "form": form,
            "querystring": build_filter_querystring(filters),  # role + q only, no page
        }
        return render(request, "usuarios/directory/list.html", ctx)

# views/detail.py
class DirectoryDetailView(AdminRequiredMixin, View):
    def get(self, request, matricula: str):
        # UserNotFound propagates → AppErrorMiddleware renders 404
        detail = get_user_directory_service().get_detail(matricula)
        back_url = (
            safe_return_path(request.GET.get("return", ""))
            or reverse("usuarios:directory:list")
        )
        ctx = {"user_detail": detail, "back_url": back_url}
        return render(request, "usuarios/directory/detail.html", ctx)
```

Back-link strategy: the list view passes the active filter querystring to each
detail link as `?return=<urlencoded>`. The detail view reads
`request.GET.get("return", "")`, validates it via `safe_return_path` (relative
path only — rejects scheme, netloc, protocol-relative `//`, and payloads over
512 chars), and uses it to build the "Volver" href; falls back to
`{% url 'usuarios:directory:list' %}` when missing/unsafe.

### 7. URLs

`app/usuarios/directory/urls.py`:

```python
from django.urls import path
from usuarios.directory.views.admin import DirectoryListView, DirectoryDetailView

app_name = "directory"

urlpatterns = [
    path("", DirectoryListView.as_view(), name="list"),
    path("<str:matricula>/", DirectoryDetailView.as_view(), name="detail"),
]
```

`app/usuarios/urls.py` — include the feature:

```python
from django.urls import include, path
# ... existing imports + auth routes ...
urlpatterns += [
    path("usuarios/", include(("usuarios.directory.urls", "directory"))),
]
```

> Reverse names: `usuarios:directory:list`, `usuarios:directory:detail`.

### 8. Dependencies wiring (`dependencies.py`)

```python
import logging
from usuarios.directory.constants import PAGE_SIZE
from usuarios.directory.repositories.user_directory.implementation import OrmUserDirectoryRepository
from usuarios.directory.services.user_directory.implementation import DefaultUserDirectoryService
from mentores.dependencies import get_mentor_service

def get_user_directory_repository():
    return OrmUserDirectoryRepository()

def get_user_directory_service():
    return DefaultUserDirectoryService(
        directory_repo=get_user_directory_repository(),
        mentor_service=get_mentor_service(),
        page_size=PAGE_SIZE,
        logger=logging.getLogger("usuarios.directory.service"),
    )
```

### 9. Templates

All extend `base.html`, follow Bootstrap 5 conventions used by `reportes/`.

- `templates/usuarios/directory/list.html`
  - Page header "Usuarios", subhead "Vista de solo lectura. Los datos los administran SIGA y el proveedor de identidad."
  - `{% include "usuarios/directory/_filter_form.html" %}` (role select + q text + Buscar/Limpiar buttons; preserves selections after submit).
  - Table with the six list columns; row is a `<tr>` wrapped in a `<a>` (or row-level link via JS-free `data-href` — match existing `reportes/list.html` pattern).
  - Pagination component (existing `_shared/pagination` partial, with `?role=...&q=...&page=N` QS preserved).
  - Empty-state ("Sin coincidencias. Ajusta los filtros.") when `page.items` is empty.
- `templates/usuarios/directory/detail.html`
  - Header "Detalle de usuario — {matricula}", "Volver" link using `back_qs`.
  - Read-only definition list grouped into Identidad / Académico / Mentor / Auditoría sections per RF-DIR-06.
  - Mentor section: "Sí" / "No" / "Desconocido" (when `is_mentor is None`).
  - Gender rendered as "Hombre" (H), "Mujer" (M), "—" (otherwise).
  - `last_login_at` rendered with the existing `humanize` filter chain used in `reportes/list.html`; "Nunca" when null.
  - **No edit/delete buttons anywhere** — the only buttons are "Volver".

### 10. Sidebar entry

Edit `templates/components/sidebar.html` — inside the existing `{% if request.user.role == 'ADMIN' %}` block, **before** the "Reportes" sub-section, add:

```django
<div class="text-muted text-uppercase small fw-semibold mt-3 mb-1 px-2"
     style="letter-spacing:.08em;">
  Directorio
</div>
<a class="nav-link app-sidebar-link {% if '/usuarios/' in request.path and not '/auth/' in request.path %}active{% endif %}"
   href="{% url 'usuarios:directory:list' %}">
  <i class="bi bi-person-lines-fill me-2" aria-hidden="true"></i>Usuarios
</a>
```

> Active-path matcher excludes `/auth/...` (CallbackView, MeView, LogoutView all live under the `usuarios` app but at `/auth/...`), so the new link does not falsely highlight on the profile page.

### 11. Settings / migrations / config

- **No migrations.** No new model, no new field.
- **No new settings.** `PAGE_SIZE = 25` is a feature constant, not an env var.
- **No INSTALLED_APPS change.** `usuarios` is already installed; the `directory` package is auto-discovered by being imported from `usuarios/urls.py`.

### 12. Permissive parsing checklist (mirrors RF-REP-06)

| Bad input | Behavior |
|---|---|
| `?role=INVALID` | Treat as no role filter; render full list. |
| `?role=alumno` (lowercase) | `Role("alumno")` raises → no role filter. (Choices use uppercase.) |
| `?page=0` / `?page=-1` / `?page=abc` | Form rejects → fall back to page 1. |
| `?page=99999` (past end) | `Page` returns empty `items`; pagination component shows "Sin coincidencias" and links to page 1. |
| `?q=` (empty after trim) | No search filter applied. |
| `?q=ÁRBOL` | Postgres `icontains` is accent-sensitive on default collation; **document this limitation** in `design.md` at closeout. Not in scope for v1 to fix. |

### 13. Sequencing / parallelism

- Schemas / constants / repository can be written first (independent of mentor service wiring).
- Service depends on repository **and** `mentores.dependencies.get_mentor_service` — already exists.
- Templates + sidebar wiring can be authored in parallel with the backend after schemas land.
- E2E (Tier 1) blocks on views being wired and templates rendering at minimum.
- E2E (Tier 2 / Playwright) is **not** in scope for v1 (internal admin tooling, low risk; matches what the brainstorm captured).

## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)

- **List + filter + paginate as admin.** Seed ~30 users across roles → admin GETs `/usuarios/?role=ALUMNO&q=…&page=2` → assert 200, correct subset, deterministic ordering, pagination links carry the active QS.
- **Detail page with mentor overlay.** Seed an alumno + mark them mentor in the catalog → admin GETs `/usuarios/<matricula>/` → assert `is_mentor=True` rendered as "Sí". Repeat with a non-mentor → "No".
- **Detail page with mentor service failing.** Inject a `FakeMentorService` whose `is_mentor` raises → admin GETs detail → assert 200 and "Desconocido" in the rendered body, no 500.
- **Authorization gates.** Anonymous → redirect to login. Authenticated `ALUMNO` / `DOCENTE` / `CONTROL_ESCOLAR` / `RESPONSABLE_PROGRAMA` → 403 standard template.
- **Unknown matrícula on detail.** Admin GETs `/usuarios/NOPE/` → 404 standard template.
- **Permissive parsing.** Admin GETs `/usuarios/?role=BOGUS&page=abc` → 200, full list page 1. (Regression for the parsing posture.)

### Browser (Tier 2 — `pytest-playwright`)

_None._ Internal admin tooling, no novel JS, low risk; matches `reportes`-style coverage where Tier 2 is reserved for golden user-facing flows.

## Acceptance Criteria

- [ ] `GET /usuarios/` (admin) renders a paginated list ordered by `(role, matricula)`. (RF-DIR-01)
- [ ] `?role=…` filters by role; unknown values degrade to "no filter" (permissive parsing). (RF-DIR-02)
- [ ] `?q=…` matches case-insensitively against matrícula / full_name / email; trimmed; empty ignored. (RF-DIR-03)
- [ ] Page size = 25; invalid `page` falls back to 1; pagination links preserve filter QS. (RF-DIR-04)
- [ ] List columns and row-link match RF-DIR-05.
- [ ] `GET /usuarios/<matricula>/` (admin) renders the four sections in RF-DIR-06.
- [ ] `is_mentor` populated via `MentorService`; service failure → "Desconocido", no 500. (RF-DIR-07)
- [ ] Unknown matrícula → 404. (RF-DIR-08)
- [ ] Anonymous → redirect to login; non-admin → 403. (RF-DIR-09)
- [ ] "Volver" preserves the list QS via `?return=` (validated as relative). (RF-DIR-10)
- [ ] Sidebar "Usuarios" entry visible only to ADMIN; activates on `/usuarios/...` and not on `/auth/...`. (RF-DIR-11)
- [ ] No new migrations; no mutation paths; no edit/delete affordances anywhere.
- [ ] All Tier-1 flows in `## E2E coverage` pass.
- [ ] Coverage thresholds: views ≥ 80%, services ≥ 95%, repository ≥ 95% (parent `usuarios/design.md`).

## Open Questions

None. Brainstorm closed all design questions on 2026-04-26.
