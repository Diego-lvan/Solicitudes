# 004 — Solicitud Lifecycle — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

### Models & migrations
- [ ] `models/solicitud.py`
- [ ] `models/historial_estado.py`
- [ ] `lifecycle/repositories/folio/FolioCounter` model
- [ ] Migration; verify indexes
- [ ] `tipo.plantilla_id` FK still nullable (resolved by 006)

### Lifecycle feature — schemas, exceptions, constants
- [ ] [P] `lifecycle/constants.py` (`Estado`, `TRANSITIONS`)
- [ ] [P] `lifecycle/exceptions.py` (SolicitudNotFound, InvalidStateTransition, FolioCollision)
- [ ] [P] `lifecycle/schemas.py` (SolicitudRow, SolicitudDetail, HistorialEntry, TransitionInput, SolicitudFilter)

### Lifecycle feature — repositories
- [ ] [P] `repositories/folio/{interface,implementation}.py` + tests (atomic allocation)
- [ ] [P] `repositories/solicitud/{interface,implementation}.py` + tests (filters, pagination, query count)
- [ ] [P] `repositories/historial/{interface,implementation}.py` + tests

### Lifecycle feature — services
- [ ] `services/folio_service/{interface,implementation}.py` + tests
- [ ] `services/lifecycle_service/{interface,implementation}.py` + tests (state-machine matrix + hypothesis property test)
- [ ] `lifecycle/dependencies.py`

### `_shared/audit.py`
- [ ] Implement `write(event, **fields)` + tests (asserts log line content)

### Intake feature
- [ ] [P] `intake/exceptions.py` (CreatorRoleNotAllowed, ComprobanteRequired)
- [ ] [P] `intake/schemas.py` (CreateSolicitudInput)
- [ ] [P] `intake/permissions.py`
- [ ] `intake/forms/intake_form.py` (wraps `build_django_form` + comprobante field)
- [ ] `intake/services/intake_service/{interface,implementation}.py` + tests
- [ ] [P] `intake/views/catalog.py` + tests
- [ ] [P] `intake/views/create.py` + tests
- [ ] [P] `intake/views/mis_solicitudes.py` + tests
- [ ] [P] `intake/views/detail.py` + tests
- [ ] [P] `intake/views/cancel.py` + tests
- [ ] `intake/urls.py`, `intake/dependencies.py`
- [ ] [P] Templates: catalog, create, mis_solicitudes, detail, confirm_cancel
- [ ] [P] Partials: _estado_badge, _solicitud_row, _historial, _valores_render

### Revision feature
- [ ] [P] `revision/schemas.py`
- [ ] [P] `revision/permissions.py`
- [ ] `revision/forms/transition_form.py`
- [ ] `revision/services/review_service/{interface,implementation}.py` + tests
- [ ] [P] `revision/views/queue.py` + tests
- [ ] [P] `revision/views/detail.py` + tests
- [ ] [P] `revision/views/take.py` + tests
- [ ] [P] `revision/views/finalize.py` + tests
- [ ] [P] `revision/views/cancel.py` + tests
- [ ] `revision/urls.py`, `revision/dependencies.py`
- [ ] [P] Templates: queue, detail, confirm_take, confirm_finalize, confirm_cancel

### Cross-app stubs (until 005/007/008 land)
- [ ] `NoOpNotificationService` in `intake/dependencies.py` and `revision/dependencies.py`
- [ ] `FalseMentorService` in `intake/dependencies.py`
- [ ] `archivo_service.store_for_solicitud` contract documented; intake view discards files with `WARNING` log until 005 lands

### URL wiring
- [ ] Mount intake + revision URLs in `config/urls.py`
- [ ] Verify reverse names: `solicitudes:intake:detail`, `solicitudes:revision:queue`, etc.

### End-to-end smoke
- [ ] Alumno + admin happy path: create → personal atender → finalizar
- [ ] Alumno cancels in CREADA: 200 + estado=CANCELADA
- [ ] Alumno tries to cancel in EN_PROCESO: 409 with `_shared/error.html`
- [ ] Two parallel creates → two distinct folios (FolioCounter atomic)
- [ ] Snapshot integrity: edit tipo's field labels → existing solicitud detail still shows old labels
- [ ] List view returns ≤ 3 SQL queries (use `django_assert_num_queries`)

### Quality gates
- [ ] `ruff` + `mypy` clean
- [ ] `pytest` green
- [ ] Coverage targets: lifecycle 95%, intake 95%, review 95%, repos 95%, views 80%
- [ ] Property test for state machine green (hypothesis)
- [ ] Grep audit: no `HttpRequest` in services/repos


### E2E
- [ ] Tier 1 (Client multi-step): Cross-feature: alumno submits intake → solicitud `CREADA` with folio + historial → personal atiende (`CREADA → EN_PROCESO`) → personal finaliza (`EN_PROCESO → FINALIZADA`). Asserts estados, `HistorialEstado` rows, and (after 007) the outbox.
- [ ] Tier 1 (Client multi-step): Cross-feature: alumno cancels their own solicitud while `CREADA` → estado=`CANCELADA`. Cancel attempt while `EN_PROCESO` → 409 with friendly error.
- [ ] Tier 2 (browser/Playwright): Golden path: alumno creates and submits a solicitud through the dynamic form (browser).
- [ ] Tier 2 (browser/Playwright): Golden path: personal takes a `CREADA` solicitud and finalizes it from the revision detail page (browser).

## Blockers

- **OQ-004-1, 004-2, 004-5** — service interface stubs from 005/007/008. The plan documents the contracts so 004 can ship behind a NoOp; final integration tests run when those initiatives land.

## Legend

- `[P]` = parallelizable with siblings in the same section
