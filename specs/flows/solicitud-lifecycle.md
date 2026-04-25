# Flow — Solicitud Lifecycle

> **Status:** v1 (initiative 004). 005 (archivos), 006 (PDF), 007 (notificaciones), 008 (mentores) and 009 (reportes) have shipped. Remaining cross-feature integration: 010 swaps the dev-login picker for the real auth provider. The skeleton documented here is stable.
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
     │                │                     │   → email per staff with responsible_role │                     │                  │
     │                │                     │   → acuse de recibo to solicitante        │                     │                  │
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

1. **GET /solicitudes/crear/`<slug>`/** — `CreateSolicitudView.get` calls `IntakeService.get_intake_form(slug, role, is_mentor, actor_matricula)`. The service looks up the tipo (rejects with `Unauthorized` if `role ∉ tipo.creator_roles`), captures a `FormSnapshot`, asks `build_intake_form` to wrap a dynamic form (which **excludes auto-fill fields** so the alumno never sees them as inputs), and computes a lenient `AutoFillPreview` from the actor's hydrated `UserDTO` (added by 011). Comprobante `FileField` is appended when `requires_payment AND not (mentor_exempt AND is_mentor)`. The view renders the read-only "Datos del solicitante" panel above the form; if `preview.has_missing_required` is true the panel shows an alert and the submit button is disabled.
2. **POST /solicitudes/crear/`<slug>`/** — view validates the bound form, builds `CreateSolicitudInput`, calls `IntakeService.create(input_dto, actor)`. The service:
   1. re-checks the role + active flag (defense in depth)
   2. captures a **fresh** snapshot (so any admin edits between GET and POST are reflected — the `Solicitud.form_snapshot` records what the user actually saw at submit time)
   3. resolves auto-fill values via `AutoFillResolver.resolve(snapshot, actor_matricula=actor.matricula)` (added by 011) — strict path; raises `AutoFillRequiredFieldMissing` (422) when a required `USER_*` field has an empty resolved value. The merge `{**input_dto.valores, **auto_values}` is defensive: the form factory already excluded auto-fill `field_id`s, so client-supplied values for them never reached `valores`
   4. computes `pago_exento` (only true when payment required AND tipo exempts mentors AND actor is a mentor)
   5. **inside `transaction.atomic()`** allocates a folio, inserts the `Solicitud` row with the merged `valores`, appends the initial `HistorialEstado` (estado_anterior=None, estado_nuevo=CREADA)
   6. **outside the atomic block** fires `NotificationService.notify_creation` (one email per staff member with `tipo.responsible_role`, plus an acuse de recibo to the solicitante; failures logged + absorbed) and writes the audit line
   7. returns the hydrated `SolicitudDetail`
3. **Browser is redirected to `/solicitudes/<folio>/`** with `messages.success(...)`. Any attached FORM files and the comprobante (when required) have been persisted by `archivo_service.store_for_solicitud(...)` inside the same outer `transaction.atomic()` as the row insert; the detail page renders the archivos in their own card with download links.
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
- **Notification failure** — `NotificationService.notify_*` is fired *after* the transaction commits. A failure leaves the estado committed without the side-channel notification. As of 007, `DefaultNotificationService` swallows `EmailDeliveryError` at the adapter boundary and logs `event=email_delivery_error`; the per-recipient send loop in `notify_creation` continues after a single failure.
- **Audit failure** — same as notification: outside the transaction, best-effort. We may commit an estado without an audit line.
- **File-write rollback on intake** — `CreateSolicitudView.post` wraps the `Solicitud` insert and every `archivo_service.store_for_solicitud(...)` call in one outer `transaction.atomic()`. Storage writes go to a `.partial` sibling and are renamed via `transaction.on_commit` only when the outer atomic commits; on rollback, the view's `try/finally` calls `storage.cleanup_pending()` to delete the orphaned `.partial` files. See `apps/solicitudes/archivos/design.md` for the post-commit ENOSPC failure mode that is *not* recoverable transactionally.

## Cross-app integration points (future)

- **005 (archivos)** — *shipped.* `CreateSolicitudView.post` calls `archivo_service.store_for_solicitud(folio, ...)` for each FORM file and the comprobante inside the same outer `transaction.atomic()` as the row insert. Detail and revision views render the archivos partial. See `apps/solicitudes/archivos/design.md`.
- **006 (pdf)** — adds a "Descargar PDF" button on `intake/detail.html` and `revision/detail.html` when estado is FINALIZADA and the tipo has a plantilla. PDF rendering reads `Solicitud.form_snapshot` + `Solicitud.valores` and feeds them into the WeasyPrint pipeline.
- **007 (notificaciones)** — shipped. `lifecycle/dependencies.py` now wires `DefaultNotificationService` (in `notificaciones/`) with a read-only sibling `LifecycleService` to break the construction cycle. `notify_creation` fans out to staff *and* sends an acuse to the solicitante; `notify_state_change` emails the solicitante. Failures are logged and absorbed. The `NotificationService` ABC in `lifecycle/notification_port.py` did not change.
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
