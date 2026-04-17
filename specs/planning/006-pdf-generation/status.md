# 006 — PDF Generation — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

### Model & migration
- [ ] `models/plantilla.py` (`PlantillaSolicitud`)
- [ ] Migration: convert `tipo.plantilla_id` UUIDField → FK to PlantillaSolicitud (nullable)

### Schemas & exceptions
- [ ] [P] `pdf/schemas.py` (PlantillaDTO, Create/UpdatePlantillaInput, PdfRenderResult)
- [ ] [P] `pdf/exceptions.py` (PlantillaNotFound, PlantillaTemplateError, TipoHasNoPlantilla)

### Plantilla CRUD
- [ ] `pdf/repositories/plantilla/{interface,implementation}.py` + tests
- [ ] `pdf/services/plantilla_service/{interface,implementation}.py` + tests (template parse validation at save)
- [ ] [P] `pdf/forms/plantilla_form.py`
- [ ] [P] `pdf/views/{list,create,detail,edit}.py` + tests (admin only)
- [ ] [P] `templates/solicitudes/admin/plantillas/{list,form,detail}.html`

### PDF rendering
- [ ] `pdf/services/pdf_service/{interface,implementation}.py`
- [ ] Variable-resolution helper (slugify labels, build context)
- [ ] Tests: render context completeness, byte-identical re-render under frozen clock
- [ ] `pdf/views/download.py` + tests (authz matrix, no-plantilla → 409)
- [ ] `pdf/urls.py`, `pdf/dependencies.py`

### Hookups
- [ ] Add plantilla `<select>` to `tipos/forms/tipo_form.py`
- [ ] Add "Generar PDF" link in `templates/solicitudes/revision/detail.html` and (post-finalización) `intake/detail.html`

### End-to-end smoke
- [ ] Admin creates plantilla "Constancia de Estudios"
- [ ] Admin attaches plantilla to tipo
- [ ] Alumno creates solicitud, personal finalizes, alumno downloads PDF
- [ ] Tipo without plantilla → no "Generar PDF" link rendered

### Quality gates
- [ ] `ruff` + `mypy` clean
- [ ] `pytest` green; coverage targets met
- [ ] WeasyPrint smoke test still green


### E2E
- [ ] Tier 1 (Client multi-step): Cross-feature: solicitud reaches `FINALIZADA` (tipo with plantilla) → personal triggers PDF render → solicitante downloads (`Content-Type: application/pdf`, bytes start with `%PDF`, non-zero length).
- [ ] Tier 1 (Client multi-step): Negative: tipo with `plantilla_id=None` → 409 `tipo_has_no_plantilla`.
- [ ] Tier 2 (browser/Playwright): Golden path: personal generates the PDF from the revision detail page; solicitante downloads it from their list of solicitudes finalizadas.

## Blockers

None (depends on 001 + 003 + 004).

## Legend

- `[P]` = parallelizable with siblings in the same section
