# tipos — Requirements

## What

Admin-facing catalog of *tipos de solicitud*: each tipo describes one kind of academic/administrative request (e.g., "Constancia de Estudios", "Cambio de Programa") and carries the schema for its dynamic intake form.

A tipo has:
- An identity (slug + nombre + descripción).
- A **responsible role** that reviews its solicitudes (`CONTROL_ESCOLAR`, `RESPONSABLE_PROGRAMA`, or `DOCENTE`).
- A set of **creator roles** that may file requests of this kind (subset of `{ALUMNO, DOCENTE}`).
- Payment flags (`requires_payment`, `mentor_exempt`).
- A reference to a PDF plantilla (added in 006).
- An ordered list of typed `FieldDefinition`s (TEXT, TEXTAREA, NUMBER, DATE, SELECT, FILE) — this is the live form schema.

## Why

The university wants to roll out new procedures without code changes. An admin defines the procedure once; alumnos and docentes file solicitudes against that definition; the responsible role reviews them. Adding a new procedure ships from the admin UI, not a release.

The catalog also produces the `FormSnapshot` consumed by the intake feature (initiative 004) — a frozen copy of the tipo's fieldset captured at the moment a solicitud is filed. That snapshot is what makes it safe for an admin to keep editing a live tipo without breaking historical solicitudes.

## Scope

In:
- Admin CRUD over tipos and their fields.
- Per-tipo soft-delete (`activo=False`).
- Snapshot generation (consumed by 004).
- Live preview of the dynamic form on the create/edit page.

Out:
- Creating solicitudes (initiative 004).
- The `Plantilla` model and its FK link (initiative 006).
- Mentor catalog (initiative 008).

## Non-functional

- A tipo with historical solicitudes must remain queryable forever — soft-delete only, no hard-delete path. Historical solicitudes hold the tipo's slug/nombre in their snapshot, so the catalog row is the only place those identifiers can be cross-referenced.
- Editing a live tipo must not break solicitudes already filed against an earlier version. The intake snapshot decouples them.
- The admin UI is the only consumer; non-admin roles get 403 on every endpoint.

## Acceptance criteria added 2026-04-25 (initiative 011)

- The admin can declare a per-field **source** that determines whether the alumno fills it or the system auto-fills it from the requester's `UserDTO` (cached SIGA fields).
- Sources: `USER_INPUT` (default — alumno fills), `USER_FULL_NAME`, `USER_PROGRAMA`, `USER_EMAIL`, `USER_MATRICULA` (apply to TEXT), `USER_SEMESTRE` (applies to NUMBER). Other field types reject non-`USER_INPUT` sources at the schema layer.
- Auto-filled fields are **invisible to the alumno as form inputs** — they never re-type known data. They appear in a read-only "Datos del solicitante" panel above the form so the alumno can see what gets attached to their solicitud.
- The runtime auto-fill values come from the **backend** (intake re-hydrates `UserDTO` via `UserService` at submission) — never trust client-supplied values for these fields.
- If a field has `source != USER_INPUT` and `required=True` and the resolved `UserDTO` value is empty (SIGA failed and cache is empty too), the submission **fails fast** with a clear error pointing the alumno to Control Escolar. There is no silent partial save.
- The catalog's live preview (initiative 003) renders auto-filled fields as a non-editable pill marked "Auto" instead of as a form input.

## Related Specs

- [global/requirements.md](../../../global/requirements.md) — RF-01, RF-02
- [global/architecture.md](../../../global/architecture.md) — `tipos` and `formularios` features under `solicitudes`
- [planning/003-catalog-forms](../../../planning/003-catalog-forms/plan.md) — initial implementation
- [planning/011-field-autofill](../../../planning/011-field-autofill/plan.md) — `FieldSource` extension and runtime auto-fill
- [apps/solicitudes/formularios/design.md](../formularios/design.md) — runtime form builder consumes `FormSnapshot`
