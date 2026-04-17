# 001 — Project Setup & Base

## Summary

Bootstrap the Django 5 project with the layered architecture described in `architecture.md`: configuration split, `apps/_shared/` cross-cutting infrastructure, root URL routing, base templates, request-id middleware, structured logging, and the `AppError` exception hierarchy. **Docker is part of this first step** — a multi-stage `Dockerfile` (with WeasyPrint system deps baked in), a full dev Compose stack (`web` + `db` + `mailhog`), and a Postgres-only test Compose stack that follows the rules in `.claude/skills/django-patterns/e2e.md`. No business features land in this initiative — every other initiative depends on this foundation being correct.

## Depends on

None — this is the first initiative.

## Affected Apps / Modules

- `config/` — settings split (`base`, `dev`, `prod`, `test_postgres`), root URLs, WSGI/ASGI entrypoints
- `apps/_shared/` — exceptions, middleware, auth helpers, pagination DTO, PDF wrapper
- `templates/` — `base.html`, `components/`, `_shared/error.html`
- `static/` — Bootstrap 5 assets, project CSS shell
- `requirements.txt`, `pyproject.toml`, `.env.example`, `manage.py`
- **`Dockerfile`, `docker-compose.dev.yml`, `docker-compose.test.yml`, `.dockerignore`, `Makefile`** — containerization and developer ergonomics

## References

- [global/requirements.md](../../global/requirements.md) — RNF-01 (auth externa), RNF-03 (microservicio independiente), RT-04 (HTTPS), RT-08 (es-MX)
- [global/architecture.md](../../global/architecture.md) — tech stack, layout, layer flow
- [.claude/rules/django-code-architect.md](../../../.claude/rules/django-code-architect.md) — architectural rules (mandatory)
- [.claude/rules/django-test-architect.md](../../../.claude/rules/django-test-architect.md) — test conventions
- `.claude/skills/django-patterns/platform.md` — base templates, middleware, settings examples
- `.claude/skills/django-patterns/e2e.md` — **canonical** rules for the testing stack: default `live_server`, separate `docker-compose.test.yml`, `test_postgres` settings, Make targets

## Implementation Details

### Repository layout produced by this initiative

```
solicitudes/
├── manage.py
├── pyproject.toml                  # ruff, mypy, pytest config
├── requirements.txt                # pinned runtime deps
├── requirements-dev.txt            # pinned dev/test deps
├── .env.example
├── .gitignore                      # adds media/, .env, __pycache__, .pytest_cache, test-results/, playwright-report/
├── Dockerfile                      # multi-stage (builder + runtime), WeasyPrint deps baked in
├── .dockerignore
├── docker-compose.dev.yml          # web + db + mailhog
├── docker-compose.test.yml         # postgres-only (no app container), tmpfs, port 55432
├── Makefile                        # up/down/logs/test/e2e/e2e-postgres/e2e-headed
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   ├── prod.py
│   │   └── test_postgres.py        # opt-in Postgres for live_server tests; default tests use SQLite
│   ├── urls.py                     # root, namespaced per-app includes
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── __init__.py
│   └── _shared/
│       ├── __init__.py
│       ├── apps.py                 # AppConfig (name = "apps._shared")
│       ├── exceptions.py
│       ├── middleware/
│       │   ├── __init__.py
│       │   ├── request_id.py
│       │   ├── error_handler.py
│       │   └── logging.py
│       ├── auth.py                 # JWT decode helper (no Django imports)
│       ├── pagination.py
│       ├── pdf.py                  # WeasyPrint thin wrapper
│       ├── logging_config.py       # dictConfig builder
│       └── tests/
│           ├── __init__.py
│           ├── test_exceptions.py
│           ├── test_middleware_request_id.py
│           ├── test_middleware_error_handler.py
│           ├── test_auth.py
│           ├── test_pagination.py
│           └── test_pdf.py
├── templates/
│   ├── base.html                   # Bootstrap 5 layout, blocks
│   ├── components/
│   │   ├── nav.html
│   │   ├── alerts.html             # django.contrib.messages renderer
│   │   ├── pagination.html
│   │   └── empty_state.html
│   └── _shared/
│       ├── error.html              # generic AppError fallback
│       └── 404.html
├── static/
│   ├── css/
│   │   └── app.css
│   ├── js/
│   │   └── app.js
│   └── vendor/                     # bootstrap, htmx (if used)
├── tests-e2e/                      # skeleton; populated as initiatives add browser flows
│   └── README.md                   # points at .claude/skills/django-patterns/e2e.md
├── media/                          # gitignored
└── locale/                         # es_MX (placeholder; populated as features add copy)
```

### Settings split

`config/settings/base.py` — shared defaults; `dev.py` and `prod.py` override.

| Concern | base.py | dev.py | prod.py |
|---|---|---|---|
| `DEBUG` | `False` | `True` | `False` |
| `ALLOWED_HOSTS` | `[]` | `["*"]` | from env `ALLOWED_HOSTS` (comma-sep) |
| Database | placeholder | SQLite at `BASE_DIR / "db.sqlite3"` | PostgreSQL via env (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`) |
| `SECRET_KEY` | from env, fail loudly if missing | `dev-only-secret-…` | from env, mandatory |
| Static | `STATIC_URL = "/static/"`, `STATICFILES_DIRS = [BASE_DIR/"static"]` | + `STATIC_ROOT = BASE_DIR/"staticfiles"` | + `STATIC_ROOT`, manifest storage |
| Media | `MEDIA_URL = "/media/"`, `MEDIA_ROOT = BASE_DIR/"media"` | same | `MEDIA_ROOT` from env |
| Logging | dictConfig from `apps._shared.logging_config` | DEBUG to stdout | INFO to stdout, JSON formatter |
| `LANGUAGE_CODE` | `"es-mx"` | — | — |
| `TIME_ZONE` | `"America/Mexico_City"` | — | — |
| `USE_TZ` | `True` | — | — |
| Email | `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"` | console backend | SMTP via env (host, port, user, pass, TLS) |
| Auth | `AUTH_USER_MODEL = "usuarios.User"` (forward reference for 002) | — | — |
| `MIDDLEWARE` | order defined below | — | — |

### Middleware order (top to bottom = request order)

1. `django.middleware.security.SecurityMiddleware`
2. `django.contrib.sessions.middleware.SessionMiddleware`
3. `django.middleware.common.CommonMiddleware`
4. `django.middleware.csrf.CsrfViewMiddleware`
5. **`apps._shared.middleware.request_id.RequestIDMiddleware`** — assigns `request.id = uuid4().hex` (or echoes incoming `X-Request-ID`); attaches to log records via a `contextvars`-backed filter.
6. **`apps._shared.middleware.logging.StructuredLoggingMiddleware`** — logs `request.start` and `request.end` with method, path, status, duration_ms, request_id.
7. `django.contrib.auth.middleware.AuthenticationMiddleware` *(replaced in 002 by JWT middleware that sets `request.user` from the JWT)*
8. `django.contrib.messages.middleware.MessageMiddleware`
9. `django.middleware.clickjacking.XFrameOptionsMiddleware`
10. **`apps._shared.middleware.error_handler.AppErrorMiddleware`** — last, so it catches anything raised below.

### `apps/_shared/exceptions.py`

```python
class AppError(Exception):
    code: str = "app_error"
    user_message: str = "Ocurrió un error."
    http_status: int = 500
    def __init__(self, message: str | None = None) -> None: ...

class NotFound(AppError):           code = "not_found";          http_status = 404; user_message = "El recurso solicitado no existe."
class Conflict(AppError):           code = "conflict";           http_status = 409; user_message = "La operación entra en conflicto con el estado actual."
class Unauthorized(AppError):       code = "unauthorized";       http_status = 403; user_message = "No tienes permiso para realizar esta acción."
class AuthenticationRequired(AppError):
                                    code = "authentication_required"; http_status = 401; user_message = "Inicia sesión para continuar."
class DomainValidationError(AppError):
                                    code = "validation_error";   http_status = 422; user_message = "Los datos no son válidos."
    # carries field_errors: dict[str, list[str]]
class ExternalServiceError(AppError):
                                    code = "external_service_error"; http_status = 502; user_message = "Un servicio externo no está disponible. Intenta más tarde."
```

`DomainValidationError.__init__(message, field_errors=None)` so views can re-render forms with field-attached errors.

### `AppErrorMiddleware` behavior

`process_exception(request, exception)`:

1. If `isinstance(exception, AppError)`:
   - Log `error.app_error` with `request_id`, `code`, `path`, `user_id` (if known).
   - If `request.headers.get("HX-Request")` or `Accept: application/json`: return `JsonResponse({"code", "message", "field_errors"}, status=exc.http_status)`.
   - Else: render `_shared/error.html` with `{code, message, http_status, request_id}` at the right status.
   - For `AuthenticationRequired` (401): redirect to the auth provider (set in 002; for 001 a placeholder URL `LOGIN_REDIRECT_URL`).
2. If not an `AppError`: re-raise (Django's debug page / 500 handler takes over). Production: log `error.unhandled` with stack trace + `request_id`, render `_shared/error.html` with code `internal_error`.

### `apps/_shared/auth.py`

Pure-Python JWT helpers, no Django imports — re-used by middleware, services, tests.

```python
def decode_jwt(token: str, *, secret: str, algorithms: list[str]) -> dict[str, Any]: ...
class JwtClaims(BaseModel):
    sub: str           # matrícula
    email: str
    rol: str           # raw role string from provider
    exp: int
    iat: int
def parse_claims(payload: dict[str, Any]) -> JwtClaims: ...
```

Implementation: `PyJWT` library. Raises `AuthenticationRequired` on `ExpiredSignatureError` / `InvalidTokenError`.

### `apps/_shared/pagination.py`

```python
class PageRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    @computed_field
    def total_pages(self) -> int: ...
    @computed_field
    def has_next(self) -> bool: ...
    @computed_field
    def has_prev(self) -> bool: ...
```

Templates use `total_pages`, `has_next`, `has_prev`. Repositories return `Page[SomeRowDTO]`.

### `apps/_shared/pdf.py`

Thin wrapper around WeasyPrint — keeps the dependency contained.

```python
def render_pdf(html: str, *, base_url: str | None = None) -> bytes: ...
```

Used by 006 (PDF generation). For 001, ship the wrapper + a smoke test that renders `<html><body>hello</body></html>` to bytes.

### `templates/base.html` skeleton

Bootstrap 5 via vendored CSS (no CDN, per RT-04 and offline-friendliness). Blocks:

- `{% block title %}` — page `<title>`
- `{% block extra_head %}` — per-page CSS/meta
- `{% block nav %}` — overridable; default includes `components/nav.html`
- `{% block content %}` — main slot
- `{% block extra_scripts %}` — per-page JS

`components/alerts.html` renders `messages` from `django.contrib.messages` as Bootstrap alerts. `components/pagination.html` consumes a `Page` DTO.

Visual baseline follows the user-level `frontend-design` skill: institutional/academic look, no AI tells, WCAG 2.2 AA.

### `pyproject.toml` config

- `[tool.ruff]` — `target-version = "py312"`, `line-length = 100`, select `E,F,I,B,UP,SIM,N,C4,RUF`, ignore `E501` only inside docstrings.
- `[tool.mypy]` — `python_version = "3.12"`, `strict = true`, `plugins = ["pydantic.mypy"]`, exclude `migrations/`.
- `[tool.pytest.ini_options]` — `DJANGO_SETTINGS_MODULE = "config.settings.dev"`, `python_files = "test_*.py"`, `addopts = "-ra --strict-markers"`, markers (`integration`).
- `[tool.coverage.run]` — `source = ["apps", "config"]`, `omit = ["*/migrations/*", "*/tests/*"]`.

### `requirements.txt` (pinned versions chosen at implementation time)

Runtime: `Django>=5.0,<5.2`, `pydantic>=2.6,<3`, `psycopg[binary]>=3.1`, `PyJWT>=2.8`, `weasyprint>=62`, `python-dotenv>=1.0`, `requests>=2.31`.

Dev: `pytest`, `pytest-django`, `pytest-cov`, `model_bakery`, `freezegun`, `responses`, `ruff`, `mypy`, `django-stubs[compatible-mypy]`, `types-requests`.

### `.env.example`

```env
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=dev-only-change-me
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (prod)
DB_HOST=
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_PORT=5432

# JWT (filled in 002)
JWT_SECRET=
JWT_ALGORITHM=HS256
AUTH_PROVIDER_LOGIN_URL=
AUTH_PROVIDER_LOGOUT_URL=

# SIGA (filled in 002)
SIGA_BASE_URL=
SIGA_TIMEOUT_SECONDS=5

# SMTP (prod, filled in 007)
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=no-reply@uaz.edu.mx
```

### Root URL conf (`config/urls.py`)

```python
urlpatterns = [
    path("", RedirectView.as_view(url="/solicitudes/", permanent=False)),
    # filled by later initiatives:
    # path("auth/", include(("apps.usuarios.urls", "usuarios"))),
    # path("solicitudes/", include(("apps.solicitudes.urls", "solicitudes"))),
    # path("mentores/", include(("apps.mentores.urls", "mentores"))),
    # path("reportes/", include(("apps.reportes.urls", "reportes"))),
]
```

For 001, only the redirect + a `health/` endpoint that returns `200 OK` (used by container probes).

### Docker

Docker is set up at the **first step** and is the **only** runtime developers interact with. Hosts don't need Python, Postgres, WeasyPrint OS deps, or anything else installed — `make up` and `make test` work on a clean machine that has Docker.

This satisfies what `.claude/skills/django-patterns/e2e.md` actually protects against: **tests must not share state with the dev database**. That guarantee is enforced by *settings* (test DB is either in-process SQLite or the separate `postgres-test` service), not by where pytest runs from. pytest runs **inside the dev `web` container** under test settings — same container as `runserver`, isolated DB.

#### `Dockerfile` (multi-stage; shared by dev and any future prod image)

Stage 1 — `builder`:
- Base: `python:3.12-slim-bookworm`
- Install OS deps for WeasyPrint and Postgres client: `libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info fonts-dejavu fonts-liberation libpq-dev build-essential`
- Copy `requirements.txt` + `requirements-dev.txt`; `pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt` (dev image; prod stage installs runtime-only)

Stage 2 — `runtime`:
- Same base, only the runtime libs (no `-dev`, no `build-essential`)
- `COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages`
- `COPY --from=builder /usr/local/bin /usr/local/bin`
- `COPY . /app` ; `WORKDIR /app`
- Non-root user `app` (`useradd --create-home --shell /bin/bash app && chown -R app /app`); `USER app`
- `EXPOSE 8000`
- Default `CMD`: `gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3` — overridden in dev compose to use `runserver` for hot reload.

#### `docker-compose.dev.yml`

Three services on a `solicitudes-net` bridge network:

| Service | Image / Build | Ports (host:container) | Volumes |
|---|---|---|---|
| `web` | `build: { context: ., target: runtime }` | `8000:8000` | `.:/app` (live reload), `./media:/app/media` |
| `db` | `postgres:16` | `5432:5432` | `solicitudes_dev_data:/var/lib/postgresql/data` |
| `mailhog` | `mailhog/mailhog` | `1025:1025` (SMTP), `8025:8025` (UI) | — |

`web`:
- `command: python manage.py runserver 0.0.0.0:8000`
- `environment`: `DJANGO_SETTINGS_MODULE=config.settings.dev`, `DB_HOST=db`, `DB_PORT=5432`, `EMAIL_HOST=mailhog`, `EMAIL_PORT=1025`
- `depends_on: { db: { condition: service_healthy } }`

`db.healthcheck`: `pg_isready -U $POSTGRES_USER` every 2s, 5 retries.

The `.:/app` bind mount + `runserver` gives hot reload. Mailhog catches outgoing SMTP without leaking real emails (007 wires this in).

#### `docker-compose.test.yml` (Postgres only — no app container)

Per `e2e.md`, the test compose has **no `web` service**. The `web` that runs pytest is the dev one (already up via `make up`); the test compose just provides an isolated Postgres on the same network so the dev `web` can reach it by name.

```yaml
services:
  postgres-test:
    image: postgres:16
    environment:
      POSTGRES_DB: solicitudes_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    tmpfs: /var/lib/postgresql/data    # in-memory, ephemeral, fast
    networks: [solicitudes-net]
    # No ports: ... published — only reachable from inside the network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test -d solicitudes_test"]
      interval: 2s
      timeout: 5s
      retries: 5

networks:
  solicitudes-net:
    external: true                     # joins the dev compose's network
    name: solicitudes_solicitudes-net  # docker-compose default-naming; verify with `docker network ls`
```

The `external: true` declaration means this Compose file does not create the network — it joins the network that `docker-compose.dev.yml` already created when `make up` ran. The network name follows Compose's `<project>_<network>` convention; pin it explicitly to avoid surprises.

The `web` container in dev compose resolves `postgres-test:5432` via Docker's network DNS. No host port published, no `host.docker.internal` hack, no port collision with dev's `db` (5432).

Adding Redis here is deferred until 007's notification path actually exercises a worker (currently sync — not needed).

#### `config/settings/test_postgres.py`

```python
from .base import *   # noqa

DATABASES["default"] = {
    "ENGINE": "django.db.backends.postgresql",
    "HOST": "postgres-test",            # Docker DNS name on solicitudes-net
    "PORT": "5432",                     # in-network port (no host port published)
    "NAME": "solicitudes_test",
    "USER": "test",
    "PASSWORD": "test",
}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
```

Default test runs use SQLite (configured in `pytest.ini` / `pyproject.toml`). Pass `--ds=config.settings.test_postgres` (via `make e2e-postgres`) to swap to the `postgres-test` container.

#### `Makefile` (single entry point — every command goes through Docker)

```makefile
DC_DEV  := docker compose -f docker-compose.dev.yml
DC_TEST := docker compose -f docker-compose.test.yml
EXEC    := $(DC_DEV) exec -T web

.PHONY: help up down build logs shell migrate makemigrations \
        lint type test e2e e2e-postgres e2e-headed clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up:                ## Start dev stack (web + db + mailhog)
	$(DC_DEV) up -d --build

down:              ## Stop dev stack
	$(DC_DEV) down

build:             ## Rebuild the web image without starting the stack
	$(DC_DEV) build web

logs:              ## Tail web logs
	$(DC_DEV) logs -f web

shell:             ## Django shell inside web
	$(EXEC) python manage.py shell

migrate:           ## Apply migrations against dev DB
	$(EXEC) python manage.py migrate

makemigrations:    ## Generate migrations
	$(EXEC) python manage.py makemigrations

lint:              ## ruff inside web
	$(EXEC) ruff check .

type:              ## mypy inside web
	$(EXEC) mypy

test:              ## Unit + integration (inside web; SQLite, in-process live_server)
	$(EXEC) pytest

e2e:               ## All Tier 1 + Tier 2 tests (inside web; SQLite, in-process live_server)
	$(EXEC) pytest -m e2e

e2e-postgres:      ## Same as e2e but against ephemeral Postgres on the shared network
	$(DC_TEST) up -d --wait
	$(EXEC) pytest -m e2e --ds=config.settings.test_postgres; \
	rc=$$?; \
	$(DC_TEST) down -v; \
	exit $$rc

e2e-headed:        ## Browser tests with visible Chromium (debug; needs X server / VNC)
	$(EXEC) pytest -m e2e --headed --slowmo 200

clean:             ## Stop everything, remove volumes
	$(DC_DEV) down -v
	$(DC_TEST) down -v
```

Conventions:
- `EXEC := $(DC_DEV) exec -T web` is the canonical "run inside the dev `web` container" prefix. `-T` disables TTY allocation so the targets work in CI scripts.
- All Python tooling (`pytest`, `ruff`, `mypy`, `manage.py …`) goes through `$(EXEC)`. **The host never needs Python, Postgres, or any other dep.**
- `make up` must run before any `$(EXEC)` target. If `web` isn't running, Compose fails fast with a clear error ("service web is not running"). We deliberately don't auto-`up` from every target — explicit is better than rebuilding the image transparently.
- `e2e-postgres` brings up the test Compose, runs pytest **inside the dev `web` container** (which resolves `postgres-test` via the shared `solicitudes-net` network), then tears down with `down -v` even when pytest fails (the `;`-chain).
- `--wait` on `up -d` blocks until the test Postgres healthcheck passes — no race with pytest connecting before the DB is ready.

Editor integration: configure your IDE's Python interpreter as the `web` container (PyCharm: "Docker Compose" remote interpreter; VSCode: "Dev Containers" extension). Test discovery and debugger hooks work natively against the in-container interpreter.

#### `.dockerignore`

Mirrors `.gitignore` plus build excludes: `.git`, `tests-e2e/auth`, `test-results`, `playwright-report`, `media`, `*.sqlite3`, `.env`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`.

#### `.gitignore` additions (beyond a stock Django gitignore)

```
# Testing artifacts
test-results/
playwright-report/
playwright/.cache/
tests-e2e/auth/*.json

# Local
.env
media/
*.sqlite3
.docker-cache/
```

### Sequencing

1. Initialize `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `.dockerignore`, `.env.example`.
2. `django-admin startproject config .` (or hand-roll the structure to match `config/settings/{base,dev,prod,test_postgres}.py`).
3. Write `Dockerfile` (multi-stage). Verify `docker build .` succeeds and `docker run --rm <image> python -c "import weasyprint; weasyprint.HTML(string='<h1>x</h1>').write_pdf()"` produces non-empty bytes — proves WeasyPrint's system deps are present.
4. Write `docker-compose.dev.yml` (web + db + mailhog). `make up` brings everything up; `make migrate` runs migrations against Postgres in the `db` service.
5. Write `docker-compose.test.yml` (postgres-only, tmpfs, joins `solicitudes-net` as `external`) and `config/settings/test_postgres.py` (HOST=`postgres-test`, PORT=`5432`). Verify `make up` first, then `docker compose -f docker-compose.test.yml up -d --wait` boots, then `docker compose -f docker-compose.dev.yml exec web psql -h postgres-test -U test solicitudes_test -c "SELECT 1"` succeeds from inside `web`.
6. Write `Makefile` with the targets above. Verify `make help` lists all targets.
7. Create `apps/_shared/` package and `AppConfig` (registered in `INSTALLED_APPS` as `"apps._shared"`).
8. Implement `exceptions.py` + tests.
9. Implement `pagination.py` + tests.
10. Implement `auth.py` (JWT helpers) + tests with stubbed secret.
11. Implement `pdf.py` thin wrapper + smoke test (runs **inside the dev container** as well — proves the OS deps).
12. Implement `middleware/request_id.py` + `middleware/logging.py` + tests.
13. Implement `middleware/error_handler.py` + tests (covers AppError mapping, JSON vs HTML branch, redirect on 401).
14. Wire middleware into `MIDDLEWARE` in `base.py`.
15. Create `templates/base.html` + `components/*` + `_shared/error.html` + `_shared/404.html`.
16. Configure logging via `logging_config.dictConfig`; ensure `RequestIDFilter` injects `request_id` into every log record.
17. Add `health/` URL in `config/urls.py`.
18. Create empty `tests-e2e/README.md` pointing at `.claude/skills/django-patterns/e2e.md`. (Browser layout populated by initiatives that add Tier 2 flows.)
19. Run `make lint`, `make type`, `make test` — all green.
20. Run `make e2e-postgres` end-to-end: Compose up → tests run against real Postgres → Compose down -v.
21. Verify `make up` boots; `/health/` returns 200 from `http://localhost:8000/health/`; mailhog UI reachable at `http://localhost:8025/`.


## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)
- _None — initiative is pure project bootstrap; no user flows yet._

### Browser (Tier 2 — `pytest-playwright`)
- _None — no UI yet._

## Acceptance Criteria

### Django foundation
- [ ] `make shell` then `python manage.py check` passes with no warnings.
- [ ] `make test` green; `apps/_shared/` coverage ≥ 90% line.
- [ ] `make lint` and `make type` clean (zero errors).
- [ ] `make up` boots the stack; `/health/` returns 200 with `{"status":"ok","request_id":"…"}`.
- [ ] Raising any `AppError` subclass from a throwaway view returns the correct HTTP status, the correct user message, and logs `request_id`.
- [ ] An unknown exception in dev shows the Django debug page; in prod settings (`DJANGO_SETTINGS_MODULE=config.settings.prod`) renders `_shared/error.html` with `code=internal_error`.
- [ ] `templates/base.html` extends successfully; `components/alerts.html` renders one of each Bootstrap alert variant from a test view.
- [ ] WeasyPrint smoke test inside `web`: `render_pdf("<html><body>hola</body></html>")` returns non-empty bytes starting with `b"%PDF"`.
- [ ] Logs are JSON in prod settings, human-readable in dev; every record carries `request_id` when emitted inside a request.
- [ ] `.env.example` documents every variable read by `base.py`/`prod.py`.

### Docker — every command goes through it
- [ ] `docker build .` succeeds for both `--target builder` and `--target runtime`.
- [ ] `make help` lists all targets with their descriptions.
- [ ] `make up` brings the dev stack up cleanly; `web`, `db`, `mailhog` all healthy.
- [ ] `make migrate` runs successfully against the `db` Postgres container.
- [ ] `make test`, `make lint`, `make type` all run **inside `web`** (host has no Python installed; verify by uninstalling local Python or using a clean VM).
- [ ] `make e2e-postgres` brings up `docker-compose.test.yml`, runs pytest **inside `web`** against `postgres-test` on the shared `solicitudes-net` network, tears down with `down -v` even on failure (verified by `docker volume ls` showing no leftover test volume).
- [ ] `docker network ls` shows `solicitudes_solicitudes-net` after `make up`; `docker-compose.test.yml` joins it as `external`.
- [ ] Hot reload: editing a Python file under `apps/` triggers Django's autoreload inside `web`.
- [ ] Sending an email via `make shell` in `web` lands in Mailhog UI at `localhost:8025`.
- [ ] `.dockerignore` excludes secrets and build artifacts (image size for runtime stage ~ < 800 MB).
- [ ] Container runs as non-root user `app`.

## Open Questions

- **OQ-001-1** — Static file serving in prod: `whitenoise` vs nginx-served? Default to `whitenoise` for now; revisit when a deployment target is chosen.
- **OQ-001-2** — Should `RequestIDMiddleware` accept incoming `X-Request-ID` from upstream nginx, or always mint its own? Default: trust incoming if present and matches `[a-f0-9]{32}`, else mint.
