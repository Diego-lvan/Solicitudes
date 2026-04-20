# Sistema de Solicitudes — UAZ

Sistema de Solicitudes for the Universidad Autónoma de Zacatecas. Monolithic Django application with server-side templates (Bootstrap 5, no DRF).

For architectural rules and the SDD workflow this project follows, see [`CLAUDE.md`](./CLAUDE.md).

## Local development

The dev stack runs entirely in Docker — `nginx` (TLS termination on `:443`), `web` (Django), `db` (Postgres 16), and `mailhog` (SMTP capture on `:8025`).

A `Makefile` is provided for convenience but **every command also has a raw `docker compose` equivalent below**, so you don't need `make` installed.

### Prerequisites

- Docker Desktop (or Docker Engine 24+ with Compose v2)
- `mkcert` (recommended) or `openssl` for self-signed dev certs
- `git`

### One-time setup

```sh
# 1) Generate self-signed TLS certs for https://localhost
#    (mkcert is preferred — installs a trusted local CA so the browser doesn't warn)
mkdir -p certs
mkcert -install \
  && mkcert -cert-file certs/server.crt -key-file certs/server.key localhost 127.0.0.1
#    Fallback if you don't have mkcert (browser will warn — accept once):
# openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
#   -keyout certs/server.key -out certs/server.crt \
#   -subj "/CN=localhost" \
#   -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

# 2) Start the stack (builds the web image first time)
docker compose -f docker-compose.dev.yml up -d --build

# 3) Apply database migrations
docker compose -f docker-compose.dev.yml exec -T web python manage.py migrate

# 4) Seed dev data (5 users, 2 tipos with their fields)
docker compose -f docker-compose.dev.yml exec -T web python manage.py seed

# 5) Open the app
#    https://localhost/auth/dev-login → click any role to log in
```

### Daily commands

| Task | `make` | Raw `docker compose` |
|---|---|---|
| Start the stack | `make up` | `docker compose -f docker-compose.dev.yml up -d --build` |
| Stop the stack | `make down` | `docker compose -f docker-compose.dev.yml down` |
| Tail web logs | `make logs` | `docker compose -f docker-compose.dev.yml logs -f web` |
| Django shell | `make shell` | `docker compose -f docker-compose.dev.yml exec web python manage.py shell` |
| Apply migrations | `make migrate` | `docker compose -f docker-compose.dev.yml exec -T web python manage.py migrate` |
| Generate migrations | `make makemigrations` | `docker compose -f docker-compose.dev.yml exec -T web python manage.py makemigrations` |
| Seed dev data (idempotent) | `make seed` | `docker compose -f docker-compose.dev.yml exec -T web python manage.py seed` |
| Seed dev data (wipe + rebuild) | `make seed-fresh` | `docker compose -f docker-compose.dev.yml exec -T web python manage.py seed --fresh` |
| Lint (ruff) | `make lint` | `docker compose -f docker-compose.dev.yml exec -T web ruff check .` |
| Type-check (mypy strict) | `make type` | `docker compose -f docker-compose.dev.yml exec -T web mypy .` |
| Run tests | `make test` | `docker compose -f docker-compose.dev.yml exec -T web pytest` |
| Stop + remove volumes | `make clean` | `docker compose -f docker-compose.dev.yml down -v` |

### Seeded dev users

`python manage.py seed` (or `make seed`) creates one user per role, matching the matriculas the `/auth/dev-login` picker uses:

| Role | Matrícula | Email |
|---|---|---|
| `ALUMNO` | `ALUMNO_TEST` | `alumno.test@uaz.edu.mx` |
| `DOCENTE` | `DOCENTE_TEST` | `docente.test@uaz.edu.mx` |
| `CONTROL_ESCOLAR` | `CE_TEST` | `ce.test@uaz.edu.mx` |
| `RESPONSABLE_PROGRAMA` | `RP_TEST` | `rp.test@uaz.edu.mx` |
| `ADMIN` | `ADMIN_TEST` | `admin.test@uaz.edu.mx` |

Defaults are **idempotent** — re-running `seed` preserves any rows you've added by hand. Pass `--fresh` to wipe seeded rows and rebuild from scratch:

```sh
docker compose -f docker-compose.dev.yml exec -T web python manage.py seed --fresh
```

Run a single app's seeder only:

```sh
docker compose -f docker-compose.dev.yml exec -T web python manage.py seed --only usuarios
```

### Browser E2E (Playwright)

Browser tests need Chromium + system deps inside the web container; bootstrap once after `make build` (or after a fresh image pull):

```sh
docker compose -f docker-compose.dev.yml exec -T -u root web python -m playwright install-deps chromium
docker compose -f docker-compose.dev.yml exec -T web python -m playwright install chromium
```

Then run them:

```sh
# Tier 1 + Tier 2 (in-process server, SQLite)
docker compose -f docker-compose.dev.yml exec -T web pytest -m e2e

# With visible browser (slowed down for debugging)
docker compose -f docker-compose.dev.yml exec -T web pytest -m e2e --headed --slowmo 200
```

### URLs (after `make up` + `make seed`)

| URL | What |
|---|---|
| `https://localhost/auth/dev-login` | Dev login picker (DEBUG-only, removed by initiative 010) |
| `https://localhost/auth/me` | Current user profile |
| `https://localhost/solicitudes/admin/tipos/` | Catalog of solicitud types (admin only) |
| `https://localhost/solicitudes/admin/tipos/nuevo/` | Create a new tipo |
| `http://localhost:8025/` | Mailhog (captured outbound email) |

### Adding seed data for a new app

Drop a `seeders.py` at the app root with a `run(*, fresh: bool) -> None` function:

```python
# app/<your_app>/seeders.py
DEPENDS_ON: list[str] = ["usuarios"]  # optional — runs after these apps

def run(*, fresh: bool) -> None:
    if fresh:
        ...  # delete rows this seeder owns
    ...  # update_or_create your sample rows
```

The `manage.py seed` command auto-discovers it.
