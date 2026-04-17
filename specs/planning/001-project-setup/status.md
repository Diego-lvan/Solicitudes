# 001 — Project Setup & Base — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

### Bootstrap
- [ ] Create `pyproject.toml` (ruff + mypy + pytest config)
- [ ] Create `requirements.txt` and `requirements-dev.txt` with pinned versions
- [ ] Create `.gitignore`, `.dockerignore`, `.env.example`, `manage.py`
- [ ] `django-admin startproject` (or hand-roll) → `config/{settings,urls,wsgi,asgi}.py`

### Docker — every command goes through it (host has no Python)
- [ ] [P] `Dockerfile` (multi-stage builder + runtime; WeasyPrint + libpq deps; non-root user `app`)
- [ ] [P] `docker-compose.dev.yml` (nginx-dev + web + db + mailhog, healthchecks, hot-reload bind mount, `solicitudes-net` network; only `nginx-dev` and `db` publish host ports)
- [ ] [P] `docker-compose.test.yml` (`postgres-test` only, tmpfs, joins `solicitudes-net` as `external`; **no app container**, **no host port published**)
- [ ] `Makefile` with `EXEC := $(DC_DEV) exec -T web` and targets `up/down/build/logs/shell/migrate/makemigrations/lint/type/test/e2e/e2e-postgres/e2e-headed/clean/help/certs` — every Python command goes through `$(EXEC)`
- [ ] Verify: `docker build .` succeeds for `builder` and `runtime` targets
- [ ] Verify: WeasyPrint smoke runs **inside the `web` container**
- [ ] Verify: `make test` and `make e2e` run pytest **inside `web`** against in-process `live_server` + SQLite; pass on a host with no Python installed
- [ ] Verify: `make e2e-postgres` brings up test Compose, runs pytest **inside `web`** against `postgres-test:5432` on the shared network, tears down with `down -v` even when pytest fails (no leftover volume per `docker volume ls`)
- [ ] Verify: shared network — `docker network ls` shows `solicitudes_solicitudes-net` after `make up`; test compose's `external: true` resolves to it
- [ ] Verify: container runs as non-root user `app`; runtime image < 800 MB
- [ ] Document IDE remote-interpreter setup in `tests-e2e/README.md` (PyCharm / VSCode pointing at `web` container)

### Nginx & TLS — every browser request goes through nginx, even in dev
- [ ] [P] `nginx/dev/nginx.conf` — TLSv1.2+1.3, 80→443 redirect, `/` → `web:8000`, `/__mailhog/` → `mailhog:8025`, X-Forwarded-* headers, X-Request-ID
- [ ] [P] `nginx/prod/nginx.conf` — TLSv1.3 only, HSTS, CSP, server_tokens off, rate limiting on `/auth/*`, no Mailhog vhost, hardened ciphers
- [ ] Add `nginx-dev` service to `docker-compose.dev.yml` (`depends_on: [web, mailhog]`, mounts config + certs, publishes 443 + 80)
- [ ] Remove host port publishing from `web` and `mailhog` in dev compose
- [ ] `make certs` target — uses mkcert if installed, openssl fallback
- [ ] Add `certs/`, `*.crt`, `*.key`, `*.pem` to `.gitignore`
- [ ] Set `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` in dev + prod settings
- [ ] Verify: `make up` then `https://localhost/health/` returns 200 with valid TLS handshake
- [ ] Verify: `https://localhost/__mailhog/` shows Mailhog UI
- [ ] Verify: `http://localhost/health/` 301-redirects to `https://localhost/health/`
- [ ] Verify: `X-Request-ID` from nginx appears in Django logs for the same request
- [ ] Verify: `request.is_secure()` returns True inside Django views behind nginx

### Settings split
- [ ] [P] `config/settings/base.py`
- [ ] [P] `config/settings/dev.py`
- [ ] [P] `config/settings/prod.py`
- [ ] [P] `config/settings/test_postgres.py` (opt-in for `--ds=config.settings.test_postgres`)
- [ ] Verify `python manage.py check --settings=config.settings.dev` passes
- [ ] Verify `python manage.py check --settings=config.settings.prod` passes (with prod env vars set)
- [ ] Verify `python manage.py check --settings=config.settings.test_postgres` passes when `docker-compose.test.yml` is up

### `_shared/` infrastructure
- [ ] Create `_shared/__init__.py` + `apps.py` (`AppConfig`)
- [ ] [P] `_shared/exceptions.py` (AppError + 6 sentinels)
- [ ] [P] `_shared/pagination.py` (`PageRequest`, `Page[T]`)
- [ ] [P] `_shared/auth.py` (JWT decode helpers)
- [ ] [P] `_shared/pdf.py` (WeasyPrint wrapper)
- [ ] [P] `_shared/logging_config.py` (dictConfig builder + `RequestIDFilter`)

### Middleware
- [ ] [P] `_shared/middleware/request_id.py` + tests
- [ ] [P] `_shared/middleware/logging.py` + tests
- [ ] `_shared/middleware/error_handler.py` + tests (depends on exceptions.py)
- [ ] Wire all three into `MIDDLEWARE` in `config/settings/base.py`

### Templates & static
- [ ] Vendor Bootstrap 5 CSS/JS into `static/vendor/`
- [ ] [P] `templates/base.html`
- [ ] [P] `templates/components/{nav,alerts,pagination,empty_state}.html`
- [ ] [P] `templates/_shared/{error,404}.html`
- [ ] `static/css/app.css` shell
- [ ] Frontend baseline review against `frontend-design` skill

### Plumbing
- [ ] Add `health/` URL returning `{"status":"ok","request_id":...}`
- [ ] Root redirect `/` → `/solicitudes/` placeholder
- [ ] Configure `LOGGING` from `logging_config.dictConfig`
- [ ] Create `tests-e2e/README.md` pointing at `.claude/skills/django-patterns/e2e.md` (skeleton only; flows added by later initiatives)

### Tests (_shared coverage ≥ 90%)
- [ ] [P] `test_exceptions.py` — every subclass carries the right `code`, `http_status`, `user_message`
- [ ] [P] `test_pagination.py` — `Page` computed fields, edge cases (empty, single page)
- [ ] [P] `test_auth.py` — valid token decodes, expired raises `AuthenticationRequired`, invalid raises same
- [ ] [P] `test_pdf.py` — smoke test renders bytes starting with `%PDF`
- [ ] [P] `test_middleware_request_id.py` — mints uuid, echoes incoming, attaches to log records
- [ ] [P] `test_middleware_error_handler.py` — AppError → HTML, AppError + `HX-Request` → JSON, 401 → redirect, unhandled re-raised in dev

### Quality gates
- [ ] `make lint` clean (`ruff check .`)
- [ ] `make type` clean (`mypy` strict)
- [ ] `make test` green
- [ ] `make e2e-postgres` green (Compose up → tests pass against real Postgres → `down -v` succeeds)
- [ ] `python manage.py runserver` boots locally without errors
- [ ] `make up` boots dev stack without errors

## Blockers

None.

## Legend

- `[P]` = parallelizable with siblings in the same section
