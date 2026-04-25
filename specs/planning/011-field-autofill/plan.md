# 011 — Field Auto-fill from User Data

## Summary

Extend `FieldDefinition` with a per-field **source** so admins can declare "this field is auto-filled from the alumno's profile, not typed in". At intake time, the alumno never sees those fields as form inputs; the backend re-hydrates the `UserDTO` via SIGA, plucks the requested attributes, and merges them into the solicitud's `valores`. A read-only "Datos del solicitante" panel shows the alumno what the system will attach to their submission. If a required auto-fill field has no resolvable value (SIGA down + cache empty), the submission fails fast with a clear error.

This consolidates the catalog's live-preview UX (initiative 003) with the intake flow (initiative 004) and the SIGA hydration plumbing already shipped in 002.

## Depends on

- **003** — `FieldDefinition`, `FieldSnapshot`, `build_django_form`, the catalog's live preview pane.
- **004** — intake view + service (where the runtime auto-fill happens).
- **002** — `UserService.hydrate_from_siga`, `SigaService` (the data source).

> **Note on sequencing.** Tasks under "Schema delta" and "Catalog admin UI" can land before 004 is done — they only touch `tipos/` and `formularios/`. The "Intake integration" tasks must wait for 004's `intake/` package to exist. The plan is split accordingly.

## Affected Apps / Modules

- `solicitudes/tipos/` — new `FieldSource` constant; `FieldDefinition.source` column; schema validators; admin form + template; live preview update.
- `solicitudes/formularios/` — `FieldSnapshot.source`; builder skips non-`USER_INPUT` fields; service-level snapshot includes the new column.
- `solicitudes/intake/` — runtime resolver service that converts a snapshot's auto-fill fields into `valores` from a `UserDTO`; intake-view integration; failure path.
- `usuarios/` — no code changes; consumes `UserService.hydrate_from_siga` as a service-to-service call.

## References

- [apps/solicitudes/tipos/requirements.md](../../apps/solicitudes/tipos/requirements.md) — extended 2026-04-25 with the source acceptance criteria
- [apps/solicitudes/formularios/requirements.md](../../apps/solicitudes/formularios/requirements.md) — extended 2026-04-25 with snapshot/builder behavior
- [apps/solicitudes/tipos/design.md](../../apps/solicitudes/tipos/design.md) — current FieldDefinition shape and admin UI conventions
- [apps/solicitudes/formularios/design.md](../../apps/solicitudes/formularios/design.md) — current snapshot/builder
- [apps/usuarios/design.md](../../apps/usuarios/design.md) — `UserService.hydrate_from_siga`, `SigaProfile` shape (alumno-shaped today; see OQ-011-2)
- [planning/003-catalog-forms/plan.md](../003-catalog-forms/plan.md) — catalog scaffold this initiative extends
- [planning/004-solicitud-lifecycle/plan.md](../004-solicitud-lifecycle/plan.md) — intake view this initiative plugs into
- [global/requirements.md](../../global/requirements.md) — RNF-02 (SIGA integration)

## Implementation Details

### 1. `FieldSource` enum (`solicitudes/tipos/constants.py`)

```python
class FieldSource(StrEnum):
    USER_INPUT      = "USER_INPUT"      # default — alumno fills the form input
    USER_FULL_NAME  = "USER_FULL_NAME"  # auto-fill from UserDTO.full_name (TEXT)
    USER_PROGRAMA   = "USER_PROGRAMA"   # auto-fill from UserDTO.programa  (TEXT)
    USER_EMAIL      = "USER_EMAIL"      # auto-fill from UserDTO.email     (TEXT)
    USER_MATRICULA  = "USER_MATRICULA"  # auto-fill from UserDTO.matricula (TEXT)
    USER_SEMESTRE   = "USER_SEMESTRE"   # auto-fill from UserDTO.semestre  (NUMBER)


# Source ↔ FieldType compatibility — enforced by Pydantic validator below.
FIELD_SOURCE_ALLOWED_TYPES: dict[FieldSource, frozenset[FieldType]] = {
    FieldSource.USER_INPUT:     frozenset(FieldType),
    FieldSource.USER_FULL_NAME: frozenset({FieldType.TEXT}),
    FieldSource.USER_PROGRAMA:  frozenset({FieldType.TEXT}),
    FieldSource.USER_EMAIL:     frozenset({FieldType.TEXT}),
    FieldSource.USER_MATRICULA: frozenset({FieldType.TEXT}),
    FieldSource.USER_SEMESTRE:  frozenset({FieldType.NUMBER}),
}
```

### 2. DB schema delta

```python
# solicitudes/models/field_definition.py
class FieldDefinition(models.Model):
    ...
    source = models.CharField(
        max_length=24,
        choices=FieldSource.choices(),
        default=FieldSource.USER_INPUT.value,
    )
```

Migration `0005_fielddefinition_source.py` (additive — defaults to `USER_INPUT` for legacy rows). Plan originally pre-allocated `0002`, but `solicitudes/migrations/` already contains `0001..0004` from initiatives 003/004/005 — `0005` is the next free slot.

### 3. DTO + snapshot delta

```python
# solicitudes/tipos/schemas.py
class FieldDefinitionDTO(BaseModel):
    ...
    source: FieldSource = FieldSource.USER_INPUT

class CreateFieldInput(BaseModel):
    ...
    source: FieldSource = FieldSource.USER_INPUT

    @model_validator(mode="after")
    def _check_source_matches_type(self) -> CreateFieldInput:
        allowed = FIELD_SOURCE_ALLOWED_TYPES[self.source]
        if self.field_type not in allowed:
            raise ValueError(
                f"source={self.source.value} only applies to "
                f"{', '.join(t.value for t in allowed)} fields"
            )
        return self
```

Validator order in `CreateFieldInput`: keep `_check_options` and `_check_extensions` first (shape errors), then `_check_max_chars_scope`, then `_check_source_matches_type`. The new check is a per-type scope assertion analogous to `max_chars`.

```python
# solicitudes/formularios/schemas.py
class FieldSnapshot(BaseModel):
    ...
    source: FieldSource = FieldSource.USER_INPUT
```

### 4. Repository + service propagation

- `OrmTipoRepository.create` / `_replace_fields` / `_to_dto` carry `source`.
- `DefaultTipoService.snapshot` carries `source` into the `FieldSnapshot`.
- View helper `_collect_fields` reads `cleaned_data.get("source", "USER_INPUT")`.

### 5. Admin form (`tipos/forms/field_form.py`)

```python
class FieldForm(forms.Form):
    ...
    source = forms.ChoiceField(
        label="Fuente del campo",
        choices=FieldSource.choices(),
        initial=FieldSource.USER_INPUT.value,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # No help_text. The choice labels themselves are self-explanatory in
    # Spanish ("El solicitante lo escribe" / "Auto · Programa" / …) and
    # mentioning the internal `USER_*` identifiers in user-facing copy was
    # technical and misleading.

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        ...
        # Normalize: USER_* sources are only meaningful on TEXT/NUMBER. If the
        # admin switches type and leaves a stale source, reset to USER_INPUT.
        ft = FieldType(cleaned.get("field_type") or "TEXT")
        src = FieldSource(cleaned.get("source") or "USER_INPUT")
        if ft not in FIELD_SOURCE_ALLOWED_TYPES[src]:
            cleaned["source"] = FieldSource.USER_INPUT.value
        return cleaned
```

### 6. Admin template (`templates/solicitudes/admin/tipos/_field_row.html`)

A new cell tagged `data-shows-for="TEXT,NUMBER"` exposes the `source` dropdown — invisible for SELECT/FILE/DATE/TEXTAREA where source can only be `USER_INPUT`. Reuses the existing `data-shows-for` toggle plumbing from 003.

**Hide input-decoration cells when source is auto-fill.** A field with `source != USER_INPUT` has no alumno-typed value, so the cells that decorate the input box (`max_chars`, `placeholder`, `help_text`) are dead UI when auto-fill is selected. Mark those cells with a new boolean attribute `data-hide-when-auto-fill` and extend the JS toggle so a cell is visible iff:

1. its `data-shows-for` matches the current `field_type` (or it has no `data-shows-for`), **AND**
2. it has no `data-hide-when-auto-fill` **OR** the current `source` is `USER_INPUT`.

The toggle now listens on both the `field_type` and `source` selects. Cells kept visible for auto-fill: `label`, `field_type`, `required`, `source`. Cells hidden: `max_chars`, `placeholder`, `help_text` (plus the type-only ones already hidden by `data-shows-for`: SELECT options, FILE extensions/size).

### 7. Builder change (`solicitudes/formularios/builder.py`)

```python
def build_django_form(snapshot: FormSnapshot) -> type[forms.Form]:
    attrs: dict[str, Any] = {}
    user_input_fields = [f for f in snapshot.fields if f.source is FieldSource.USER_INPUT]
    ordered = sorted(user_input_fields, key=lambda f: f.order)
    for snap in ordered:
        attrs[field_attr_name(snap.field_id)] = _build_django_field(snap)
    attrs["field_order"] = [field_attr_name(s.field_id) for s in ordered]
    ...
```

Auto-fill fields are excluded entirely from the Django form. They still travel inside the snapshot, so 006's PDF builder and the detail view see them in `valores`.

### 8. Resolver (`solicitudes/intake/services/auto_fill_resolver/`)

```python
class AutoFillResolver(ABC):
    @abstractmethod
    def resolve(
        self,
        snapshot: FormSnapshot,
        actor_matricula: str,
    ) -> dict[str, Any]:
        """
        Hydrate the actor's UserDTO via UserService and return
        ``{field_id_str: value}`` for every snapshot field with
        ``source != USER_INPUT``. Empty mapping when no auto-fill fields exist.

        Raises ``AutoFillRequiredFieldMissing`` if any auto-fill field is
        ``required=True`` and the resolved UserDTO has no value for the
        requested attribute (SIGA down + cache empty path).
        """
```

`DefaultAutoFillResolver` is constructor-injected with `UserService`. `solicitudes/intake/dependencies.py` wires it.

```python
# solicitudes/intake/exceptions.py
class AutoFillRequiredFieldMissing(DomainValidationError):
    code = "auto_fill_required_missing"
    user_message = (
        "No pudimos cargar tus datos académicos del SIGA y este formulario "
        "los necesita. Intenta de nuevo en unos minutos o contacta a "
        "Control Escolar si el problema persiste."
    )
```

The resolver maps each `FieldSource` to the `UserDTO` attribute:

| `FieldSource` | `UserDTO` attr | Default when missing |
|---|---|---|
| `USER_FULL_NAME` | `full_name` | `""` |
| `USER_PROGRAMA` | `programa` | `""` |
| `USER_EMAIL` | `email` | (always present) |
| `USER_MATRICULA` | `matricula` | (always present) |
| `USER_SEMESTRE` | `semestre` | `None` |

"Missing" = the resolved value is `""` or `None`. `email` and `matricula` come from the JWT and are always present, so a resolver that requests them effectively never fails on that path; they're included for completeness.

### 9. Intake integration (modifies 004's intake.create)

```python
# solicitudes/intake/services/intake_service/implementation.py (extends what 004 ships)

def create(self, input_dto: CreateSolicitudInput) -> SolicitudDTO:
    snapshot = self._tipo_service.snapshot(input_dto.tipo_id)

    # NEW in 011: resolve auto-fill values from the actor's UserDTO before
    # validation. Raises AutoFillRequiredFieldMissing on empty required values.
    auto_values = self._auto_fill.resolve(snapshot, input_dto.actor_matricula)
    merged = {**input_dto.valores, **auto_values}

    # Existing 004 path: validate the merged values against the snapshot.
    FormCls = build_django_form(snapshot)  # only USER_INPUT fields
    form = FormCls(data=input_dto.valores)
    if not form.is_valid():
        raise InvalidSolicitudPayload(...)
    final_values = {**form.to_values_dict(), **auto_values}

    return self._repo.create(... valores=final_values ...)
```

Note: the form is built and validated only over `USER_INPUT` fields (the alumno-supplied data). Auto-fill values are merged on top — they bypass form validation but are produced by trusted code, not the client. The intake view never accepts client-side values for auto-fill field ids; if a malicious client POSTs `valores[field_id]` for an auto-fill field, that value is **dropped** because the form factory doesn't include the field, so `form.to_values_dict()` won't surface it.

### 10. Alumno-facing preview panel (intake view)

Above the form, render `templates/solicitudes/intake/_solicitante_panel.html`:

```django
{% if auto_fill_resolved %}
<aside class="card mb-3" aria-label="Datos del solicitante">
  <div class="card-body">
    <h2 class="h6 mb-3">Datos del solicitante</h2>
    <p class="form-text mb-3">
      Estos datos se incluirán automáticamente en tu solicitud.
      Si están desactualizados, contacta a Control Escolar.
    </p>
    <dl class="row mb-0">
      {% for label, value in auto_fill_resolved %}
        <dt class="col-sm-4">{{ label }}</dt>
        <dd class="col-sm-8">{{ value|default:"—" }}</dd>
      {% endfor %}
    </dl>
  </div>
</aside>
{% endif %}
```

The view computes `auto_fill_resolved` via the same resolver used at submit time, displaying `(snapshot field label, resolved value)` pairs. If the resolver raises `AutoFillRequiredFieldMissing` at preview time, render the page with a top-of-page alert ("No pudimos cargar tus datos del SIGA — intenta de nuevo o contacta a Control Escolar") and disable the submit button. This mirrors the submit-time failure but surfaces it earlier.

### 11. Catalog admin live-preview (003 update)

In `static/js/tipo_form.js` `renderField`, when the row's `source` is not `USER_INPUT`, render a faux pill instead of an interactive control:

```js
if (state.source && state.source !== "USER_INPUT") {
  const pill = document.createElement("span");
  pill.className = "badge text-bg-light border me-2";
  pill.textContent = `Auto · ${state.source.replace("USER_", "").toLowerCase()}`;
  wrap.appendChild(pill);
  return wrap;  // skip the usual control rendering
}
```

`readRowState` gains a `source` field reading `select[name$="-source"]`.

### 12. Failure semantics

- **At catalog admin time**: a `source != USER_INPUT` on an incompatible `field_type` is rejected by both the form `clean()` (auto-resets to `USER_INPUT`) and the schema validator (defense in depth).
- **At intake preview**: if `AutoFillRequiredFieldMissing` is raised, the page renders with the alert + disabled submit; the alumno cannot submit until SIGA recovers.
- **At intake submission**: same exception → 422 + flash message → re-render the form with the alert. No partial save.
- **Stale cache vs. fresh SIGA**: at submission, we always re-hydrate via `UserService.hydrate_from_siga`. If SIGA returns fresh data, that wins over cached values; if SIGA fails, the cached UserDTO is what gets used. (This matches the contract already in 002.)

### 13. SIGA shape assumption

`SigaProfile` today is alumno-shaped (`matricula`, `email`, `full_name`, `programa`, `semestre`). For docente flows we don't yet have a confirmed shape — that's deferred. See OQ-011-2.

### 14. Files added / modified (high-level)

```
solicitudes/
├── models/field_definition.py             [MOD]  + source column
├── migrations/0005_fielddefinition_source.py [NEW]
├── tipos/
│   ├── constants.py                       [MOD]  + FieldSource enum + ALLOWED map
│   ├── schemas.py                         [MOD]  + source on DTO + Input + validator
│   ├── repositories/tipo/implementation.py [MOD] + source on read/write
│   ├── services/tipo_service/implementation.py [MOD] + source on snapshot
│   ├── forms/field_form.py                [MOD]  + source field + clean normalization
│   ├── views/_helpers.py                  [MOD]  + source forwarded
│   └── tests/                             [MOD]  + source tests
├── formularios/
│   ├── schemas.py                         [MOD]  + source on FieldSnapshot
│   └── builder.py                         [MOD]  skip USER_* fields
├── intake/                                [NEW—built by 004; this initiative adds]
│   ├── services/auto_fill_resolver/
│   │   ├── interface.py
│   │   └── implementation.py
│   ├── exceptions.py                      [MOD]  + AutoFillRequiredFieldMissing
│   └── tests/test_auto_fill_resolver.py   [NEW]
└── templates/
    ├── solicitudes/admin/tipos/_field_row.html [MOD] + source dropdown cell
    └── solicitudes/intake/_solicitante_panel.html [NEW]
static/js/tipo_form.js                     [MOD]  + Auto pill in live preview
```

## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)

- Admin POSTs a tipo with `source=USER_PROGRAMA` on a TEXT field → catalog persists the source.
- Admin POSTs a tipo with `source=USER_PROGRAMA` on a SELECT field → form rejects with field-level error pointing at `source`.
- Intake POST with a snapshot containing one `USER_INPUT` and one `USER_PROGRAMA` field → resolver merges; persisted `valores` carries both keys.
- Intake POST where `UserDTO.programa = ""` and the auto-fill field is required → submission fails with `AutoFillRequiredFieldMissing` mapped to a 422 + flash; nothing persisted.
- Intake POST where the client tries to inject a value for an auto-fill `field_id` → that value is dropped (it's not in the built form).

### Browser (Tier 2 — `pytest-playwright`)

- **Admin golden path:** admin opens catalog → adds a TEXT field with source `USER_PROGRAMA` → live preview shows an "Auto · programa" pill instead of a text input → saves → reopens detail → preview still shows the pill.
- **Alumno golden path:** alumno opens an intake page for a tipo with one `USER_INPUT` and one `USER_PROGRAMA` field → "Datos del solicitante" panel lists `Programa: <value>` → fills the input field → submits → confirmation page shows both values in the rendered solicitud.

## Acceptance Criteria

- [ ] `FieldDefinition.source` persists with `USER_INPUT` default; legacy migration is additive and reversible.
- [ ] `CreateFieldInput` rejects sources that are incompatible with the field type (`SELECT`, `FILE`, `DATE`, `TEXTAREA` cannot have `USER_*` sources).
- [ ] Catalog admin can pick a source from a dropdown; the cell is hidden for incompatible types via `data-shows-for`.
- [ ] Catalog live preview renders auto-fill fields as a non-editable pill ("Auto · programa") instead of an input.
- [ ] `build_django_form` excludes `source != USER_INPUT` fields from the constructed Django form.
- [ ] Intake's `AutoFillResolver` produces `{field_id: value}` from a `UserDTO` for all auto-fill fields; raises `AutoFillRequiredFieldMissing` if any required auto-fill field has an empty resolved value.
- [ ] Intake page shows "Datos del solicitante" panel with the resolved values; the panel is the alumno's only view of those fields.
- [ ] Intake submission fails fast (no partial save) when `AutoFillRequiredFieldMissing` fires; the alumno sees a clear error pointing to Control Escolar.
- [ ] An attempt to inject client-side values for auto-fill field ids is silently dropped — only the backend's resolved values land in `valores`.
- [ ] PDF (006, when it lands) sees no difference: auto-fill values appear in `valores` exactly like alumno-typed values.
- [ ] Tests: schema (3+), repository round-trip, builder skip, resolver (success + missing + drop-injection), intake view path. Coverage targets unchanged from 003 (services ≥ 95%, repository ≥ 95%, views ≥ 80%, forms 100%, builder ≥ 95%).

## Open Questions

- **OQ-011-1** — Should the alumno's "Datos del solicitante" panel offer a "refrescar" link that re-hydrates SIGA on demand if a value looks stale? Current default: no — the panel always reflects the latest `UserService.hydrate_from_siga` call, refreshed on every page load. Revisit if alumnos report stale values.
- **OQ-011-2** — `SigaProfile` is alumno-shaped today. When docente flows surface, we'll need to extend the DTO (`departamento`, `categoria`, etc.) and add new variants to `FieldSource` (`USER_DEPARTAMENTO`, …). The admin UI should filter source choices by `creator_roles` so docente-only sources don't appear on alumno-only tipos. Punted to whichever initiative first needs a docente auto-fill field.
- **OQ-011-3** — Sequencing: ship 011 as one initiative depending on 004, or split 011a (schema + admin UI + catalog preview) before 004 and 011b (intake integration) after? Default: one initiative, staged inside; revisit if 004 slips.

## Sequencing notes

The order below is the recommended execution sequence inside `/implement`.

1. **Schema layer** (depends only on 003): `FieldSource` constant, model column, migration, DTO/snapshot delta, repository + service propagation, schema validator, form-clean normalization, view helper. Can ship as a coherent first batch even before 004 is started.
2. **Admin UI** (depends on step 1): source dropdown in `_field_row.html`, JS toggle, live-preview "Auto" pill, admin form tests.
3. **Builder skip** (depends on step 1): `build_django_form` excludes `USER_*` fields; builder tests.
4. **Resolver + intake integration** (depends on 004 having shipped intake): `AutoFillResolver` interface + impl, exception, intake-service merge, alumno preview panel, intake view tests.
5. **E2E** (depends on steps 2 + 4).
