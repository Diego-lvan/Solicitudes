# tests-e2e/

End-to-end browser tests live here, populated by initiatives that introduce
new user-facing flows.

The canonical rules for the testing stack — Tier 1 (in-process `Client`)
vs. Tier 2 (`pytest-playwright` + `live_server`), the `docker-compose.test.yml`
shape, the opt-in `config.settings.test_postgres`, and the Make targets —
live in `.claude/skills/django-patterns/e2e.md`. Read that before adding
flows here.

## IDE remote interpreter

All Python runs **inside the `web` container**. Configure your IDE to use
that interpreter so test discovery, debugging, and type-checking work:

- **PyCharm** — Settings → Project → Python Interpreter → Add Interpreter →
  *On Docker Compose* → Configuration files: `docker-compose.dev.yml`,
  Service: `web`.
- **VSCode** — Install the "Dev Containers" extension; reopen the workspace
  in the `web` container; the in-container Python interpreter is auto-picked.
