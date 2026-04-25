# intake — Requirements

> WHAT this feature does and WHY. No implementation details. Shipped by initiative **004 — Solicitud Lifecycle**.

## Purpose

The solicitante's surface. Intake answers four questions for an authenticated alumno or docente:

1. *Which tipos can I file right now?* (catalog filtered by `creator_roles ⊇ {my role}` and `activo`)
2. *What does the form look like?* (the dynamic form of the chosen tipo, with a comprobante field if payment is required and I'm not exempt)
3. *Can I file it?* (validation, snapshot capture, atomic persistence with file uploads, folio assignment, initial historial entry, notification)
4. *What did I file, and can I cancel it?* (Mis solicitudes list, detail view, owner-only cancellation while `estado = CREADA`)

This is the entry point that turns a tipo definition into a real, traceable solicitud. Without intake, the catalog has nothing to consume it and the lifecycle state machine has nothing to advance.

## Why a separate feature from `lifecycle` and `revision`

`lifecycle` owns the state machine, the models, and the cross-feature ports. `revision` is the personal-side mirror that advances solicitudes through the queue. `intake` is the *solicitante-side* HTTP boundary — its templates, forms, view authorization (creators only), and the special "cancel my own" verb are all alumno/docente-specific. Mixing them into lifecycle would couple solicitante presentation to the state machine; mixing them into revision would conflate the two distinct UX surfaces (one fills a form, the other works a queue).

## In scope

- A **catalog page** showing the tipos the actor's role is authorized to create, filtered to active tipos only.
- A **dynamic create form** rendered from the chosen tipo's current field definitions, with file fields where applicable and an additional **comprobante** file field when `tipo.requires_payment` AND the actor is not exempt.
- **Snapshot capture at submit time**: the form definition stored on the resulting solicitud reflects what the tipo looked like at the moment of creation, never an earlier or later version.
- **Atomic persistence**: the new solicitud row, the initial historial entry, and any uploaded files commit together or roll back together.
- **Folio assignment** (`SOL-YYYY-NNNNN`, sequential per year) by delegating to the lifecycle feature's folio service.
- **Notification fan-out** on creation (delegated through the lifecycle feature's outbound notification port; the no-op binding is acceptable until initiative 007 ships).
- A **"Mis solicitudes" list** and a **detail page** for the solicitante, plus a **cancel-own** action restricted to estado `CREADA`.
- **Defense-in-depth authorization**: the URL-level role mixin is the coarse filter; the service re-checks `actor.role ∈ tipo.creator_roles` and `tipo.activo` before persistence.
- **Exemption resolution** at the view boundary: the view (not the service) calls the outbound `MentorService` port; the service trusts the boolean it's handed.

## Out of scope

- Owning the state machine, the `Solicitud` / `HistorialEstado` / `FolioCounter` models, or the `cancelar` authorization rules — that's `lifecycle`.
- Reviewing solicitudes (taking them, finalizing, cancelling-as-personal) — that's `revision`.
- Sending email — `notificaciones` (initiative 007); intake only fires the port.
- File storage primitives — `archivos` (initiative 005); intake invokes `ArchivoService.store_for_solicitud` per uploaded file but never touches storage directly.
- PDF rendering — `pdf` (initiative 006); intake's detail view simply gates a "Descargar PDF" button on `tipo.plantilla_id` + finalized estado.
- Determining who is a mentor — `mentores` (initiative 008); intake declares the outbound port and the producer adapts.

## Functional requirements

| ID | Requirement | Source |
|---|---|---|
| RF-INT-01 | An authenticated alumno or docente must see only the **active** tipos whose `creator_roles` include their role. Other tipos must not be discoverable through the catalog. | RF-04, RF-06 |
| RF-INT-02 | Filing a solicitud must capture a **snapshot** of the tipo's field definitions at the moment of submit. Subsequent edits to the tipo must not alter solicitudes already filed. | RF-04 |
| RF-INT-03 | When the tipo requires payment and the actor is not exempt, the form must include a required comprobante file field; otherwise the field must be absent. | RF-04 |
| RF-INT-04 | The comprobante exemption must be evaluated at create time as `tipo.requires_payment AND tipo.mentor_exempt AND is_mentor(actor)`, and the resulting `pago_exento` flag must be **stamped onto the solicitud row** so it survives later changes to the tipo or the mentor list. | RF-04, RF-11 |
| RF-INT-05 | Each new solicitud must be assigned a unique folio of the form `SOL-YYYY-NNNNN`, sequential per calendar year. | RF-04 |
| RF-INT-06 | The new solicitud, its initial `CREADA` historial entry, and all attached files must persist atomically. A failure at any step must roll back the others; partially-written files on disk must be cleaned up. | RF-04, RF-10 |
| RF-INT-07 | After successful persistence, intake must fire the lifecycle feature's notification port (`notify_creation`). A failure in the notification path must not roll back the committed solicitud. | RF-07 |
| RF-INT-08 | A solicitante must see only their own solicitudes in "Mis solicitudes", with filters for folio (substring), estado, and date range. | RF-08 |
| RF-INT-09 | The detail page must be reachable by the solicitante, by personal in the row's `responsible_role`, and by admin. Other users must receive 403. | RF-08, RF-09 |
| RF-INT-10 | The solicitante may cancel their own solicitud only while `estado = CREADA`. Cancellation in any other estado must be denied at the lifecycle layer. | RF-05 |
| RF-INT-11 | The catalog and create endpoints must require the actor to be `ALUMNO` or `DOCENTE` at the URL level; the service must additionally re-verify the actor's role against `tipo.creator_roles`. | RF-06, defense-in-depth |
| RF-INT-12 | Invalid form input (extension, size, missing required fields, bad enum) must re-render the form with field-level errors; the solicitud row must not be created. | RF-04, UX |

## Non-functional requirements

- **Snapshot integrity is non-negotiable.** Once a solicitud is filed, the rendered form, the values, the requires-pago flag, and the exemption flag must all reflect *create-time* state. Any later admin edit, mentor deactivation, or tipo deletion must not retroactively change a filed solicitud's display or audit shape.
- **Cross-feature direction is one-way.** Intake consumes `tipos`, `lifecycle`, `archivos`, `usuarios`. Intake declares an outbound `MentorService` port; the producer (`mentores`) provides the adapter. Intake's runtime code must not import from `mentores.*` directly.
- **The view, not the service, calls outbound ports for actor-derived data.** The mentor lookup happens at the view boundary; the service receives `is_mentor_at_creation` as a primitive on its input DTO. This keeps the service pure-domain and the cross-feature reach pinned to one place.
- **Notifications and audit are best-effort.** They fire after the transaction commits. A notification or audit failure must not undo a committed solicitud.
- **Spanish UI copy** end-to-end (catalog cards, form labels, error messages, success toasts, detail page, cancellation confirmation). Code identifiers in English.
- **WCAG color-as-only-signal** is satisfied: estado is conveyed by text *and* color in every badge.
- **No JSON API by default.** The intake surface is server-rendered HTML.

## Auto-fill from user data (initiative 011)

Initiative 011 extended intake's create flow with a server-side resolver that
plucks values from the actor's hydrated `UserDTO` for any snapshot field
whose `source != USER_INPUT`. The alumno never types those fields; they
appear in a read-only **"Datos del solicitante"** panel above the form.

| ID | Requirement | Source |
|---|---|---|
| RF-INT-13 | The intake page must render a read-only "Datos del solicitante" panel listing every auto-fill field the snapshot declares, with each field's resolved value pulled from the actor's `UserDTO`. | 011 |
| RF-INT-14 | Auto-fill values must come exclusively from the backend. Client-supplied values for auto-fill `field_id`s must be silently dropped — only the resolved server value lands in the persisted `valores`. | 011 |
| RF-INT-15 | If a `required=True` auto-fill field has an empty resolved value (SIGA down + cache empty), the submission must fail with a 422 and a flash message pointing the alumno to Control Escolar. No partial save. | 011 |
| RF-INT-16 | When the same condition is detected at GET time (preview), the page must render the panel with a top-of-page alert and disable the submit button so the alumno cannot post. | 011 |
| RF-INT-17 | Optional auto-fill fields with empty resolved values must be **dropped** from the persisted `valores`, not written as `null` / `""`. Mirrors `DynamicTipoForm.to_values_dict()`'s treatment of absent values. | 011 |

## Open questions

None at initiative closeout for 011. The original 011 open question (whether auto-fill should be one initiative or split into 011a/011b) was answered by shipping it as one — see `specs/planning/011-field-autofill/changelog.md`.

## Related Specs

- [design.md](./design.md) — HOW.
- [`specs/apps/solicitudes/lifecycle/design.md`](../lifecycle/design.md) — owner of `Solicitud` / `HistorialEstado` / `FolioCounter`, the state machine, and the `NotificationService` port.
- [`specs/apps/solicitudes/revision/design.md`](../revision/design.md) — personal-side mirror.
- [`specs/apps/solicitudes/tipos/design.md`](../tipos/design.md) — provides `get_for_creator`, `snapshot`, and the catalog filter rules.
- [`specs/apps/solicitudes/formularios/design.md`](../formularios/design.md) — the form builder intake wraps.
- [`specs/apps/solicitudes/archivos/design.md`](../archivos/design.md) — the file-storage service intake calls per upload.
- [`specs/apps/mentores/catalog/design.md`](../../mentores/catalog/design.md) — the producer side of the `MentorService` port.
- [`specs/flows/solicitud-lifecycle.md`](../../../flows/solicitud-lifecycle.md) — end-to-end sequence.
- [`specs/global/requirements.md`](../../../global/requirements.md) — RF-04, RF-05, RF-06, RF-07, RF-08, RF-09, RF-10, RF-11.
