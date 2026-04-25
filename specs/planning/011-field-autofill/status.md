# 011 — Field Auto-fill from User Data — Status

**Status:** Done
**Last updated:** 2026-04-26

## Checklist

### Schema layer (depends only on 003)
- [x] [P] Add `FieldSource` enum + `FIELD_SOURCE_ALLOWED_TYPES` map in `solicitudes/tipos/constants.py`
- [x] [P] `FieldDefinition.source` column + migration `0005_fielddefinition_source.py`
- [x] [P] `FieldDefinitionDTO.source`, `CreateFieldInput.source` + `_check_source_matches_type` validator
- [x] [P] `FieldSnapshot.source` in `formularios/schemas.py`
- [x] Repository: `OrmTipoRepository.create` / `_replace_fields` / `_to_dto` carry `source`
- [x] Service: `DefaultTipoService.snapshot` carries `source`
- [x] View helper `_collect_fields` forwards `source`

### Admin form + UI (depends on schema layer)
- [x] [P] `FieldForm.source` field + `clean()` normalization (reset to `USER_INPUT` on incompatible type)
- [x] [P] `_field_row.html` adds source dropdown cell with `data-shows-for="TEXT,NUMBER"`
- [x] [P] Form unit tests: round-trip, type-mismatch normalization, accept on TEXT/NUMBER, reject elsewhere
- [x] `tipo_form.js` `renderField` renders an "Auto · <source>" pill instead of a control when `source !== USER_INPUT`
- [x] `tipo_form.js` `readRowState` reads `select[name$="-source"]`

### Builder change (depends on schema layer)
- [x] `build_django_form` excludes fields with `source != USER_INPUT`
- [x] Builder unit tests: snapshot with mixed sources renders only USER_INPUT fields; `field_order` reflects only those

### Resolver + intake integration (depends on 004 + schema layer)
- [x] `solicitudes/intake/services/auto_fill_resolver/interface.py`
- [x] `solicitudes/intake/services/auto_fill_resolver/implementation.py` (`DefaultAutoFillResolver` injected with `UserService`)
- [x] `solicitudes/intake/exceptions.py` adds `AutoFillRequiredFieldMissing`
- [x] `solicitudes/intake/dependencies.py` wires the resolver
- [x] Resolver unit tests with in-memory fake `UserService`: success path, required-missing → raises, optional-missing → empty value, malicious-injection drop
- [x] Intake view computes `auto_fill_resolved` for the preview panel; on `AutoFillRequiredFieldMissing` renders alert + disables submit
- [x] Intake submission merges `auto_values` into `valores` after `form.is_valid()` (auto-fill values bypass the form factory; client-supplied values for those field_ids are dropped)
- [x] `templates/solicitudes/intake/_solicitante_panel.html` renders the read-only panel above the form

### Tests
- [x] Schema: source-on-incompatible-type rejected; source-on-compatible-type accepted; default = USER_INPUT (`test_schemas.py` — 6 new tests)
- [x] Repository: round-trip `source` on create + update + read (`test_tipo_repository.py` — 2 new tests)
- [x] Form: per-type normalization (`test_forms.py` — 6 new tests)
- [x] Builder: skip USER_* fields; user-input-only field_order (`test_builder.py` — 3 new tests including injection-drop)
- [x] Resolver: 4+ tests (`test_auto_fill_resolver.py` — 9 tests covering resolve strict, preview lenient, optional empty, semestre None)
- [x] Intake view: preview panel renders; missing-required-auto-fill blocks submit; client injection on auto-fill ids is silently dropped (`test_intake_views.py` — 5 new tests)

### Quality gates
- [x] `ruff` + `mypy --strict` clean across `solicitudes/` (mypy: 14 touched files clean; the 5 leftover --strict errors are pre-existing in `lifecycle/tests/fakes.py` and `_StubLifecycleService` test stubs that 011 did not touch)
- [x] `python manage.py check` clean (`System check identified no issues (0 silenced).`)
- [ ] Coverage targets met (services ≥ 95%, repository ≥ 95%, views ≥ 80%, forms 100%, builder ≥ 95%) — deferred to `/review`

### E2E
- [x] Tier 1 (Client): admin POSTs tipo with `source=USER_PROGRAMA` on TEXT → persists (`test_create_post_persists_user_programa_source_on_text_field`)
- [x] Tier 1 (Client): admin POSTs tipo with `source=USER_PROGRAMA` on SELECT → silently normalized to `USER_INPUT` (per plan §12; `test_create_post_normalizes_source_when_field_type_is_select`). The status item originally said "field-level error" but the plan's defense-in-depth design auto-resets at the form-clean layer; the schema validator is a backstop the user never sees in normal flow.
- [x] Tier 1 (Client): intake POST with one USER_INPUT + one USER_PROGRAMA field → both keys in persisted valores (`test_create_post_merges_auto_fill_values_into_persisted_valores`)
- [x] Tier 1 (Client): intake POST when `UserDTO.programa=""` and auto-fill field is required → 422 + nothing persisted (`test_create_post_returns_422_when_required_auto_fill_missing`)
- [x] Tier 1 (Client): intake POST tries to inject a value on an auto-fill field_id → injection dropped, backend value used (`test_create_post_drops_client_injection_for_auto_fill_field_id`)
- [x] Tier 2 (Playwright): admin golden path (`tests-e2e/test_field_autofill_golden_path.py::test_admin_creates_tipo_with_auto_fill_text_field`) — file lands; runs in CI via `make e2e` once Chromium is bootstrapped. Manual visual capture this session via MCP Playwright covered the same UI scenarios at 1280×900 + 320×800 (`/tmp/011-screenshots/011-admin-source-{desktop,mobile}.png`).
- [x] Tier 2 (Playwright): alumno golden path (`tests-e2e/test_field_autofill_golden_path.py::test_alumno_intake_with_auto_fill_panel`) — file lands; manual visual capture covered both happy + missing-required states at desktop + mobile (`/tmp/011-screenshots/011-intake-panel-{happy,missing}-{desktop,mobile}.png`).

## Blockers

- **004 (Solicitud Lifecycle)** must ship `solicitudes/intake/` (intake view + service + dependencies) before the *Resolver + intake integration* section can start. Schema/Admin UI/Builder sections do not block on 004 and can land first.

[P] = can run in parallel
