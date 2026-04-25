# formularios — Design

> Canonical reference for the runtime form builder. Updated after initiative 003 closed.

## Public surface

```python
from solicitudes.formularios.builder import build_django_form, field_attr_name
from solicitudes.formularios.schemas import FieldSnapshot, FormSnapshot
```

- **`build_django_form(snapshot: FormSnapshot) -> type[forms.Form]`** — returns a dynamically-constructed Django form class whose fields match `snapshot.fields`, ordered by `order`. **Fields with `source != FieldSource.USER_INPUT` are excluded entirely** (added by 011): they are absent from `Form.fields`, from `field_order`, and from `to_values_dict()`. This is the security boundary that drops malicious client `field_<auto_id>=...` payloads before they can land in `valores`. The class also carries a `to_values_dict(self) -> dict[str, Any]` method.
- **`field_attr_name(field_id: Any) -> str`** — `f"field_{str(field_id).replace('-', '')}"`. Deterministic, the only way callers should derive the form-field name from a snapshot field id.

## Schemas (`formularios/schemas.py`)

Frozen Pydantic v2 DTOs. `formularios` only consumes `tipos` data — never imports the ORM, never imports view code.

- **`FieldSnapshot`** — `field_id, label, field_type, required, order, options, accepted_extensions, max_size_mb, max_chars, placeholder, help_text, source`. Same shape as `FieldDefinitionDTO` minus the live `id`; `field_id` carries the original DB id forever (so historical solicitudes can resolve a deleted field). The `source` (added by 011) travels with the snapshot so the resolver can decide which field to auto-fill, even if the live `FieldDefinition.source` later changes.
- **`FormSnapshot`** — `tipo_id, tipo_slug, tipo_nombre, captured_at: datetime, fields: list[FieldSnapshot]`.

`tipo_slug` and `tipo_nombre` are denormalized into the snapshot so historical solicitude listings can render them without a join — they remain readable even if the tipo is later renamed.

## Type-to-Django mapping (`builder.py`)

| `FieldType` | Django field | Widget attrs | Validators |
|---|---|---|---|
| `TEXT` | `CharField(max_length=snap.max_chars or 200)` | `class="form-control"`, `placeholder` | (none extra) |
| `TEXTAREA` | `CharField(max_length=snap.max_chars or 2000, widget=Textarea)` | `class="form-control"`, `rows=4`, `placeholder` | (none extra) |
| `NUMBER` | `DecimalField` | `class="form-control"`, `step="any"` | (none extra) |
| `DATE` | `DateField` | `class="form-control"`, `type="date"` | (none extra) |
| `SELECT` | `ChoiceField(choices=[("", "---------"), *((o,o) for o in options)])` | `class="form-select"` | (none extra) |
| `FILE` | `FileField` | `class="form-control"`, `accept=",".join(accepted_extensions)` | `make_extension_validator(accepted_extensions)`, `make_size_validator(max_size_mb)` |

`required`, `label`, and `help_text` flow directly from the snapshot.

`max_chars=None` falls back to 200/2000 — older snapshots predating the column read with `None` and silently use the default cap. Setting `max_chars` on a non-text snapshot would raise at the schema layer; here in the builder we trust the snapshot is well-formed.

## Validators (`formularios/validators.py`)

- **`make_extension_validator(allowed: list[str]) -> Validator`** — returns a function that raises `ValidationError` with `code="invalid_extension"` if the uploaded file's extension is not in `allowed`. Compares lowercased.
- **`make_size_validator(max_size_mb: int) -> Validator`** — returns a function that raises `ValidationError` with `code="file_too_large"` and `params={"mb": max_size_mb}` when the upload exceeds the limit.

Both helpers exist as factories (not classes) because Django serializes validators by import path; using closures keeps the signature stable.

## Field attribute naming

`field_attr_name(field_id)` returns `field_<uuid-without-hyphens>`. The form class also exposes:

- **`field_order`** — list of attr names in `snapshot.order` order; templates iterate this for stable rendering.
- **`to_values_dict(self) -> dict[str, Any]`** — serializes `cleaned_data` to JSON primitives keyed by **string field_id** (with hyphens), not by attr name. Mapping:
  - `Decimal` → `str` (preserves precision for solicitud history)
  - `date` → ISO string
  - `FileField` → `value.name` only (file bytes go through 005's storage)

## Consumers

- **003 — `TipoDetailView`** instantiates `build_django_form(service.snapshot(tipo_id))` and renders the unbound form for the admin preview.
- **004 (planned) — Intake view** instantiates the same form bound to `request.POST` + `request.FILES`, calls `is_valid()`, and writes both the snapshot and `form.to_values_dict()` into the solicitud row. Files go through 005.

## Tests

`formularios/tests/test_builder.py` covers:
- One test per `FieldType` round-trip (valid + invalid input).
- `max_chars` enforcement and the default fallback.
- `to_values_dict` serialization for each type.
- `field_attr_name` determinism.

## Related Specs

- [requirements.md](./requirements.md) — WHAT/WHY for this feature
- [apps/solicitudes/tipos/design.md](../tipos/design.md) — produces the `FormSnapshot` consumed here
- [planning/003-catalog-forms](../../../planning/003-catalog-forms/plan.md) — implementation initiative
