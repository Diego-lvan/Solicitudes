# 005 — File Management — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

### Model & migration
- [ ] `models/archivo_solicitud.py` (with kind constraint, partial unique indexes)
- [ ] `ArchivoKind` enum
- [ ] Migration applies cleanly

### Schemas & exceptions
- [ ] [P] `archivos/schemas.py` (`ArchivoDTO`)
- [ ] [P] `archivos/exceptions.py` (ArchivoNotFound, FileTooLarge, FileExtensionNotAllowed)

### Storage
- [ ] `archivos/storage/interface.py`
- [ ] `archivos/storage/local.py` (`LocalFileStorage`) + tests using `tmp_path`
- [ ] On-rollback cleanup hook (transaction.on_commit / on_rollback equivalent)

### Repository
- [ ] `archivos/repositories/archivo/{interface,implementation}.py` + tests

### Service
- [ ] `archivos/services/archivo_service/{interface,implementation}.py`
- [ ] Validation: extension whitelist per field, size ceiling, comprobante rules
- [ ] Authz in `open_for_download`
- [ ] Tests with fake `FileStorage` and in-memory repo

### Views & wiring
- [ ] `archivos/views/download.py` + tests (auth matrix)
- [ ] `archivos/urls.py` mounted under `solicitudes/archivos/`
- [ ] `archivos/dependencies.py`

### Integration into intake
- [ ] Replace 004's NoOp file handling in `intake/views/create.py`
- [ ] Verify atomic rollback: induce failure, assert no orphan files

### Templates
- [ ] [P] `templates/solicitudes/_partials/_archivos.html`
- [ ] Include partial in intake/detail.html and revision/detail.html

### End-to-end smoke
- [ ] Alumno creates with .pdf + .zip + comprobante → all stored and downloadable
- [ ] Wrong extension → 422 + form re-render with field error
- [ ] Non-owner non-personal hits download URL → 403
- [ ] Force a DB error after file write → file deleted (no orphan in `media/`)

### Quality gates
- [ ] `ruff` + `mypy` clean
- [ ] `pytest` green; coverage targets met


### E2E
- [ ] Tier 1 (Client multi-step): Cross-feature: alumno submits intake with FORM attachments and a comprobante → archivos persisted under `media/solicitudes/<folio>/` → owner download OK, unrelated user 403.
- [ ] Tier 1 (Client multi-step): Failure path: induce a DB error after the file write → transaction rolls back and the file is removed (no orphans).
- [ ] Tier 2 (browser/Playwright): Golden path: alumno attaches a real PDF, sees it listed on the detail page, downloads it.

## Blockers

None (depends on 003 + 004).

## Legend

- `[P]` = parallelizable with siblings in the same section
