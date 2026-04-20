# 011 — Field Auto-fill from User Data — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

### Schema layer (depends only on 003)
- [ ] [P] Add `FieldSource` enum + `FIELD_SOURCE_ALLOWED_TYPES` map in `solicitudes/tipos/constants.py`
- [ ] [P] `FieldDefinition.source` column + migration `0002_fielddefinition_source.py`
- [ ] [P] `FieldDefinitionDTO.source`, `CreateFieldInput.source` + `_check_source_matches_type` validator
- [ ] [P] `FieldSnapshot.source` in `formularios/schemas.py`
- [ ] Repository: `OrmTipoRepository.create` / `_replace_fields` / `_to_dto` carry `source`
- [ ] Service: `DefaultTipoService.snapshot` carries `source`
- [ ] View helper `_collect_fields` forwards `source`

### Admin form + UI (depends on schema layer)
- [ ] [P] `FieldForm.source` field + `clean()` normalization (reset to `USER_INPUT` on incompatible type)
- [ ] [P] `_field_row.html` adds source dropdown cell with `data-shows-for="TEXT,NUMBER"`
- [ ] [P] Form unit tests: round-trip, type-mismatch normalization, accept on TEXT/NUMBER, reject elsewhere
- [ ] `tipo_form.js` `renderField` renders an "Auto · <source>" pill instead of a control when `source !== USER_INPUT`
- [ ] `tipo_form.js` `readRowState` reads `select[name$="-source"]`

### Builder change (depends on schema layer)
- [ ] `build_django_form` excludes fields with `source != USER_INPUT`
- [ ] Builder unit tests: snapshot with mixed sources renders only USER_INPUT fields; `field_order` reflects only those

### Resolver + intake integration (depends on 004 + schema layer)
- [ ] `solicitudes/intake/services/auto_fill_resolver/interface.py`
- [ ] `solicitudes/intake/services/auto_fill_resolver/implementation.py` (`DefaultAutoFillResolver` injected with `UserService`)
- [ ] `solicitudes/intake/exceptions.py` adds `AutoFillRequiredFieldMissing`
- [ ] `solicitudes/intake/dependencies.py` wires the resolver
- [ ] Resolver unit tests with in-memory fake `UserService`: success path, required-missing → raises, optional-missing → empty value, malicious-injection drop
- [ ] Intake view computes `auto_fill_resolved` for the preview panel; on `AutoFillRequiredFieldMissing` renders alert + disables submit
- [ ] Intake submission merges `auto_values` into `valores` after `form.is_valid()` (auto-fill values bypass the form factory; client-supplied values for those field_ids are dropped)
- [ ] `templates/solicitudes/intake/_solicitante_panel.html` renders the read-only panel above the form

### Tests
- [ ] Schema: source-on-incompatible-type rejected; source-on-compatible-type accepted; default = USER_INPUT
- [ ] Repository: round-trip `source` on create + update + read
- [ ] Form: per-type normalization
- [ ] Builder: skip USER_* fields; user-input-only field_order
- [ ] Resolver: 4+ tests as above
- [ ] Intake view: preview panel renders; missing-required-auto-fill blocks submit; client injection on auto-fill ids is silently dropped

### Quality gates
- [ ] `ruff` + `mypy --strict` clean across `solicitudes/`
- [ ] `python manage.py check` clean
- [ ] Coverage targets met (services ≥ 95%, repository ≥ 95%, views ≥ 80%, forms 100%, builder ≥ 95%)

### E2E
- [ ] Tier 1 (Client): admin POSTs tipo with `source=USER_PROGRAMA` on TEXT → persists
- [ ] Tier 1 (Client): admin POSTs tipo with `source=USER_PROGRAMA` on SELECT → field-level error
- [ ] Tier 1 (Client): intake POST with one USER_INPUT + one USER_PROGRAMA field → both keys in persisted valores
- [ ] Tier 1 (Client): intake POST when `UserDTO.programa=""` and auto-fill field is required → 422 + nothing persisted
- [ ] Tier 1 (Client): intake POST tries to inject a value on an auto-fill field_id → injection dropped, backend value used
- [ ] Tier 2 (Playwright): admin golden path — declares an auto-fill TEXT field, sees "Auto" pill in live preview, saves, reopens detail
- [ ] Tier 2 (Playwright): alumno golden path — sees "Datos del solicitante" panel with resolved values, fills only USER_INPUT fields, submits, confirmation shows both kinds of values

## Blockers

- **004 (Solicitud Lifecycle)** must ship `solicitudes/intake/` (intake view + service + dependencies) before the *Resolver + intake integration* section can start. Schema/Admin UI/Builder sections do not block on 004 and can land first.

[P] = can run in parallel
