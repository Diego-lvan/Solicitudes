# 004 — Solicitud Lifecycle — Status

**Status:** Done
**Last updated:** 2026-04-25

## Checklist

### Models & migrations
- [x] `models/solicitud.py`
- [x] `models/historial_estado.py`
- [x] `lifecycle/repositories/folio/FolioCounter` model (lives in `solicitudes/models/folio_counter.py` per architect rules — models are app-level)
- [x] Migration; verify indexes (`0002_foliocounter_solicitud_historialestado_…`)
- [x] `tipo.plantilla_id` FK still nullable (resolved by 006) — verified in 0001_initial; no new migration needed

### Lifecycle feature — schemas, exceptions, constants
- [x] [P] `lifecycle/constants.py` (`Estado`, `TRANSITIONS`)
- [x] [P] `lifecycle/exceptions.py` (SolicitudNotFound, InvalidStateTransition, FolioCollision)
- [x] [P] `lifecycle/schemas.py` (SolicitudRow, SolicitudDetail, HistorialEntry, TransitionInput, SolicitudFilter)

### Lifecycle feature — repositories
- [x] [P] `repositories/folio/{interface,implementation}.py` + tests (atomic allocation)
- [x] [P] `repositories/solicitud/{interface,implementation}.py` + tests (filters, pagination, query count ≤ 3)
- [x] [P] `repositories/historial/{interface,implementation}.py` + tests

### Lifecycle feature — services
- [x] `services/folio_service/{interface,implementation}.py` + tests
- [x] `services/lifecycle_service/{interface,implementation}.py` + tests (state-machine matrix + hypothesis property test)
- [x] `lifecycle/dependencies.py`
- [x] `lifecycle/notification_port.py` — outbound port owned by lifecycle (ABC + `NoOpNotificationService` until 007)

### `_shared/audit.py`
- [x] Implement `write(event, **fields)` + tests (asserts log line content)

### Intake feature
- [x] [P] `intake/exceptions.py` (CreatorRoleNotAllowed, ComprobanteRequired)
- [x] [P] `intake/schemas.py` (CreateSolicitudInput)
- [x] [P] `intake/permissions.py` (CreatorRequiredMixin)
- [x] [P] `intake/mentor_port.py` (MentorService ABC + FalseMentorService stub until 008)
- [x] `intake/forms/intake_form.py` (wraps `build_django_form` + comprobante FileField)
- [x] `intake/services/intake_service/{interface,implementation}.py` + tests (covered via Tier-1 view + Tier-1 e2e tests)
- [x] [P] `intake/views/catalog.py` + tests
- [x] [P] `intake/views/create.py` + tests
- [x] [P] `intake/views/mis_solicitudes.py` + tests
- [x] [P] `intake/views/detail.py` + tests
- [x] [P] `intake/views/cancel.py` + tests
- [x] `intake/urls.py`, `intake/dependencies.py`
- [x] [P] Templates: catalog, create, mis_solicitudes, detail (no separate confirm_cancel — inline JS confirm)
- [x] [P] Partials: _estado_badge, _solicitud_row, _historial, _valores_render

### Revision feature
- [x] [P] `revision/permissions.py` (ReviewerRequiredMixin — covers DOCENTE, CE, RP, ADMIN)
- [x] `revision/forms/transition_form.py`
- [x] `revision/services/review_service/{interface,implementation}.py` + tests (covered via Tier-1 view tests)
- [x] [P] `revision/views/queue.py` + tests
- [x] [P] `revision/views/detail.py` + tests
- [x] [P] `revision/views/take.py` + tests
- [x] [P] `revision/views/finalize.py` + tests
- [x] [P] `revision/views/cancel.py` + tests
- [x] `revision/urls.py`, `revision/dependencies.py`
- [x] [P] Templates: queue, detail (transition controls inline; no separate confirm pages — JS confirm)

### Cross-app stubs (until 005/007/008 land)
- [x] `NoOpNotificationService` in `solicitudes.lifecycle.notification_port`, wired by `lifecycle/dependencies.py`
- [x] `FalseMentorService` in `solicitudes.intake.mentor_port`, wired by `intake/dependencies.py`
- [x] `archivo_service.store_for_solicitud` contract documented (in plan); intake view discards files with `WARNING` log until 005 lands

### URL wiring
- [x] Mount intake + revision URLs via `solicitudes.urls` (under namespace `solicitudes`); routes:
  - `/solicitudes/` → intake (`solicitudes:intake:*`)
  - `/solicitudes/revision/` → revision (`solicitudes:revision:*`) — note path differs from plan's `/revision/` to keep namespace consistent
- [x] Verify reverse names: `solicitudes:intake:detail`, `solicitudes:revision:queue`, etc.

### End-to-end smoke
- [x] Alumno + admin happy path: create → personal atender → finalizar (Tier-1 client + Tier-2 Playwright)
- [x] Alumno cancels in CREADA: 200 + estado=CANCELADA (Tier-1)
- [x] Alumno tries to cancel in EN_PROCESO: friendly redirect + flash, estado unchanged (Tier-1)
- [x] Two parallel creates → two distinct folios (Tier-1)
- [x] Snapshot integrity: edit tipo's field labels → existing solicitud detail still shows old labels (Tier-1)
- [x] List view returns ≤ 3 SQL queries (`django_assert_num_queries`)

### Quality gates
- [x] `ruff` clean (auto-fixed batch + manual SIM103/RUF005)
- [x] `mypy` clean (introduced `_shared/request_actor.py` so views can read `UserDTO` without `# type: ignore`)
- [x] `pytest` green (286 tests; 1 pre-existing tier-2 flake in `tests-e2e/test_tipos_golden_path.py` unrelated to 004)
- [x] Property test for state machine green (hypothesis)
- [x] Grep audit: no `HttpRequest`/`request.POST`/`request.user` in services or repositories

### E2E
- [x] Tier 1 (Client multi-step): alumno submits intake → solicitud `CREADA` with folio + historial → personal atiende (`CREADA → EN_PROCESO`) → personal finaliza (`EN_PROCESO → FINALIZADA`). Asserts estados and `HistorialEstado` rows. (Outbox assertion deferred to 007.)
- [x] Tier 1 (Client multi-step): alumno cancels their own solicitud while `CREADA` → estado=`CANCELADA`. Cancel attempt while `EN_PROCESO` → friendly redirect + flash, estado unchanged.
- [x] Tier 2 (browser/Playwright): alumno creates and submits a solicitud through the dynamic form (browser).
- [x] Tier 2 (browser/Playwright): personal takes a `CREADA` solicitud and finalizes it from the revision detail page (browser).
- [x] Visual verification: desktop (1280x900) + mobile (320x800) screenshots saved under `/tmp/screenshots-004/` and reviewed against frontend-design rules.

## Blockers

- **OQ-004-1, 004-2, 004-5** — service interface stubs from 005/007/008. The plan documents the contracts so 004 ships behind a NoOp; final integration tests run when those initiatives land.

## Legend

- `[P]` = parallelizable with siblings in the same section
