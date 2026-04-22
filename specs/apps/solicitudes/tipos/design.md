# tipos — Design

> Canonical reference for the catalog feature. Updated after initiative 003 closed.

## Layer wiring

```
Admin browser → views/{list,create,detail,edit,delete}.py
                       │
                       ▼
                 TipoForm + FieldFormSet (cleaned_data → CreateTipoInput / UpdateTipoInput)
                       │
                       ▼
                 TipoService (interface in services/tipo_service/interface.py)
                       │
                       ▼
                 TipoRepository (interface in repositories/tipo/interface.py)
                       │
                       ▼
                 ORM (TipoSolicitud, FieldDefinition)
```

`tipos/dependencies.py` wires `OrmTipoRepository → DefaultTipoService` as factory functions; views call the factory once per request.

## Data shapes

### Models (`solicitudes/models/`)

- **`TipoSolicitud`** — `id` (UUID), `slug` (unique, ≤80), `nombre` (≤120), `descripcion` (text), `responsible_role` (`Role`), `creator_roles` (JSONField → `list[str]`), `requires_payment`, `mentor_exempt`, `plantilla` (FK → `solicitudes.PlantillaSolicitud`, nullable, `on_delete=SET_NULL`, `related_name="tipos"`; introduced in 006), `activo`, `created_at`, `updated_at`. Index on `(activo, responsible_role)`. The Django auto-generated `plantilla_id` accessor remains the public attribute name on the ORM row.
- **`FieldDefinition`** — `id` (UUID), `tipo` (FK CASCADE), `label` (≤120), `field_type` (`FieldType`), `required`, `order` (PositiveSmallInt), `options` (JSONField → `list[str]`, SELECT only), `accepted_extensions` (JSONField → `list[str]`, FILE only), `max_size_mb` (PositiveInt, FILE only, default 10), `max_chars` (PositiveInt, nullable, TEXT/TEXTAREA only), `placeholder` (≤200), `help_text` (≤300). Constraint: `unique (tipo, order)`. Default ordering: `order` asc.

### DTOs (`tipos/schemas.py`)

- **`FieldDefinitionDTO`** — frozen Pydantic: `id, label, field_type, required, order, options, accepted_extensions, max_size_mb, max_chars, placeholder, help_text`.
- **`TipoSolicitudDTO`** — frozen: full hydrated tipo with `fields: list[FieldDefinitionDTO]`.
- **`TipoSolicitudRow`** — frozen list-view DTO: `id, slug, nombre, responsible_role, creator_roles, requires_payment, activo, plantilla_id (UUID | None, default None)`. No fields. `plantilla_id` was added in 006 so consumers (notably `SolicitudDetail.tipo` and the intake/revision detail templates) can decide whether a PDF can be rendered without re-fetching the full tipo. Backwards-compatible default keeps existing constructors valid.
- **`CreateFieldInput`** / **`CreateTipoInput`** / **`UpdateTipoInput`** — input DTOs the form layer constructs from `cleaned_data`. Each carries the same shape as the persisted DTO plus Pydantic validators.

### Validator order (matters)

`CreateFieldInput` runs three `@model_validator(mode="after")` hooks, in this declaration order:

1. `_check_options` — SELECT must define options; non-SELECT must not.
2. `_check_extensions` — FILE must declare accepted_extensions; non-FILE must not.
3. `_check_max_chars_scope` — `max_chars` only allowed on TEXT/TEXTAREA.

Shape-of-value errors surface before the per-type-only flag errors so the admin sees the actionable fix first instead of the noisier stale-flag error. Cross-type values (`max_chars` on a FILE row, `max_size_mb` on a TEXT row) are normalized to defaults at the **form-clean layer** before they reach the schema — defense in depth.

`CreateTipoInput` validators: `creator_roles` ⊆ `{ALUMNO, DOCENTE}`; `responsible_role` ∈ `{CONTROL_ESCOLAR, RESPONSABLE_PROGRAMA, DOCENTE}`; `mentor_exempt` is auto-cleared when `requires_payment` is false (not rejected — quietly normalized so toggling off payment doesn't strand a stale flag); field count ≤ `MAX_FIELDS_PER_TIPO` (50); field `order` values unique within a tipo.

## Service surface

`TipoService` (`services/tipo_service/interface.py`):

| Method | Purpose | Raises |
|---|---|---|
| `list_for_admin(*, only_active, responsible_role=None)` | Admin index, optional responsible-role filter pushed down to SQL. | — |
| `list_for_creator(role)` | Tipos a given creator role can file (active + role ∈ creator_roles). | — |
| `get_for_admin(tipo_id)` | Full DTO. | `TipoNotFound` |
| `get_for_creator(slug, role)` | Defense-in-depth: re-checks `creator_roles ⊇ {role}` and `activo`. | `TipoNotFound` (when missing or inactive or role disallowed) |
| `create(input_dto)` | Persists tipo + fields atomically. | `TipoSlugConflict` |
| `update(input_dto)` | Replaces fieldset atomically (see Repository). | `TipoNotFound`, `TipoSlugConflict` |
| `deactivate(tipo_id)` | Soft-delete. | `TipoNotFound` |
| `snapshot(tipo_id)` | `FormSnapshot` of the active tipo's current fieldset, captured at `now()`. | `TipoNotFound` (when inactive) |

**Hard-delete is intentionally absent.** Tipos are tombstones — once filed against, they must remain queryable forever so historical solicitudes can resolve their own snapshot's `tipo_slug`/`tipo_nombre`. If a future need brings back hard-delete, it lands with its own in-use gate (`has_solicitudes`); the gate exists on the repository today but has no caller.

## Repository surface

`TipoRepository` (`repositories/tipo/interface.py`):

`get_by_id`, `get_by_slug`, `list(*, only_active, creator_role=None, responsible_role=None)`, `create(CreateTipoInput) → TipoSolicitudDTO`, `update(UpdateTipoInput) → TipoSolicitudDTO`, `deactivate(tipo_id) → None`, `has_solicitudes(tipo_id) → bool` (returns `False` until 004 introduces the `Solicitud` model).

`OrmTipoRepository` notes:
- `prefetch_related("fields")` on every read that returns a full DTO; bulk lists skip it.
- `creator_role` filter uses `creator_roles__contains=[role.value]` — Django translates per backend (Postgres `?` containment, SQLite `__contains`).
- Slug auto-derived from `nombre` (`slugify` + numeric suffix on collision).
- `update` is the only complex path. It runs in a `transaction.atomic()`:
  1. Delete `FieldDefinition` rows whose ids are not in the input.
  2. Two-phase order rewrite to dodge the `unique (tipo, order)` constraint: park surviving rows at `order + 1000` (asserted to exceed `MAX_FIELDS_PER_TIPO`), then write the real values.
  3. Update existing rows in place, create new rows.

## Exceptions (`tipos/exceptions.py`)

All inherit from `_shared.exceptions.AppError`:

- **`TipoNotFound`** — `code="tipo_not_found"`, 404. Raised by repository on `DoesNotExist`.
- **`TipoSlugConflict`** — `code="tipo_slug_conflict"`, 409. Raised by repository on slug uniqueness collision.
- **`InvalidFieldDefinition`** — `code="invalid_field_definition"`, 422. Reserved for service-level field validation (currently the Pydantic validators carry this surface).

## Admin views & templates

URLs (mounted via `solicitudes/urls.py` → `tipos/urls.py`, namespace `solicitudes:tipos`):

| URL | View | Methods | Purpose |
|---|---|---|---|
| `admin/tipos/` | `TipoListView` | GET | Index with active/inactive + responsible-role filter |
| `admin/tipos/nuevo/` | `TipoCreateView` | GET, POST | Create + initial fields |
| `admin/tipos/<uuid:tipo_id>/` | `TipoDetailView` | GET | Read-only detail with form preview |
| `admin/tipos/<uuid:tipo_id>/editar/` | `TipoEditView` | GET, POST | Edit metadata + fields |
| `admin/tipos/<uuid:tipo_id>/desactivar/` | `TipoDeactivateView` | GET, POST | Soft-delete confirm |

All views require admin (`AdminRequiredMixin` from `usuarios.permissions`). Stale-id POSTs on edit/deactivate redirect to the list with a flash, never 500.

Templates under `templates/solicitudes/admin/tipos/`: `list.html`, `form.html` (shared by create/edit), `_field_row.html` (one card per field, cloned by JS), `detail.html`, `confirm_deactivate.html`.

### Form ergonomics (`tipos/forms/`)

- `TipoForm` carries metadata (nombre, descripción, responsible_role, creator_roles, requires_payment, mentor_exempt).
- `FieldFormSet = formset_factory(FieldForm, extra=0, max_num=MAX_FIELDS_PER_TIPO, can_delete=True)` carries the rows.
- `FieldForm.clean()` parses CSV inputs to lists, validates per-type (SELECT options, FILE extensions), and **normalizes cross-type values** (`max_size_mb → 10` when not FILE; `max_chars → None` when not TEXT/TEXTAREA) so a stale value from a now-hidden input cannot reach the schema.
- View helpers in `tipos/views/_helpers.py` translate `cleaned_data` to `CreateTipoInput`/`UpdateTipoInput` after `formset.is_valid()`. `_collect_fields` skips DELETE-marked rows but **never silently skips invalid rows** — that would mask user errors.

### Catalog admin UI (delivered in 003)

Beyond plain CRUD, the catalog editor ships these UX affordances; future contributors should preserve the contract:

- **Collapsible field cards.** Each `FieldDefinition` row is a card with a header (drag handle, label preview, type badge, ↑/↓ buttons, delete) and a collapsible body. New rows open expanded; siblings auto-collapse so focus stays on the row being edited.
- **Drag reorder + accessible ↑/↓ fallback.** `SortableJS` (vendored at `static/vendor/sortablejs/`, MIT, `handle: .field-drag-handle`) for pointer/touch; ↑/↓ buttons are the keyboard fallback (WCAG 2.5.7). The `order` column is hidden in the UI; the JS rewrites every row's `<input name="fields-N-order">` from its DOM position right before submit. Rows soft-deleted via `DELETE=true` are skipped during this rewrite so persisted orders are contiguous `0..n-1`.
- **Delete branches.** Existing rows (with a stable `field_id`) flip the formset's `DELETE` checkbox and hide; new rows are popped from the DOM **and the formset is renumbered** to a contiguous `0..n-1` sequence (`renumberRows()` in `tipo_form.js`). Without renumber, Django's formset reads a hole as "row missing" and silently drops every subsequent row.
- **Per-type cell visibility.** Each type-scoped input cell carries `data-shows-for="TYPE[,TYPE...]"`; the JS toggles visibility on `field_type` change. SELECT → chip-input options + live `<select>` preview, FILE → btn-check extension multiselect (`COMMON_FILE_EXTENSIONS` constant grouped Documentos/Imágenes/Hojas de cálculo/Otros) + max size, TEXT/TEXTAREA → `max_chars`.
- **Live preview pane.** A sticky `<aside>` to the right of the editor at `xl+` (1200px), stacked below at narrower widths. Renders real Bootstrap controls (interactive, no `name` attribute → never submitted) plus the tipo's nombre/descripción header. Triggered by a delegated `input`/`change` listener on `#field-rows` plus a `MutationObserver(childList, subtree)` for add/delete/Sortable reorders.
- **Legend sized as a label.** Bootstrap reboot ships `<legend>` at ~1.5rem; the `creator_roles` legend is forced to `fs-6 fw-normal mb-2 float-none w-auto p-0` so it matches sibling labels.

## Constants (`tipos/constants.py`)

- `FieldType` (StrEnum): `TEXT`, `TEXTAREA`, `NUMBER`, `DATE`, `SELECT`, `FILE`.
- `MAX_FIELDS_PER_TIPO = 50`.
- `ALLOWED_CREATOR_ROLES = {ALUMNO, DOCENTE}`.
- `ALLOWED_RESPONSIBLE_ROLES = {CONTROL_ESCOLAR, RESPONSABLE_PROGRAMA, DOCENTE}`.
- `COMMON_FILE_EXTENSIONS` — sectioned tuple of (group_label, extensions); fed to the row template via `tipos_tags.common_file_extensions`.

## What 004 consumes from this feature

- `TipoService.list_for_creator(role)` for the "elegir tipo" page.
- `TipoService.snapshot(tipo_id)` at the moment a solicitud is filed; the resulting `FormSnapshot` is stored inside the solicitud row.
- `formularios.build_django_form(snapshot)` to render the intake form (see `formularios/design.md`).

## Related Specs

- [requirements.md](./requirements.md) — WHAT/WHY for this feature
- [planning/003-catalog-forms](../../../planning/003-catalog-forms/plan.md) — implementation initiative
- [apps/solicitudes/formularios/design.md](../formularios/design.md) — snapshot consumer
- [apps/usuarios/design.md](../../usuarios/design.md) — `Role`, `AdminRequiredMixin`
