# `usuarios · directory` — Design

> HOW this feature is built. Promoted from `specs/planning/013-user-directory/plan.md` after `/review` passed for **013** on 2026-04-26.

## Layer structure

```
app/usuarios/directory/
├── constants.py                 # PAGE_SIZE = 25
├── schemas.py                   # UserListFilters, UserListItem, UserDetail (Pydantic v2 frozen)
├── urls.py                      # app_name="directory"; "" → list, "<matricula>/" → detail
├── dependencies.py              # get_user_directory_repository, get_user_directory_service
├── forms/filter_form.py         # DirectoryFilterForm — permissive GET parsing
├── repositories/user_directory/
│   ├── interface.py             # UserDirectoryRepository(ABC)
│   └── implementation.py        # OrmUserDirectoryRepository
├── services/user_directory/
│   ├── interface.py             # UserDirectoryService(ABC)
│   └── implementation.py        # DefaultUserDirectoryService
├── views/
│   ├── _helpers.py              # safe_return_path, build_filter_querystring
│   ├── list.py                  # DirectoryListView
│   └── detail.py                # DirectoryDetailView
└── tests/                       # test_repositories, test_services, test_forms, test_views
```

No `models/`, no `exceptions.py`, no migrations. Reuses `usuarios.exceptions.UserNotFound` (404) and `_shared.exceptions.Unauthorized` (403). Templates live at `app/templates/usuarios/directory/{list,detail,_filter_form}.html`.

## DTOs (`schemas.py`)

All three are `model_config = {"frozen": True}` Pydantic v2 models.

| DTO | Purpose | Built by |
|---|---|---|
| `UserListFilters` | Parsed querystring → repository input. Fields: `role: Role \| None`, `q: str` (already trimmed), `page: int >= 1`. | `DirectoryFilterForm.to_filters()` |
| `UserListItem` | One row in the directory list. Six fields: matrícula, full_name, role, programa, email, last_login_at. | Repository |
| `UserDetail` | Full read-only detail. Adds `semestre`, `gender`, `is_mentor (bool \| None)`, `created_at`, `updated_at`. `is_mentor` is overlaid by the service. | Repository (`is_mentor=None`) → Service overlays |

## Repository contract — `UserDirectoryRepository`

```python
class UserDirectoryRepository(ABC):
    @abstractmethod
    def list(self, filters: UserListFilters, page_size: int) -> Page[UserListItem]: ...

    @abstractmethod
    def get_detail(self, matricula: str) -> UserDetail:
        """Raises usuarios.exceptions.UserNotFound when the matrícula is unknown."""
```

**`OrmUserDirectoryRepository`** owns all access to `usuarios.User`:
- `list` filters by `role` when set, `Q(matricula__icontains) | Q(full_name__icontains) | Q(email__icontains)` when `q` is non-empty, orders by `("role", "matricula")` (unique → stable pagination), counts, then slices `[(page-1)*page_size : page*page_size]`.
- `get_detail` does `User.objects.get(matricula=…)`, catches `User.DoesNotExist`, raises `UserNotFound(f"matricula={matricula}")`. Returns `UserDetail` with `is_mentor=None`.

> **Production-safe enumeration.** `UserRepository.list_all()` (DEBUG-only dev-login enumerator documented in `usuarios/design.md`) is *not* reused — its narrowed contract is preserved.

> **Known limitation.** Postgres `icontains` is accent-sensitive on the default collation; `?q=ÁRBOL` will not match a row stored as `Arbol`. Out of scope for v1; revisit when the dataset grows.

## Service contract — `UserDirectoryService`

```python
class UserDirectoryService(ABC):
    @abstractmethod
    def list(self, filters: UserListFilters) -> Page[UserListItem]: ...

    @abstractmethod
    def get_detail(self, matricula: str) -> UserDetail: ...
```

**`DefaultUserDirectoryService`** is constructor-injected with `directory_repository: UserDirectoryRepository`, `mentor_service: MentorService`, `page_size: int`, `logger: logging.Logger`.

- `list(filters)` → `directory_repo.list(filters, page_size)` (passthrough).
- `get_detail(matricula)`:
  1. `detail = directory_repo.get_detail(matricula)` — may raise `UserNotFound` (propagated).
  2. Try `is_mentor = mentor_service.is_mentor(matricula)`; on **any** exception, log at WARNING with the matrícula and `exc_info=True`, set `is_mentor = None`.
  3. Return `detail.model_copy(update={"is_mentor": is_mentor})`.

**Cross-feature contract:** the service depends on `MentorService` (interface from `mentores.services.mentor_service.interface`), never `MentorRepository`. This is the project's service-to-service rule.

## Form — `DirectoryFilterForm`

GET-bound `forms.Form` with `role` (`ChoiceField` driven by `Role.choices()` plus a leading "" / "Todos los roles" entry), `q` (`CharField`, trimmed, max 200), and `page` (`IntegerField`, min 1).

**Permissive `to_filters() -> UserListFilters`:** reads `cleaned_data` defensively (it may be missing keys when invalid input was rejected per-field), maps unknown role values to `None`, clamps invalid/negative `page` to 1, returns a `UserListFilters` DTO. The view calls `is_valid()` purely to populate `cleaned_data`; it never blocks on the result.

This mirrors the `reportes` posture (RF-REP-06): bad input degrades silently rather than surfacing a 400.

## Views (`views/list.py`, `views/detail.py`)

Both views use `AdminRequiredMixin` (which itself extends `LoginRequiredMixin`; applying both is redundant). URLs accept GET only.

- `DirectoryListView`: builds the form, calls `is_valid()`, derives filters, asks the service for a `Page[UserListItem]`, computes a "filter QS without `page`" via `build_filter_querystring(filters)` for pagination links, renders `usuarios/directory/list.html`.
- `DirectoryDetailView`: asks the service for `UserDetail` (lets `UserNotFound` propagate to `AppErrorMiddleware` → standard 404 page), validates `?return=` via `safe_return_path`, falls back to `reverse("usuarios:directory:list")`, renders `usuarios/directory/detail.html`.

## Safe back-link — `views/_helpers.safe_return_path`

```python
_MAX_RETURN_LEN = 512

def safe_return_path(raw: str) -> str | None:
    """Returns ``raw`` only if it is a safe same-origin relative path:
       - non-empty and ≤ _MAX_RETURN_LEN chars,
       - starts with a single ``/`` (not ``//``, not ``/\\``),
       - has no scheme and no netloc.
       Anything else returns None so the caller falls back to the canonical list URL."""
```

**Threat model:** the value comes from the querystring. The helper guards against open-redirect / phishing-style `?return=` payloads (`https://evil/`, `//evil/`) and against unbounded payload echo into the rendered href.

## URL surface

- `usuarios:directory:list` → `GET /usuarios/`
- `usuarios:directory:detail` → `GET /usuarios/<matricula>/`

Mounted under prefix `usuarios/` from `app/usuarios/urls.py`. Reverse-name format: `usuarios:directory:<name>`.

## Templates

All extend `base.html` and follow the `frontend-design` skill (Bootstrap 5, h1 sized `.h3`, `.table-hover` not striped, low-priority columns hidden `<md`/`<lg`, status via `text-bg-*` badges with text + color, no AI-look gradients).

- `list.html`: header + subhead, filter-form include, six-column `.table-hover`, pagination component (preserves filter QS), empty state (`bi-search` + sentence + no CTA — read-only feature).
- `detail.html`: 2×2 card grid (Identidad / Académico / Mentor / Auditoría) at `lg`, single column on mobile. Mentor status renders as **Sí** (`text-bg-success`) / **No** (`text-bg-secondary`) / **Desconocido** (`text-bg-warning`). Gender renders as Hombre / Mujer / "—". Last-login as `d/m/Y H:i` or "Nunca". `Volver` button uses `back_url` from the view.
- `_filter_form.html`: `<select name="role">` populated from `form.role.field.choices` (single source of truth — drift-free if a `Role` is added), `<input type="search" name="q" maxlength="200">`, **Buscar** + **Limpiar** buttons.

## DI wiring (`dependencies.py`)

```python
def get_user_directory_repository() -> UserDirectoryRepository:
    return OrmUserDirectoryRepository()

def get_user_directory_service() -> UserDirectoryService:
    return DefaultUserDirectoryService(
        directory_repository=get_user_directory_repository(),
        mentor_service=get_mentor_service(),
        page_size=PAGE_SIZE,
        logger=logging.getLogger("usuarios.directory.service"),
    )
```

## Sidebar wiring

`app/templates/components/sidebar.html` — inside the `{% if request.user.role == 'ADMIN' %}` block, **before** the "Reportes" header, a "Directorio" header followed by a "Usuarios" link to `usuarios:directory:list`. Active-path matcher: `'/usuarios/' in request.path and not '/auth/' in request.path` — the `/auth/` exclusion stops the link from falsely highlighting on `/auth/me` (CallbackView, MeView, LogoutView all live under the `usuarios` app but at `/auth/...`).

## Test architecture

- **`test_repositories.py`** (11 tests, `@pytest.mark.django_db`) — filter combos (role, q, role+q), ordering stability, pagination correctness across multi-page + past-end + empty, detail get + `UserNotFound`. Asserts on returned DTOs, never models.
- **`test_services.py`** (5 tests, **no** `@django_db`) — local `_FakeRepo` + `_FakeMentor` classes. Covers list passthrough, mentor true/false, swallow-and-log on raise (asserted via `caplog`), `UserNotFound` propagation without calling the mentor service.
- **`test_forms.py`** (8 tests) — bad/lowercase/blank role, zero/negative/garbage page, empty q, valid combo.
- **`test_views.py`** (20 tests) — admin list rendering, paginate+filter (page=2 with QS preserved), q-search, row→detail link with `?return=` preservation, empty state, permissive parsing of `role=BOGUS&page=abc`, detail mentor true/false/raises (mocked at `DefaultMentorService.is_mentor`), safe-return helper accept + reject (`https://`, oversized 600-char), 404 unknown matrícula, anon redirect, and 403 for ALUMNO/DOCENTE/CONTROL_ESCOLAR/RESPONSABLE_PROGRAMA. Auth uses real JWT middleware; JWT minting builds the inverse of `PROVIDER_ROLE_MAP` because internal `Role.value.lower()` does not equal the provider claim string for every role (notably `RESPONSABLE_PROGRAMA` → `resp_programa`).

No browser-tier tests — internal admin tooling, low risk; matches the `reportes` posture.

## Settings / migrations

- **No migrations.** No new model, no new field.
- **No new env vars.** `PAGE_SIZE = 25` is a feature constant.
- **No INSTALLED_APPS change.** `usuarios.directory.urls` is included from `usuarios.urls`.

## Related Specs

- [requirements.md](./requirements.md) — WHAT/WHY.
- [`specs/apps/usuarios/design.md`](../design.md) — parent app: `User` model, `UserRepository` (DEBUG-only `list_all`), `AdminRequiredMixin`.
- [`specs/apps/mentores/catalog/design.md`](../../mentores/catalog/design.md) — `MentorService.is_mentor` consumed live for the detail page.
- [`specs/apps/reportes/dashboard/design.md`](../../reportes/dashboard/design.md) — reference for permissive querystring parsing posture (RF-REP-06).
- [`specs/planning/013-user-directory/plan.md`](../../../planning/013-user-directory/plan.md) — implementation blueprint (kept for historical reference).
- [`.claude/rules/django-code-architect.md`](../../../../.claude/rules/django-code-architect.md) — the architectural law this design implements.
