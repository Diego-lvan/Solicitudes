# 003 — Catalog & Dynamic Forms — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

### App skeleton
- [ ] `apps/solicitudes/` package + `apps.py`
- [ ] Register in `INSTALLED_APPS`
- [ ] `apps/solicitudes/urls.py` (mounts admin tipos URL)

### Data models
- [ ] [P] `models/tipo_solicitud.py`
- [ ] [P] `models/field_definition.py`
- [ ] Initial migration; verify constraints (unique slug, unique (tipo, order))

### `tipos/` feature — schemas & exceptions
- [ ] [P] `tipos/constants.py` (`FieldType`)
- [ ] [P] `tipos/exceptions.py` (TipoNotFound, TipoSlugConflict, TipoInUse, InvalidFieldDefinition)
- [ ] [P] `tipos/schemas.py` (DTOs + Pydantic validators)

### Repository
- [ ] `repositories/tipo/interface.py`
- [ ] `repositories/tipo/implementation.py` (`OrmTipoRepository` with prefetch)
- [ ] `tests/test_tipo_repository.py` (real DB, atomic update of fieldset)

### Service
- [ ] `services/tipo_service/interface.py`
- [ ] `services/tipo_service/implementation.py`
- [ ] `tests/fakes.py` (`InMemoryTipoRepository`)
- [ ] `tests/test_tipo_service.py`

### Forms (admin)
- [ ] [P] `forms/tipo_form.py` (metadata)
- [ ] [P] `forms/field_form.py` (single row + formset)
- [ ] [P] `tests/test_forms.py`

### Views & templates
- [ ] [P] `views/list.py` + tests
- [ ] [P] `views/create.py` + tests
- [ ] [P] `views/detail.py` (form preview) + tests
- [ ] [P] `views/edit.py` + tests
- [ ] [P] `views/delete.py` (deactivate) + tests
- [ ] `tipos/urls.py`, `tipos/dependencies.py`
- [ ] [P] `templates/solicitudes/admin/tipos/list.html`
- [ ] [P] `templates/solicitudes/admin/tipos/form.html`
- [ ] [P] `templates/solicitudes/admin/tipos/_field_row.html`
- [ ] [P] `templates/solicitudes/admin/tipos/detail.html`
- [ ] [P] `templates/solicitudes/admin/tipos/confirm_deactivate.html`
- [ ] JS for adding/removing field rows in `static/js/tipo_form.js`

### `formularios/` feature — runtime builder (consumed by 004)
- [ ] [P] `formularios/schemas.py` (`FieldSnapshot`, `FormSnapshot`)
- [ ] [P] `formularios/validators.py` (extension + size validators)
- [ ] `formularios/builder.py`
- [ ] `formularios/tests/test_builder.py`

### End-to-end smoke
- [ ] Admin creates "Constancia de Estudios" with 3 fields → list shows it
- [ ] Detail page renders the dynamic form preview correctly
- [ ] `tipo_service.snapshot(id)` returns matching `FormSnapshot`

### Quality gates
- [ ] `ruff` + `mypy` clean
- [ ] `pytest` green; coverage targets met (services 95%, repo 95%, views 80%, forms 100%)
- [ ] No ORM call in views/services beyond the repository


### E2E
- [ ] Tier 2 (browser/Playwright): Golden path: admin creates a new TipoSolicitud with two FieldDefinitions; lists it; edits it.

## Blockers

None.

## Legend

- `[P]` = parallelizable with siblings in the same section
