# 002 — Auth & Users

## Summary

Wire authentication for a server-rendered Django app whose login is **delegated to an external provider**. The provider issues a JWT after its own login flow and redirects back to our `/auth/callback` endpoint with the token. Our middleware validates the JWT on every request, materializes a Django user, sets `request.user`, and provides role-based permission mixins. SIGA integration provides on-demand enrichment of user data (name, programa, semestre) with a deterministic JWT-only fallback.

We **do not** issue tokens, run a login form, or store passwords. The callback handshake and JWT cookie shape are pending coordination with the provider team — see Open Questions.

## Depends on

- **001** — `apps/_shared/auth.py` (JWT helpers), `AppErrorMiddleware`, `RequestIDMiddleware`, `AuthenticationRequired` exception, base templates.

## Affected Apps / Modules

- `apps/usuarios/` — new app
- `apps/_shared/auth.py` — extended if needed (e.g., role normalization helper)
- `config/settings/base.py` — middleware, env vars, `AUTH_USER_MODEL`
- `config/urls.py` — mount `apps.usuarios.urls` under `/auth/`

## References

- [global/requirements.md](../../global/requirements.md) — RNF-01 (auth externa), RNF-02 (SIGA), RF-06 (roles)
- [global/architecture.md](../../global/architecture.md) — Authentication flow diagram
- [.claude/skills/django-patterns/features.md](../../../.claude/skills/django-patterns/features.md) — feature package layout
- The whiteboard photo: Provider issues JWT carrying `matricula` and `correo`; routes through nginx; SIGA reachable via REST.

## Implementation Details

### App layout

```
apps/usuarios/
├── __init__.py
├── apps.py
├── urls.py                          # /auth/callback, /auth/logout, /auth/me
├── constants.py                     # Role enum, claim keys
├── exceptions.py                    # InvalidJwt, RoleNotRecognized, SigaUnavailable
├── models/
│   ├── __init__.py
│   └── user.py                      # one model per file (custom User)
├── schemas.py                       # Pydantic DTOs
├── permissions.py                   # role-based mixins
├── dependencies.py                  # DI factories
├── middleware.py                    # JwtAuthenticationMiddleware (replaces Django's)
├── repositories/
│   └── user/
│       ├── __init__.py
│       ├── interface.py
│       └── implementation.py        # OrmUserRepository
├── services/
│   ├── role_resolver/
│   │   ├── __init__.py
│   │   ├── interface.py
│   │   └── jwt_implementation.py    # current: read role from claim
│   ├── user_service/
│   │   ├── __init__.py
│   │   ├── interface.py
│   │   └── implementation.py        # get_or_create_from_claims, get_by_matricula
│   └── siga/
│       ├── __init__.py
│       ├── interface.py
│       ├── http_implementation.py   # requests.get with timeout, ExternalServiceError on failure
│       └── jwt_fallback.py          # used when SIGA is down
├── views/
│   ├── __init__.py
│   ├── callback.py                  # GET /auth/callback?token=…
│   ├── logout.py                    # GET /auth/logout
│   └── me.py                        # GET /auth/me  (current profile)
├── migrations/
└── tests/
    ├── __init__.py
    ├── factories.py
    ├── fakes.py                     # InMemoryUserRepository, FakeSigaService
    ├── test_middleware.py
    ├── test_role_resolver.py
    ├── test_user_service.py
    ├── test_user_repository.py
    ├── test_siga_service.py
    ├── test_views_callback.py
    ├── test_views_logout.py
    └── test_permissions.py
```

### Data model — `apps/usuarios/models/user.py`

```python
class User(AbstractBaseUser):
    matricula = CharField(max_length=20, primary_key=True)
    email = EmailField(unique=True)
    role = CharField(max_length=32, choices=Role.choices)
    full_name = CharField(max_length=200, blank=True)         # cached from SIGA, optional
    programa = CharField(max_length=200, blank=True)          # cached from SIGA, optional
    semestre = IntegerField(null=True, blank=True)            # cached from SIGA, optional
    last_login_at = DateTimeField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    USERNAME_FIELD = "matricula"
    REQUIRED_FIELDS = ["email", "role"]

    objects = UserManager()  # required by Django auth, even if we never use create_user

    @property
    def is_authenticated(self) -> bool: return True
    @property
    def is_anonymous(self) -> bool: return False
```

We deliberately avoid `AbstractUser` because we have no password, no username, no `first_name`/`last_name` from Django's default. We provide a `UserManager` with stubbed `create_user` (raises `NotImplementedError` — auth is external) and `get_by_natural_key(matricula)` for compatibility with Django's auth machinery.

### `Role` enum (`constants.py`)

```python
class Role(str, Enum):
    ALUMNO = "ALUMNO"
    DOCENTE = "DOCENTE"
    CONTROL_ESCOLAR = "CONTROL_ESCOLAR"
    RESPONSABLE_PROGRAMA = "RESPONSABLE_PROGRAMA"
    ADMIN = "ADMIN"

    @classmethod
    def choices(cls): return [(m.value, m.value.replace("_", " ").title()) for m in cls]
```

The provider's claim string is mapped via a dict in `RoleResolver` so changes to provider vocabulary don't ripple.

### Pydantic DTOs (`schemas.py`)

```python
class UserDTO(BaseModel):
    model_config = {"frozen": True}
    matricula: str
    email: str
    role: Role
    full_name: str = ""
    programa: str = ""
    semestre: int | None = None
    is_mentor: bool = False           # populated by mentores service when needed (NOT stored on User)

class CreateOrUpdateUserInput(BaseModel):
    matricula: str
    email: str
    role: Role
    full_name: str = ""

class SigaProfile(BaseModel):
    matricula: str
    full_name: str
    email: str
    programa: str
    semestre: int | None
```

### Exceptions (`exceptions.py`)

```python
class InvalidJwt(Unauthorized):           code = "invalid_jwt";          user_message = "Tu sesión no es válida. Inicia sesión nuevamente."
class RoleNotRecognized(Unauthorized):    code = "role_not_recognized";  user_message = "Tu rol no está autorizado para usar este sistema."
class SigaUnavailable(ExternalServiceError):
                                          code = "siga_unavailable";     user_message = "El sistema de información académica no responde. Continuamos con datos básicos."
```

### Repository — `repositories/user/`

```python
class UserRepository(ABC):
    @abstractmethod
    def get_by_matricula(self, matricula: str) -> UserDTO: ...      # raises NotFound subclass
    @abstractmethod
    def upsert(self, input_dto: CreateOrUpdateUserInput) -> UserDTO: ...
    @abstractmethod
    def update_last_login(self, matricula: str, *, when: datetime) -> None: ...
```

`OrmUserRepository` uses `User.objects.get(pk=matricula)`, catching `User.DoesNotExist` → raises a feature-level `UserNotFound` (subclass of `NotFound`). `upsert` uses `update_or_create`.

### Services

#### `RoleResolver` (`services/role_resolver/`)

```python
class RoleResolver(ABC):
    @abstractmethod
    def resolve(self, claims: JwtClaims) -> Role: ...   # raises RoleNotRecognized
```

Current implementation (`jwt_implementation.py`) maps `claims.rol` strings via a dict:

```python
PROVIDER_ROLE_MAP: dict[str, Role] = {
    "alumno": Role.ALUMNO,
    "docente": Role.DOCENTE,
    "control_escolar": Role.CONTROL_ESCOLAR,
    "resp_programa": Role.RESPONSABLE_PROGRAMA,
    "admin": Role.ADMIN,
}
```

This abstraction exists because **personal roles (Control Escolar, Responsable de Programa) might not be carried by the provider's JWT** — see OQ-002-2. If the provider does not emit them, a future implementation (`directory_implementation.py`) will look the matricula up in an internal directory table without changing the rest of the codebase.

#### `UserService` (`services/user_service/`)

```python
class UserService(ABC):
    @abstractmethod
    def get_or_create_from_claims(self, claims: JwtClaims) -> UserDTO: ...
    @abstractmethod
    def get_by_matricula(self, matricula: str) -> UserDTO: ...
    @abstractmethod
    def hydrate_from_siga(self, matricula: str) -> UserDTO: ...   # call when extra data needed
```

`get_or_create_from_claims` flow:
1. `role = role_resolver.resolve(claims)`
2. `repo.upsert(CreateOrUpdateUserInput(matricula=claims.sub, email=claims.email, role=role))`
3. `repo.update_last_login(claims.sub, when=now)`
4. Return `UserDTO`.

`hydrate_from_siga` flow:
1. Try `siga_service.fetch_profile(matricula)`. On `SigaUnavailable`: return existing `UserDTO` unchanged (logging a warning). Never raise to the caller.
2. On success: `repo.upsert(...)` with the enriched data, return updated DTO.

#### `SigaService` (`services/siga/`)

```python
class SigaService(ABC):
    @abstractmethod
    def fetch_profile(self, matricula: str) -> SigaProfile: ...   # raises SigaUnavailable
```

`HttpSigaService` uses `requests.get(f"{base}/alumnos/{matricula}", timeout=settings.SIGA_TIMEOUT_SECONDS)`. On `Timeout` / `ConnectionError` / non-2xx: raise `SigaUnavailable`. On 404: raise `NotFound`. Successful response is parsed into `SigaProfile` via `model_validate`.

### Middleware — `JwtAuthenticationMiddleware`

Replaces Django's `AuthenticationMiddleware` in the chain.

```
on each request:
  1. token = read_token(request)
       → cookie "stk" first, then Authorization: Bearer <token>
  2. If no token:
       request.user = AnonymousUser()
       return  # views decide whether to require auth
  3. claims = decode_jwt(token, secret=settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
       → raises AuthenticationRequired on failure (caught by AppErrorMiddleware → 401 redirect)
  4. user_dto = user_service.get_or_create_from_claims(claims)
  5. orm_user = User.objects.get(pk=user_dto.matricula)   # for Django's auth contract
  6. request.user = orm_user
     request.user_dto = user_dto                          # typed access without ORM lookups
```

Skip the middleware for `/health/`, `/static/*`, `/media/*`, and `/auth/callback` (the callback is what *issues* the cookie).

### `/auth/callback` view

```
GET /auth/callback?token=<jwt>&return=<encoded-url>
  1. validate token → claims
  2. UserService.get_or_create_from_claims(claims)
  3. (best-effort) UserService.hydrate_from_siga(matricula) — swallow SigaUnavailable
  4. response = redirect(return or "/solicitudes/")
  5. response.set_cookie(
        key="stk",
        value=token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="Lax",
        max_age=claims.exp - now_unix(),
     )
  6. return response
```

`return` URL is validated against `ALLOWED_HOSTS` to prevent open-redirect.

### `/auth/logout` view

```
GET /auth/logout
  1. response = redirect(settings.AUTH_PROVIDER_LOGOUT_URL)
  2. response.delete_cookie("stk")
  3. return response
```

If `AUTH_PROVIDER_LOGOUT_URL` is empty: redirect to `/`.

### `/auth/me` view (debug aid + profile read)

`LoginRequiredMixin`-protected GET that renders `usuarios/me.html` with `request.user_dto`. Useful for verifying the integration end-to-end.

### Permission mixins (`permissions.py`)

```python
class LoginRequiredMixin:
    """Raises AuthenticationRequired (caught by middleware → redirect to provider)."""

class RoleRequiredMixin:
    required_roles: ClassVar[set[Role]] = set()

class AlumnoRequiredMixin(RoleRequiredMixin):       required_roles = {Role.ALUMNO}
class DocenteRequiredMixin(RoleRequiredMixin):      required_roles = {Role.DOCENTE}
class PersonalRequiredMixin(RoleRequiredMixin):     required_roles = {Role.CONTROL_ESCOLAR, Role.RESPONSABLE_PROGRAMA}
class AdminRequiredMixin(RoleRequiredMixin):        required_roles = {Role.ADMIN}
```

`RoleRequiredMixin.dispatch`: if anonymous → raise `AuthenticationRequired`; if role not in `required_roles` → raise `Unauthorized`. Both caught by `AppErrorMiddleware`.

### URLs (`apps/usuarios/urls.py`)

| URL | View | Method | Auth |
|---|---|---|---|
| `auth/callback` | `CallbackView` | GET | none (entry point) |
| `auth/logout` | `LogoutView` | GET | optional |
| `auth/me` | `MeView` | GET | required |

Mounted in `config/urls.py` via `path("", include(("apps.usuarios.urls", "usuarios")))` so the URLs are exactly `/auth/callback`, `/auth/logout`, `/auth/me`.

### `dependencies.py`

```python
def get_user_repository() -> UserRepository: ...
def get_role_resolver() -> RoleResolver: ...
def get_siga_service() -> SigaService: ...
def get_user_service() -> UserService:
    return DefaultUserService(
        user_repository=get_user_repository(),
        role_resolver=get_role_resolver(),
        siga_service=get_siga_service(),
        logger=logging.getLogger("apps.usuarios.user_service"),
    )
```

### Settings additions

| Var | Required in prod | Notes |
|---|---|---|
| `JWT_SECRET` | yes | shared with provider |
| `JWT_ALGORITHM` | default `HS256` | |
| `AUTH_PROVIDER_LOGIN_URL` | yes | redirect target on 401 |
| `AUTH_PROVIDER_LOGOUT_URL` | optional | empty → redirect home |
| `SIGA_BASE_URL` | yes | API root |
| `SIGA_TIMEOUT_SECONDS` | default `5` | |
| `SESSION_COOKIE_SECURE` | `True` in prod | |
| `LOGIN_URL` (Django) | dynamically set to `AUTH_PROVIDER_LOGIN_URL` | |

### Cross-app dependencies

This initiative is consumed by **every** later initiative (via `UserService` and the permission mixins). It does not depend on any feature app.

### Sequencing

1. Create `apps/usuarios/` skeleton + `apps.py`; add to `INSTALLED_APPS`.
2. `models/user.py` + `UserManager` + initial migration. Verify `python manage.py migrate` runs.
3. `constants.py` (`Role`).
4. `schemas.py`, `exceptions.py`.
5. Repository: interface + ORM impl + tests (real DB).
6. Fakes: `tests/fakes.py` with `InMemoryUserRepository`, `FakeSigaService`.
7. `services/siga/` interface + http impl + tests (HTTP mocked via `responses`).
8. `services/role_resolver/` interface + jwt impl + tests.
9. `services/user_service/` interface + default impl + tests (uses fake repo + fake siga).
10. `dependencies.py`.
11. `middleware.py` + tests.
12. `permissions.py` + tests.
13. Views + templates + tests.
14. Wire into `config/urls.py` and replace `AuthenticationMiddleware` with `JwtAuthenticationMiddleware` in `MIDDLEWARE`.
15. Manual end-to-end: mint a dev JWT, hit `/auth/callback?token=…&return=/auth/me`, verify redirect + cookie + profile render.


## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)
- Cross-feature: a JWT-validated request reaches a protected view; expired/invalid tokens are rejected with the right redirect.

### Browser (Tier 2 — `pytest-playwright`)
- Golden path: external login → land on dashboard → logout. (UI portion of auth.)

## Acceptance Criteria

- [ ] `User` migration applies cleanly; `AUTH_USER_MODEL = "usuarios.User"` accepted by Django.
- [ ] Hitting any protected URL without a token redirects to `AUTH_PROVIDER_LOGIN_URL` (with `return=` round-trip).
- [ ] `/auth/callback?token=<valid>&return=/foo` sets the `stk` cookie and 302s to `/foo`; `return` outside `ALLOWED_HOSTS` 302s to `/`.
- [ ] `/auth/callback?token=<expired>` raises `AuthenticationRequired` → middleware redirects to provider login.
- [ ] Subsequent requests with the cookie populate `request.user` and `request.user_dto`.
- [ ] `RoleRequiredMixin` denies wrong-role users with 403 `_shared/error.html` (or JSON for AJAX).
- [ ] SIGA timeout (mocked) does not block login: `/auth/callback` succeeds even if SIGA is down; `request.user_dto.full_name` falls back to whatever was previously stored or empty string.
- [ ] `/auth/me` renders `usuarios/me.html` with all DTO fields.
- [ ] Tests: views ≥ 80% line, services ≥ 95% line, repository ≥ 95% line.
- [ ] No service or repository imports `HttpRequest`; verified by grep in CI.

## Open Questions

- **OQ-002-1 (PENDING)** — JWT transport from provider. Plan assumes Option 3 (provider redirects to `/auth/callback?token=…`, we set an HTTP-only cookie `stk`). Awaiting confirmation from the provider team. If they emit a cross-domain cookie directly, we drop the callback and the middleware reads the cookie they set. If they emit a Bearer header from a frontend, we drop the cookie and read `Authorization`.
- **OQ-002-2** — Personal roles (CONTROL_ESCOLAR, RESPONSABLE_PROGRAMA): does the provider's JWT carry these? If yes, `JwtRoleResolver` is sufficient. If no, we need a `DirectoryRoleResolver` backed by a small admin-managed mapping table — proposed deferred to a 002-bis if it materializes. The `RoleResolver` ABC absorbs the change.
- **OQ-002-3** — JWT renewal / refresh: does the cookie expire mid-session? Plan currently sets cookie `max_age = exp - now`. If the provider issues short-lived tokens, we may need a refresh-token flow. Defer until provider contract is known.
- **OQ-002-4** — User deactivation: if the provider revokes a user, our cached `User` row stays. Acceptable for v1 (the next request fails the JWT check). Revisit if compliance asks.
