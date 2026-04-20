# formularios — Requirements

## What

Runtime form builder. Given a frozen `FormSnapshot` (a copy of a tipo's fieldset), produces:

1. A dynamically-constructed Django `forms.Form` class whose fields match the snapshot.
2. A `to_values_dict(self)` helper on that class that serializes `cleaned_data` to JSON-safe primitives keyed by `field_id`.

Validators per field type:
- `TEXT` / `TEXTAREA` — `max_length` from `snap.max_chars` (default 200 for TEXT, 2000 for TEXTAREA).
- `NUMBER` — `DecimalField`, free range.
- `DATE` — `DateField` with `type="date"` widget.
- `SELECT` — `ChoiceField` over `snap.options` with a placeholder option.
- `FILE` — `FileField` with extension + size validators (`max_size_mb` enforced).

## Why

The catalog (`tipos`) is admin-editable. Solicitudes filed against a tipo must keep working even after the admin edits or removes fields. The intake feature (initiative 004) solves that by **freezing a snapshot of the tipo's fieldset** at the moment a solicitud is created and storing the snapshot inside the solicitud row.

Two consumers need to render forms from those snapshots:

- **Admin preview** on the catalog detail page — shows what creators will see.
- **Intake form** (initiative 004) — the real submit-bound form for an alumno/docente.

Both must produce identical UI, validation, and serialization. A single builder solves that — the snapshot is the contract.

## Scope

In:
- The form factory (`build_django_form`).
- Per-type widget + validator wiring.
- JSON-safe serialization helper (`to_values_dict`).

Out:
- Storing the snapshot (`Solicitud.form_snapshot` is defined in 004).
- File storage (initiative 005).
- PDF rendering (initiative 006).

## Non-functional

- The builder must be deterministic: the same snapshot always produces the same field attribute names (`field_<uuid-no-hyphens>`), so `cleaned_data` keys are stable across calls.
- The output `<input>`/`<select>`/`<textarea>` markup follows Bootstrap conventions (`form-control`, `form-select`).
- No ORM access. The builder takes a Pydantic DTO and returns a Django form class — pure transformation.

## Related Specs

- [global/requirements.md](../../../global/requirements.md) — RF-02
- [apps/solicitudes/tipos/design.md](../tipos/design.md) — produces `FormSnapshot`
- [planning/003-catalog-forms](../../../planning/003-catalog-forms/plan.md) — implementation initiative
- [planning/004-solicitud-lifecycle](../../../planning/004-solicitud-lifecycle/plan.md) — primary consumer (intake)
