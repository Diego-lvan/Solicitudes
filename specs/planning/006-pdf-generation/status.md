# 006 — PDF Generation — Status

**Status:** Done
**Last updated:** 2026-04-26

## Checklist

### Model & migration
- [x] `models/plantilla.py` (`PlantillaSolicitud`)
- [x] Migration: convert `tipo.plantilla_id` UUIDField → FK to PlantillaSolicitud (nullable)

### Schemas & exceptions
- [x] [P] `pdf/schemas.py` (PlantillaDTO, Create/UpdatePlantillaInput, PdfRenderResult)
- [x] [P] `pdf/exceptions.py` (PlantillaNotFound, PlantillaTemplateError, TipoHasNoPlantilla)

### Plantilla CRUD
- [x] `pdf/repositories/plantilla/{interface,implementation}.py` + tests
- [x] `pdf/services/plantilla_service/{interface,implementation}.py` + tests (template parse validation at save)
- [x] [P] `pdf/forms/plantilla_form.py`
- [x] [P] `pdf/views/{list,create,detail,edit,delete}.py` + tests (admin only)
- [x] [P] `templates/solicitudes/admin/plantillas/{list,form,detail,confirm_deactivate}.html`

### PDF rendering
- [x] `pdf/services/pdf_service/{interface,implementation}.py`
- [x] Variable-resolution helper (slugify labels, build context) → `pdf/context.py`
- [x] Tests: render context completeness, byte-identical re-render under frozen clock
- [x] `pdf/views/download.py` + tests (authz matrix, no-plantilla → 409)
- [x] `pdf/urls.py`, `pdf/dependencies.py`

### Hookups
- [x] Add plantilla `<select>` to `tipos/forms/tipo_form.py` (also wired through `_helpers.py` build_*_input)
- [x] Add "Generar PDF" link in `templates/solicitudes/revision/detail.html` and (post-finalización) `intake/detail.html`

### End-to-end smoke
- [x] Admin creates plantilla "Constancia de Estudios" (verified live in dev stack)
- [x] Admin attaches plantilla to tipo
- [x] Alumno creates solicitud, personal finalizes, alumno downloads PDF (live curl + browser fetch returned 7.4 KB %PDF)
- [x] Tipo without plantilla → no "Generar PDF" link rendered (template guards on `detail.tipo.plantilla_id`)

### Quality gates
- [x] `ruff` + `mypy` clean
- [x] `pytest` green; coverage targets met (402/402, 22 new pdf-feature tests)
- [x] WeasyPrint smoke test still green


### E2E
- [x] Tier 1 (Client multi-step): Cross-feature: solicitud reaches `FINALIZADA` (tipo with plantilla) → personal triggers PDF render → solicitante downloads (`Content-Type: application/pdf`, bytes start with `%PDF`, non-zero length). → covered by `pdf/tests/test_views.py::test_owner_downloads_pdf_when_finalizada` and `test_personal_can_download_at_any_estado`.
- [x] Tier 1 (Client multi-step): Negative: tipo with `plantilla_id=None` → 409 `tipo_has_no_plantilla`. → `pdf/tests/test_views.py::test_no_plantilla_returns_409`.
- [ ] Tier 2 (browser/Playwright): Golden path: personal generates the PDF from the revision detail page; solicitante downloads it from their list of solicitudes finalizadas. → deferred (Tier 2 stack pre-existing browser-install gap; manually verified golden path via dev stack and Playwright MCP — screenshots at `/tmp/006-screenshots/`).

## Blockers

None (depends on 001 + 003 + 004).

## Legend

- `[P]` = parallelizable with siblings in the same section
