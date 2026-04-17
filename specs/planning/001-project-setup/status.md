# 001 — Project Setup & Base — Status

**Status:** Done
**Last updated:** 2026-04-25

## Checklist

### Bootstrap
- [x] Create `pyproject.toml` (ruff + mypy + pytest config)
- [x] Create `requirements.txt` and `requirements-dev.txt` with pinned versions
- [x] Create `.gitignore`, `.dockerignore`, `.env.example`, `manage.py`
- [x] `django-admin startproject` (or hand-roll) → `config/{settings,urls,wsgi,asgi}.py`

### Docker — every command goes through it (host has no Python)
- [x] [P] `Dockerfile` (multi-stage builder + runtime; WeasyPrint + libpq deps; non-root user `app`)
- [x] [P] `docker-compose.dev.yml` (nginx-dev + web + db + mailhog, healthchecks, hot-reload bind mount, `solicitudes-net` network; only `nginx-dev` and `db` publish host ports)
- [x] [P] `docker-compose.test.yml` (`postgres-test` only, tmpfs, joins `solicitudes-net` as `external`; **no app container**, **no host port published**)
- [x] `Makefile` with `EXEC := $(DC_DEV) exec -T web` and targets `up/down/build/logs/shell/migrate/makemigrations/lint/type/test/e2e/e2e-postgres/e2e-headed/clean/help/certs` — every Python command goes through `$(EXEC)`
- [x] Verify: `docker build .` succeeds for `builder` and `runtime` targets
- [x] Verify: WeasyPrint smoke runs **inside the `web` container** (returns `b"%PDF"` bytes; 2.2 KB output)
- [x] Verify: `make test` and `make e2e` run pytest **inside `web`** against in-process `live_server` + SQLite; pass on a host with no Python installed
- [x] Verify: `make e2e-postgres` brings up test Compose, runs pytest **inside `web`** against `postgres-test:5432` on the shared network, tears down with `down -v` even when pytest fails (no leftover volume per `docker volume ls`)
- [x] Verify: shared network — `docker network ls` shows `solicitudes_solicitudes-net` after `make up`; test compose's `external: true` resolves to it
- [x] Verify: container runs as non-root user `app`; runtime image < 800 MB (731 MB measured)
- [x] Document IDE remote-interpreter setup in `tests-e2e/README.md` (PyCharm / VSCode pointing at `web` container)

### Nginx & TLS — every browser request goes through nginx, even in dev
- [x] [P] `nginx/dev/nginx.conf` — TLSv1.2+1.3, 80→443 redirect, `/` → `web:8000`, `/__mailhog/` → `mailhog:8025`, X-Forwarded-* headers, X-Request-ID
- [x] [P] `nginx/prod/nginx.conf` — TLSv1.3 only, HSTS, CSP, server_tokens off, rate limiting on `/auth/*`, no Mailhog vhost, hardened ciphers
- [x] Add `nginx-dev` service to `docker-compose.dev.yml` (`depends_on: [web, mailhog]`, mounts config + certs, publishes 443 + 80)
- [x] Remove host port publishing from `web` and `mailhog` in dev compose
- [x] `make certs` target — uses mkcert if installed, openssl fallback
- [x] Add `certs/`, `*.crt`, `*.key`, `*.pem` to `.gitignore`
- [x] Set `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` in dev + prod settings
- [x] Verify: `make up` then `https://localhost/health/` returns 200 with valid TLS handshake
- [x] Verify: `https://localhost/__mailhog/` shows Mailhog UI
- [x] Verify: `http://localhost/health/` 301-redirects to `https://localhost/health/`
- [x] Verify: `X-Request-ID` from nginx appears in Django logs for the same request
- [x] Verify: `request.is_secure()` returns True inside Django views behind nginx (`SECURE_PROXY_SSL_HEADER` configured)

### Settings split
- [x] [P] `config/settings/base.py`
- [x] [P] `config/settings/dev.py`
- [x] [P] `config/settings/prod.py`
- [x] [P] `config/settings/test_postgres.py` (opt-in for `--ds=config.settings.test_postgres`)
- [x] Verify `python manage.py check --settings=config.settings.dev` passes
- [ ] Verify `python manage.py check --settings=config.settings.prod` passes (with prod env vars set)  ← deferred: requires real prod env
- [x] Verify `python manage.py check --settings=config.settings.test_postgres` passes when `docker-compose.test.yml` is up

### `_shared/` infrastructure
- [x] Create `_shared/__init__.py` + `apps.py` (`AppConfig`)
- [x] [P] `_shared/exceptions.py` (AppError + 6 sentinels)
- [x] [P] `_shared/pagination.py` (`PageRequest`, `Page[T]`)
- [x] [P] `_shared/auth.py` (JWT decode helpers)
- [x] [P] `_shared/pdf.py` (WeasyPrint wrapper)
- [x] [P] `_shared/logging_config.py` (dictConfig builder + `RequestIDFilter`)

### Middleware
- [x] [P] `_shared/middleware/request_id.py` + tests
- [x] [P] `_shared/middleware/logging.py` + tests
- [x] `_shared/middleware/error_handler.py` + tests (depends on exceptions.py)
- [x] Wire all three into `MIDDLEWARE` in `config/settings/base.py`

### Templates & static
- [ ] Vendor Bootstrap 5 CSS/JS into `static/vendor/`  ← stubs in place; real assets to be downloaded before shipping (see `static/vendor/bootstrap/README.md`)
- [x] [P] `templates/base.html`
- [x] [P] `templates/components/{nav,alerts,pagination,empty_state}.html`
- [x] [P] `templates/_shared/{error,404}.html`
- [x] `static/css/app.css` shell
- [ ] Frontend baseline review against `frontend-design` skill  ← deferred to first feature initiative that adds real UI

### Plumbing
- [x] Add `health/` URL returning `{"status":"ok","request_id":...}`
- [x] Root redirect `/` → `/solicitudes/` placeholder
- [x] Configure `LOGGING` from `logging_config.dictConfig`
- [x] Create `tests-e2e/README.md` pointing at `.claude/skills/django-patterns/e2e.md` (skeleton only; flows added by later initiatives)

### Tests (_shared coverage ≥ 90%)
- [x] [P] `test_exceptions.py` — every subclass carries the right `code`, `http_status`, `user_message`
- [x] [P] `test_pagination.py` — `Page` computed fields, edge cases (empty, single page)
- [x] [P] `test_auth.py` — valid token decodes, expired raises `AuthenticationRequired`, invalid raises same
- [x] [P] `test_pdf.py` — smoke test renders bytes starting with `%PDF`
- [x] [P] `test_middleware_request_id.py` — mints uuid, echoes incoming, attaches to log records
- [x] [P] `test_middleware_error_handler.py` — AppError → HTML, AppError + `HX-Request` → JSON, 401 → redirect, unhandled re-raised in dev
- [x] `test_middleware_logging.py` — structured `request.end` record with method/path/status/duration

### Quality gates
- [x] `make lint` clean (`ruff check .`)
- [x] `make type` clean (`mypy` strict; 30 source files, 0 errors)
- [x] `make test` green (35 passed; `_shared` coverage 98%)
- [x] `make e2e-postgres` green (Compose up → tests pass against real Postgres → `down -v` succeeds, no leftover volume)
- [x] `python manage.py runserver` boots locally without errors (verified via dev compose)
- [x] `make up` boots dev stack without errors

## Blockers

None.

## Deferred (follow-up work, not in this initiative's critical path)

- **Bootstrap 5 vendor assets** — directory wired through `{% static %}`; real minified bundles to be dropped in before first UI initiative ships.
- **`prod.py` `manage.py check`** — needs a real prod env (SECRET_KEY, DB_*, EMAIL_HOST, ALLOWED_HOSTS) which isn't part of bootstrap.
- **Frontend baseline review** — meaningful only once a real UI lands; the skeleton templates here are intentionally minimal.

## Legend

- `[P]` = parallelizable with siblings in the same section
