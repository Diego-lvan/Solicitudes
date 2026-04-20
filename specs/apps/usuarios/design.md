# `usuarios` — Design

> HOW the auth subsystem is built. Long-lived reference; promoted from `planning/002-auth-users/plan.md` after that initiative shipped. Update when behavior changes; do **not** update with day-to-day implementation churn.

## Architectural shape

```
View  ──▶  Service  ──▶  Repository  ──▶  ORM
                │
                └──▶  RoleResolver  (provider claim → Role)
                │
                └──▶  SigaService   (HTTP, best-effort)
```

All cross-layer calls go through Pydantic DTOs (`UserDTO`, `CreateOrUpdateUserInput`, `SigaProfile`). `JwtClaims` (defined in `_shared/auth.py`) crosses the middleware → service boundary.

## Data model — `usuarios.User`

`AbstractBaseUser`-based, no password use, keyed on `matricula`.

| Field | Type | Notes |
|---|---|---|
| `matricula` | `CharField(20)` `primary_key` | Provider's `sub` claim. |
| `email` | `EmailField` `unique` | Owned by the auth provider; never overwritten by SIGA. |
| `role` | `CharField(32)` `choices=Role.choices()` | One of five values. |
| `full_name` / `programa` | `CharField(200)` `blank` | Cached SIGA fields; sticky on JWT-only re-login. |
| `semestre` | `IntegerField` `null/blank` | Cached SIGA field; sticky on JWT-only re-login. |
| `last_login_at` | `DateTimeField` `null/blank` | Stamped by `UserService.get_or_create_from_claims`. Separate from `AbstractBaseUser.last_login` to avoid Django's signal handlers. |
| `created_at` / `updated_at` | `DateTimeField` `auto_now_add` / `auto_now` | Audit. |

`Meta.db_table = "usuarios_user"`. `USERNAME_FIELD = "matricula"`, `REQUIRED_FIELDS = ["email", "role"]`.

`UserManager` rejects `create_user`/`create_superuser` with `NotImplementedError` — auth is external. `get_by_natural_key` is keyed on `matricula`.

`AUTH_USER_MODEL = "usuarios.User"`.

## Role enum

```python
class Role(StrEnum):
    ALUMNO, DOCENTE, CONTROL_ESCOLAR, RESPONSABLE_PROGRAMA, ADMIN
```

Provider claim string → `Role` mapping is isolated in `usuarios.constants.PROVIDER_ROLE_MAP` and consumed by `JwtRoleResolver` (case-insensitive lookup). Unknown roles raise `RoleNotRecognized`.

## Pydantic DTOs (`schemas.py`)

- `UserDTO` — frozen, returned by repository and service. `email: EmailStr`, `role: Role`, optional cached SIGA fields, plus `is_mentor: bool` (populated by the future `mentores` service, never stored on `User`).
- `CreateOrUpdateUserInput` — input to `UserRepository.upsert`. `EmailStr`, `Role`.
- `SigaProfile` — shape returned by `SigaService.fetch_profile`.

## Exception hierarchy (`exceptions.py`)

| Class | Subclass of | HTTP |
|---|---|---|
| `InvalidJwt` | `AuthenticationRequired` (`_shared`) | 401 |
| `RoleNotRecognized` | `Unauthorized` (`_shared`) | 403 |
| `UserNotFound` | `NotFound` (`_shared`) | 404 |
| `SigaUnavailable` | `ExternalServiceError` (`_shared`) | 502 |

The repository **always** translates `User.DoesNotExist` to `UserNotFound`; Django exceptions never leak.

## Repository — `UserRepository`

Interface in `repositories/user/interface.py`, ORM impl in `repositories/user/implementation.py`. Methods:

| Method | Behavior |
|---|---|
| `get_by_matricula(matricula)` | Returns `UserDTO`; raises `UserNotFound`. |
| `upsert(input_dto)` | `update_or_create` inside `transaction.atomic`. **Empty strings / `None` mean "no information"** and never overwrite cached values — this is the contract that protects SIGA-cached fields on JWT-only re-logins. |
| `update_last_login(matricula, when=...)` | `.filter().update()`; raises `UserNotFound` if 0 rows updated. |
| `list_all()` | Returns every persisted user as a list of DTOs, ordered by role then matricula. **DEBUG-only**: used by the dev-login picker. Production code paths should not enumerate users. |

## Services

### `RoleResolver` (`services/role_resolver/`)

ABC with one method `resolve(claims) -> Role`. Default impl `JwtRoleResolver` reads `claims.rol` and looks up `PROVIDER_ROLE_MAP`. A future `DirectoryRoleResolver` (anticipated by OQ-002-2) can be added without changing any consumer.

### `SigaService` (`services/siga/`)

ABC with one method `fetch_profile(matricula) -> SigaProfile`.

- `HttpSigaService` — calls `{base_url}/alumnos/{matricula}` with a hard timeout. Maps:
  - 404 → `UserNotFound`
  - 5xx, timeout, connection error, malformed JSON, missing/invalid URL → `SigaUnavailable` (broadened to `requests.RequestException` so dev/test runs with empty `SIGA_BASE_URL` are tolerated).
- `JwtFallbackSigaService` — builds a minimal profile from the captured JWT claims; used for offline / dev environments. Currently unwired; available as a drop-in replacement.

> **Profile shape is alumno-only today.** `SigaProfile` carries `matricula, email, full_name, programa, semestre`. Whether SIGA exposes the same shape (or a different one with `departamento`, `categoria`, etc.) for docentes / control escolar is **OQ-002-5** in `requirements.md`. Until SIGA confirms, the system degrades gracefully because every academic field on `UserDTO` is optional — a docente login simply gets empty `programa`/`semestre`. When the docente shape lands, extend `SigaProfile` additively and downstream consumers (e.g., initiative 011's `FieldSource` enum) gain new variants.

### `UserService` (`services/user_service/`)

ABC with three methods:

- `get_or_create_from_claims(claims) -> UserDTO` — resolves role → upsert → stamps `last_login_at`. Called by middleware on every authenticated request.
- `get_by_matricula(matricula) -> UserDTO` — read-through; raises `UserNotFound`.
- `hydrate_from_siga(matricula) -> UserDTO` — best-effort enrichment. Swallows `SigaUnavailable`. Never overwrites the auth-provider email.

## Middleware — `JwtAuthenticationMiddleware`

Replaces Django's `AuthenticationMiddleware`. Reads `stk` cookie first, then `Authorization: Bearer`. Decodes via `_shared.auth.decode_jwt`. On `AuthenticationRequired` raised inside the middleware (Django doesn't run `process_exception` for middleware-raised errors), redirects inline to `settings.LOGIN_URL` — same intent as `AppErrorMiddleware`. On success, sets:

- `request.user` — ORM `User` instance (the *one* sanctioned ORM read outside a repository — required by Django's auth contract).
- `request.user_dto` — typed `UserDTO`.

Skip-paths (`SKIP_PREFIXES`): `/health/`, `/static/`, `/media/`, `/auth/callback` (issues the cookie), `/auth/logout` (must work with stale cookie), `/auth/dev-login` (DEBUG-only picker).

## Permission mixins (`permissions.py`)

- `LoginRequiredMixin` — raises `AuthenticationRequired` for anonymous users.
- `RoleRequiredMixin` — `required_roles: ClassVar[frozenset[Role]]`. Raises `Unauthorized` for wrong-role.
- `Alumno/Docente/Personal/Admin RequiredMixin` — preset `required_roles`.

## URLs (`urls.py`, namespaced `usuarios:`)

| URL | View | Method | Auth |
|---|---|---|---|
| `auth/callback` | `CallbackView` | GET | none (entry point) |
| `auth/logout` | `LogoutView` | GET | optional |
| `auth/me` | `MeView` | GET | required |
| `auth/dev-login` | `DevLoginView` | GET, POST | DEBUG-only — route mounted only when `settings.DEBUG=True` |

`/auth/dev-login` is removed in initiative 010 along with its template, view, tests, the `if settings.DEBUG` block in `urls.py`, and the corresponding `SKIP_PREFIXES` entry.

## Cookie contract (`stk`)

| Attribute | Value |
|---|---|
| `httponly` | `True` |
| `secure` | `settings.SESSION_COOKIE_SECURE` (`True` in prod) |
| `samesite` | `Lax` |
| `max_age` | `exp − now()` (seconds) — derived from JWT claims |

## Settings (`config/settings/base.py`, hardened in `prod.py`)

| Var | Default | Required in prod |
|---|---|---|
| `JWT_SECRET` | `""` | yes (`_required`) |
| `JWT_ALGORITHM` | `"HS256"` | no |
| `AUTH_PROVIDER_LOGIN_URL` | `"/auth/login/"` | yes (`_required`) |
| `AUTH_PROVIDER_LOGOUT_URL` | `""` | no (empty → redirect to `/`) |
| `SIGA_BASE_URL` | `""` | yes (`_required`) |
| `SIGA_TIMEOUT_SECONDS` | `5` | no |
| `LOGIN_URL` | aliased to `AUTH_PROVIDER_LOGIN_URL` | (Django convention) |

Both `JwtAuthenticationMiddleware` and `_shared/middleware/error_handler.AppErrorMiddleware` redirect to `settings.LOGIN_URL` on `AuthenticationRequired`.

## Cross-feature contract

Other features must consume identity through `UserService` (the interface), never the repository. `UserDTO.is_mentor` is the contract field that `mentores` (initiative 008) populates on demand — not a column on `User`.

## Test stack

- **Repository tests** — real DB (`pytest.mark.django_db`), assert returned DTOs.
- **Service tests** — `tests/fakes.py` provides `InMemoryUserRepository`, `FakeRoleResolver`, `FakeSigaService` (with `unavailable`/`not_found` flags + a `calls` audit list). `freezegun` for time, `responses` for HTTP.
- **View tests** — Django `Client`, assert on status / cookie / rendered content.
- **Middleware tests** — `RequestFactory` + the middleware constructed with `user_service_factory` injection.
- **Tier 1 E2E** — `test_e2e_tier1.py` walks the full middleware chain with cookie persistence.
- **Tier 2 E2E** — deferred to initiative 010 (real provider).

## Coverage thresholds

| Layer | Threshold |
|---|---|
| Views | ≥ 80% line |
| Services | ≥ 95% line |
| Repository | ≥ 95% line |

Per-initiative measurements live in the corresponding `planning/<NNN>/changelog.md`.

## Related Specs

- [requirements.md](./requirements.md) — WHAT/WHY.
- [`specs/flows/external-login.md`](../../flows/external-login.md) — end-to-end sequence.
- [`specs/planning/002-auth-users/`](../../planning/002-auth-users/) — initiative that shipped this.
- [`specs/planning/010-external-auth-provider/`](../../planning/010-external-auth-provider/) — provider integration follow-up.
- `.claude/rules/django-code-architect.md` — architectural law.
