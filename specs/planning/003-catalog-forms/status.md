# 003 — Catalog & Dynamic Forms — Status

**Status:** Done
**Last updated:** 2026-04-25

## Checklist

### App skeleton
- [x] `solicitudes/` package + `apps.py`
- [x] Register in `INSTALLED_APPS`
- [x] `solicitudes/urls.py` (mounts admin tipos URL)

### Data models
- [x] [P] `models/tipo_solicitud.py`
- [x] [P] `models/field_definition.py`
- [x] Initial migration; verify constraints (unique slug, unique (tipo, order))

### `tipos/` feature — schemas & exceptions
- [x] [P] `tipos/constants.py` (`FieldType`)
- [x] [P] `tipos/exceptions.py` (TipoNotFound, TipoSlugConflict, TipoInUse, InvalidFieldDefinition)
- [x] [P] `tipos/schemas.py` (DTOs + Pydantic validators)

### Repository
- [x] `repositories/tipo/interface.py`
- [x] `repositories/tipo/implementation.py` (`OrmTipoRepository` with prefetch)
- [x] `tests/test_tipo_repository.py` (real DB, atomic update of fieldset)

### Service
- [x] `services/tipo_service/interface.py`
- [x] `services/tipo_service/implementation.py`
- [x] `tests/fakes.py` (`InMemoryTipoRepository`)
- [x] `tests/test_tipo_service.py`

### Forms (admin)
- [x] [P] `forms/tipo_form.py` (metadata)
- [x] [P] `forms/field_form.py` (single row + formset)
- [x] [P] `tests/test_forms.py`

### Views & templates
- [x] [P] `views/list.py` + tests
- [x] [P] `views/create.py` + tests
- [x] [P] `views/detail.py` (form preview) + tests
- [x] [P] `views/edit.py` + tests
- [x] [P] `views/delete.py` (deactivate) + tests
- [x] `tipos/urls.py`, `tipos/dependencies.py`
- [x] [P] `templates/solicitudes/admin/tipos/list.html`
- [x] [P] `templates/solicitudes/admin/tipos/form.html`
- [x] [P] `templates/solicitudes/admin/tipos/_field_row.html`
- [x] [P] `templates/solicitudes/admin/tipos/detail.html`
- [x] [P] `templates/solicitudes/admin/tipos/confirm_deactivate.html`
- [x] JS for adding/removing field rows in `static/js/tipo_form.js`

### `formularios/` feature — runtime builder (consumed by 004)
- [x] [P] `formularios/schemas.py` (`FieldSnapshot`, `FormSnapshot`)
- [x] [P] `formularios/validators.py` (extension + size validators)
- [x] `formularios/builder.py`
- [x] `formularios/tests/test_builder.py`

### End-to-end smoke
- [x] Admin creates "Constancia de Estudios" with 3 fields → list shows it
- [x] Detail page renders the dynamic form preview correctly
- [x] `tipo_service.snapshot(id)` returns matching `FormSnapshot`

### Quality gates
- [x] `ruff` + `mypy` clean
- [x] `pytest` green; coverage targets met (services 95%, repo 95%, views 80%, forms 100%)
- [x] No ORM call in views/services beyond the repository


### E2E
- [x] Tier 2 (browser/Playwright): Golden path: admin creates a new TipoSolicitud with two FieldDefinitions; lists it; edits it.

## Blockers

None.

## Legend

- `[P]` = parallelizable with siblings in the same section
