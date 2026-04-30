# Flow — Solicitud Lifecycle

> **Status:** v1 (initiative 004). Cross-feature integrations land later: 005 wires file storage at intake, 006 plugs PDF generation at finalization, 007 replaces `NoOpNotificationService`, 008 replaces `FalseMentorService`. The skeleton documented here is stable.
>
> **Owners:** `solicitudes` app — features `intake`, `lifecycle`, `revision`.

This flow traces the canonical end-to-end path of a solicitud: alumno files it, personal in the responsible role takes it, personal finalizes it. Cancellation paths fork off at multiple points and are documented in their own section below.

## Trigger

A solicitante (alumno or docente) opens the intake catalog (`/solicitudes/`) and clicks **Iniciar solicitud** on a tipo their role can file.

## Sequence (happy path)

```
┌─────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌────────┐
│Alumno   │  │ /solicitudes/    │  │ IntakeService    │  │ TipoService      │  │ FolioService     │  │ LifecycleService │  │Personal│
│browser  │  │  crear/<slug>/   │  │                  │  │                  │  │                  │  │                  │  │browser │
└────┬────┘  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  └────┬───┘
     │ GET            │                     │                     │                     │                     │                  │
     │───────────────▶│                     │                     │                     │                     │                  │
     │                │ get_intake_form()   │                     │                     │                     │                  │
     │                │────────────────────▶│ get_for_creator     │                     │                     │                  │
     │                │                     │────────────────────▶│                     │                     │                  │
     │                │                     │ snapshot()          │                     │                     │                  │
     │                │                     │────────────────────▶│ FormSnapshot        │                     │                  │
     │                │                     │ build_intake_form() │                     │                     │                  │
     │                │ DynamicTipoForm     │                     │                     │                     │                  │
     │ render form    │◀────────────────────│                     │                     │                     │                  │
     │◀───────────────│                     │                     │                     │                     │                  │
     │                │                     │                     │                     │                     │                  │
     │ POST data      │                     │                     │                     │                     │                  │
     │───────────────▶│                     │                     │                     │                     │                  │
     │                │ form.is_valid()     │                     │                     │                     │                  │
     │                │ create(input_dto)   │                     │                     │                     │                  │
     │                │────────────────────▶│ get_for_admin       │                     │                     │                  │
     │                │                     │────────────────────▶│                     │                     │                  │
     │                │                     │ snapshot()  ←── captured AT submit time   │                     │                  │
     │                │                     │────────────────────▶│ FormSnapshot        │                     │                  │
     │                │                     │ ┌─ atomic ────────────────────┐           │                     │                  │
     │                │                     │ │ next_folio(year)            │           │                     │                  │
     │                │                     │ │────────────────────────────▶│ "SOL-…"   │                     │                  │
     │                │                     │ │ solicitud_repo.create(…)               │                     │                  │
     │                │                     │ │ historial_repo.append(prev=None,        │                     │                  │
     │                │                     │ │                       next=CREADA, …)   │                     │                  │
     │                │                     │ └─────────────────────────────┘           │                     │                  │
     │                │                     │ notify_creation(folio, responsible_role)  │                     │                  │
     │                │                     │ audit.write("solicitud.creada", …)        │                     │                  │
     │                │ SolicitudDetail     │                     │                     │                     │                  │
     │                │◀────────────────────│                     │                     │                     │                  │
     │ 302 to detail  │                     │                     │                     │                     │                  │
     │◀───────────────│                     │                     │                     │                     │                  │
     │ flash "Solicitud creada con folio SOL-…"                                                                                   │
     │                                                                                                                            │
     │                                            ⋯ Tiempo después ⋯                                                              │
     │                                                                                                                            │
     │                                                                                                                            │  GET /solicitudes/revision/
     │                                                                                                                            │ ◀─── personal opens queue
     │                                                                                                                            │ list_assigned(role)
     │                                                                                                                            │
     │                                                                                                                            │ POST .../atender/
     │                                                                                                  ReviewService.take()      │ ◀───
     │                                                                              transition(action=ACTION_ATENDER, …)          │
     │                                                                              ┌─ atomic ────────────────────────┐           │
     │                                                                              │ update_estado(EN_PROCESO)       │           │
     │                                                                              │ historial.append(CREADA→EN_PROC)│           │
     │                                                                              └─────────────────────────────────┘           │
     │                                                                              notify_state_change(folio, EN_PROCESO, obs)   │
     │                                                                              audit.write("solicitud.estado_cambiado", …)   │
     │                                                                                                                            │
     │                                                                                                                            │ POST .../finalizar/
     │                                                                                                  ReviewService.finalize()  │ ◀───
     │                                                                              transition(action=ACTION_FINALIZAR, …)        │
     │                                                                              ┌─ atomic ────────────────────────┐           │
     │                                                                              │ update_estado(FINALIZADA)       │           │
     │                                                                              │ historial.append(EN_PROC→FINAL) │           │
     │                                                                              └─────────────────────────────────┘           │
     │                                                                              notify_state_change(folio, FINALIZADA, obs)   │
     │                                                                              audit.write("solicitud.estado_cambiado", …)   │
```

## Step-by-step (happy path)

1. **GET /solicitudes/crear/`<slug>`/** — `CreateSolicitudView.get` calls `IntakeService.get_intake_form(slug, role, is_mentor)`. The service looks up the tipo (rejects with `Unauthorized` if `role ∉ tipo.creator_roles`), captures a `FormSnapshot`, and asks `build_intake_form` to wrap a dynamic form. Comprobante `FileField` is appended when `requires_payment AND not (mentor_exempt AND is_mentor)`.
2. **POST /solicitudes/crear/`<slug>`/** — view validates the bound form, builds `CreateSolicitudInput`, calls `IntakeService.create(input_dto, actor)`. The service:
   1. re-checks the role + active flag (defense in depth)
   2. captures a **fresh** snapshot (so any admin edits between GET and POST are reflected — the `Solicitud.form_snapshot` records what the user actually saw at submit time)
   3. computes `pago_exento` (only true when payment required AND tipo exempts mentors AND actor is a mentor)
   4. **inside `transaction.atomic()`** allocates a folio, inserts the `Solicitud` row, appends the initial `HistorialEstado` (estado_anterior=None, estado_nuevo=CREADA)
   5. **outside the atomic block** fires `NotificationService.notify_creation` and writes the audit line
   6. returns the hydrated `SolicitudDetail`
3. **Browser is redirected to `/solicitudes/<folio>/`** with `messages.success(...)`. If files were submitted, an additional `messages.warning(...)` informs the user that attachments are not yet stored (until 005 ships).
4. **GET /solicitudes/revision/** — Personal in `tipo.responsible_role` opens the queue. `ReviewService.list_assigned(role)` returns rows scoped to the role (admin sees all).
5. **POST /solicitudes/revision/`<folio>`/atender/** — `ReviewService.take` calls `LifecycleService.transition(action="atender", ...)`. The service:
   1. fetches the row → `SolicitudNotFound` on miss
   2. authorizes (`actor.role == tipo.responsible_role` OR `actor.role == ADMIN`)
   3. looks up `TRANSITIONS[(CREADA, "atender")] = EN_PROCESO`
   4. **inside `transaction.atomic()`** updates estado and appends a historial row
   5. **outside the atomic block** notifies and audits
6. **POST /solicitudes/revision/`<folio>`/finalizar/** — same shape with `ACTION_FINALIZAR`. The row reaches its terminal state.

## Cancellation paths

The `cancelar` action is reachable from several places, with different authorization rules. The state machine accepts `(CREADA, cancelar)` and `(EN_PROCESO, cancelar)`. Authorization is layered on top:

| Caller             | Allowed estados      | Entry point                        |
| ------------------ | -------------------- | ---------------------------------- |
| Solicitante (owner) | `CREADA` only        | `/solicitudes/<folio>/cancelar/` (intake) |
| Responsible role   | `CREADA` or `EN_PROCESO` | `/solicitudes/revision/<folio>/cancelar/` (revision) |
| Admin              | any non-terminal     | either entry point                 |

Forbidden combinations raise:

- `Unauthorized` (403) — caller is not in any of the allowed roles for the row.
- `InvalidStateTransition` (409) — caller is allowed to cancel in *some* estado, but not the row's current estado (e.g. solicitante on EN_PROCESO).

Both are caught at the view boundary and translated to a `messages.error(...)` flash + redirect to the detail page; the row's estado stays unchanged.

## Failure modes

- **Folio collision** — the current `OrmFolioRepository` strategy (`select_for_update` on a counter row) cannot produce duplicates. The `FolioCollision` exception is reserved for a future allocator strategy.
- **Snapshot drift** — admin edits the tipo between form-render and submit. Resolution: snapshot is captured at submit time inside the service, so the persisted row reflects what the user saw. `Tier-1::test_snapshot_integrity_when_tipo_label_changes_after_creation` asserts the persisted snapshot survives subsequent admin edits to the tipo.
- **Concurrent take** — two personnel both press "Atender" on the same row at the same moment. First-write-wins: one transition succeeds, the second sees `estado=EN_PROCESO` and gets `InvalidStateTransition`. Acceptable per the shared-queue requirement; UI surfaces the resulting flash.
- **Notification failure** — `NotificationService.notify_*` is fired *after* the transaction commits. A failure leaves the estado committed without the side-channel notification. With the current `NoOpNotificationService` this is not reachable; when 007 lands, the email adapter should swallow its own errors at the adapter boundary.
- **Audit failure** — same as notification: outside the transaction, best-effort. We may commit an estado without an audit line.
- **File upload before 005 ships** — files are read into memory by Django's `FileField`, validated for size/extension, then dropped. The user sees the warning flash; the operator sees the WARNING log line. When 005 lands, the contract is `archivo_service.store_for_solicitud(folio, field_id, uploaded_file)` called from `CreateSolicitudView.post` inside the same `atomic()` block as the row insert.

## Cross-app integration points (future)

- **005 (archivos)** — replaces the file-discard branch in `CreateSolicitudView.post` with a call to `archivo_service.store_for_solicitud(folio, ...)` inside the same `atomic()` block as the row insert.
- **006 (pdf)** — adds a "Descargar PDF" button on `intake/detail.html` and `revision/detail.html` when estado is FINALIZADA and the tipo has a plantilla. PDF rendering reads `Solicitud.form_snapshot` + `Solicitud.valores` and feeds them into the WeasyPrint pipeline.
- **007 (notificaciones)** — replaces the `NoOpNotificationService` binding in `lifecycle/dependencies.py` with the email adapter. The interface (`NotificationService` ABC in `lifecycle/notification_port.py`) does not change.
- **008 (mentores)** — *shipped.* Replaced the `FalseMentorService` binding in `intake/dependencies.py` with the real catalog lookup via `mentores.adapters.intake_adapter.MentoresIntakeAdapter` (producer-side adapter). The port interface (`MentorService` ABC in `intake/mentor_port.py`) is unchanged; intake's runtime code imports zero from `mentores.*` — only `intake/dependencies.py` does, at boot. See `specs/apps/mentores/catalog/design.md` for the catalog contract.
- **009 (reportes)** — reads from the same `Solicitud` and `HistorialEstado` tables; no schema or service changes here. The audit log lines provide the secondary timeline.

## Related Specs

- [intake/design.md](../apps/solicitudes/intake/design.md)
- [lifecycle/design.md](../apps/solicitudes/lifecycle/design.md)
- [revision/design.md](../apps/solicitudes/revision/design.md)
- [tipos/design.md](../apps/solicitudes/tipos/design.md)
- [formularios/design.md](../apps/solicitudes/formularios/design.md)
- [Initiative 004 plan](../planning/004-solicitud-lifecycle/plan.md)
- [`_shared/audit.md`](../shared/infrastructure/audit.md)
- [`_shared/request_actor.md`](../shared/infrastructure/request_actor.md)
