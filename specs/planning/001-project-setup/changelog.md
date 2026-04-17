# 001-project-setup — Project Setup & Base — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25
- Initiative directory created (stub)
- Plan, status, and changelog files created as drafts pending `/brainstorm` + `/plan`
- Plan filled in: layout, settings split, `_shared/` infra (exceptions, middleware, auth helpers, pagination, pdf wrapper), base templates, quality gates. Status checklist populated. Open questions: static serving in prod, X-Request-ID trust policy.
- **Docker folded into 001** (per user direction): multi-stage `Dockerfile` with WeasyPrint OS deps baked in, `docker-compose.dev.yml` (web + db + mailhog, hot reload, healthchecks), `docker-compose.test.yml` (Postgres-only, tmpfs, no app container — daily test loop stays in-process via `pytest-django`'s `live_server`), `config/settings/test_postgres.py` for opt-in real-DB tests, `Makefile` targets (`up/down/test/e2e/e2e-postgres/e2e-headed/lint/type`). Followed `.claude/skills/django-patterns/e2e.md` rules: dev compose forbidden as test target; test compose has no `web` service; SQLite remains the default test backend.
- **Everything-through-Docker tightening:** Makefile now proxies every Python command (`pytest`, `ruff`, `mypy`, `manage.py …`) via `$(DC_DEV) exec -T web`. Host machines need only Docker — no Python install required. Test compose joins `solicitudes-net` as an `external` network; `postgres-test` is reachable from inside `web` via Docker DNS at `postgres-test:5432` (no host port published). `test_postgres.py` updated: `HOST=postgres-test`, `PORT=5432`. IDE remote-interpreter setup documented in `tests-e2e/README.md`. Acceptance criterion: `make test` passes on a host with no local Python.
