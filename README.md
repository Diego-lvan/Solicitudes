# Sistema de Solicitudes — UAZ

Sistema de Solicitudes for the Universidad Autónoma de Zacatecas. Monolithic Django application with server-side templates (Bootstrap 5, no DRF).

For architectural rules and the SDD workflow this project follows, see [`CLAUDE.md`](./CLAUDE.md).

## Local development

The dev stack runs entirely in Docker — `nginx` (TLS termination on `:443`), `web` (Django), `db` (Postgres 16), and `mailhog` (SMTP capture on `:8025`).

A `Makefile` is provided for convenience but **every command also has a raw `docker compose` equivalent below**, so you don't need `make` installed.

### Prerequisites

- Docker Desktop (or Docker Engine 24+ with Compose v2)
- `git`

### One-time setup

Dev TLS certs for `localhost` are already checked in — no need to generate them.

```sh
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml exec -T web python manage.py migrate
docker compose -f docker-compose.dev.yml exec -T web python manage.py seed
```

Then open `https://localhost/auth/dev-login` and click any role to log in.

> The browser may warn about the self-signed cert — accept it once.

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

## Manual de usuario (capturas)

Capturas tomadas contra el stack local con datos sembrados (`make up && make seed`). Se reproducen recargando el sistema y entrando con los usuarios de `/auth/dev-login`.

### 1. Acceso

#### 1.1 Login de desarrollo

Selector de usuarios disponible solo con `DEBUG=True`. Permite entrar con un rol predefinido (columna izquierda) o como un usuario ya existente (columna derecha).

![Login de desarrollo](docs/screenshots/01-dev-login.png)

#### 1.2 Mi perfil

Vista que muestra los datos provenientes del proveedor de identidad (matrícula, correo, rol, programa, semestre). Es de solo lectura: cualquier corrección se hace en SIGA.

![Mi perfil](docs/screenshots/02-alumno-perfil.png)

### 2. Flujo del alumno

#### 2.1 Catálogo — Crear solicitud

Lista los tipos de solicitud que el alumno puede iniciar. Cada tarjeta indica si el trámite requiere pago.

![Crear solicitud — catálogo](docs/screenshots/03-alumno-crear-solicitud.png)

#### 2.2 Mis solicitudes

Histórico personal del alumno con folio, tipo, fecha y estado. Se puede filtrar por folio, estado o rango de fechas.

![Mis solicitudes](docs/screenshots/04-alumno-mis-solicitudes.png)

#### 2.3 Formulario dinámico

Cada tipo de solicitud renderiza un formulario distinto, definido por el administrador. Soporta texto, selección y archivos adjuntos.

![Formulario dinámico de solicitud](docs/screenshots/05-alumno-formulario-dinamico.png)

#### 2.4 Detalle de la solicitud

Muestra los datos enviados, los archivos adjuntos y el historial completo de cambios de estado. Cuando la solicitud está finalizada y el tipo tiene plantilla, aparece el botón **Descargar PDF**.

![Detalle de solicitud](docs/screenshots/06-alumno-detalle-solicitud.png)

### 3. Flujo de Control Escolar / Responsable de Programa

#### 3.1 Cola de revisión

Lista de solicitudes pendientes para el rol responsable. Filtros por folio, solicitante y estado.

![Cola de revisión](docs/screenshots/07-ce-cola-revision.png)

#### 3.2 Detalle de revisión

Vista del personal con datos del solicitante, archivos, historial y acciones para *atender*, *finalizar* o *cancelar* la solicitud. Permite generar el PDF al finalizar.

![Detalle de revisión](docs/screenshots/08-ce-detalle-revision.png)

### 4. Administración del catálogo

#### 4.1 Tipos de solicitud

CRUD del catálogo. Cada tipo define el rol que la atiende, qué roles pueden crearla, si requiere pago, y la plantilla de PDF asociada.

![Tipos de solicitud](docs/screenshots/09-admin-tipos-list.png)

#### 4.2 Nuevo tipo de solicitud

Editor con vista previa en vivo del formulario que verá el solicitante. Los campos se agregan dinámicamente.

![Nuevo tipo de solicitud](docs/screenshots/10-admin-tipos-nuevo.png)

#### 4.3 Plantillas de PDF

Plantillas HTML/CSS que WeasyPrint usa para producir el PDF final. Se versionan y pueden activarse o desactivarse.

![Plantillas de PDF — listado](docs/screenshots/11-admin-plantillas-list.png)

#### 4.4 Nueva plantilla

Formulario para capturar HTML, CSS y descripción. La sección inferior lista las variables disponibles (`{{ solicitante.nombre }}`, `{{ solicitud.folio }}`, etc.).

![Nueva plantilla de PDF](docs/screenshots/12-admin-plantilla-nueva.png)

### 5. Mentores

#### 5.1 Catálogo de mentores

Listado con filtro por estado activo. Permite seleccionar varios y desactivarlos en lote.

![Catálogo de mentores](docs/screenshots/13-admin-mentores-list.png)

#### 5.2 Agregar mentor

Alta manual de un mentor por matrícula.

![Agregar mentor](docs/screenshots/14-admin-mentor-agregar.png)

#### 5.3 Importar CSV

Importación masiva con encabezado `matricula`. El sistema reporta filas insertadas, reactivadas, omitidas y rechazadas.

![Importar mentores (CSV)](docs/screenshots/15-admin-mentores-importar.png)

### 6. Directorio de usuarios

#### 6.1 Listado

Vista de solo lectura del directorio (los datos los administra SIGA / el proveedor de identidad). Filtros por rol y búsqueda libre.

![Directorio de usuarios](docs/screenshots/16-admin-usuarios-directorio.png)

#### 6.2 Detalle de usuario

Información de identidad, datos académicos, situación de mentoría y auditoría.

![Detalle de usuario](docs/screenshots/17-admin-usuario-detalle.png)

### 7. Reportes

#### 7.1 Dashboard

Métricas agregadas con filtros por estado, tipo, responsable y rango de fechas. Botones para exportar a CSV o PDF.

![Reportes — Dashboard](docs/screenshots/18-admin-reportes-dashboard.png)

#### 7.2 Lista detallada

Vista tabular de las solicitudes que pasan los filtros del dashboard, exportable a CSV.

![Reportes — Lista](docs/screenshots/19-admin-reportes-lista.png)

### 8. Notificaciones (Mailhog)

Mailhog captura todos los correos salientes en desarrollo. Útil para inspeccionar las notificaciones que el sistema dispara al crear/transitar solicitudes.

#### 8.1 Bandeja de Mailhog

![Bandeja de Mailhog](docs/screenshots/20-mailhog-bandeja.png)

#### 8.2 Detalle de un correo

![Correo de confirmación](docs/screenshots/21-mailhog-correo-detalle.png)

---

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
