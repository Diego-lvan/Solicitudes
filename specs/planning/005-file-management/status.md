# 005 — File Management — Status

**Status:** Done
**Last updated:** 2026-04-26

## Checklist

### Model & migration
- [x] `models/archivo_solicitud.py` (with kind constraint, partial unique indexes)
- [x] `ArchivoKind` enum
- [x] Migration applies cleanly

### Schemas & exceptions
- [x] [P] `archivos/schemas.py` (`ArchivoDTO`)
- [x] [P] `archivos/exceptions.py` (ArchivoNotFound, FileTooLarge, FileExtensionNotAllowed)

### Storage
- [x] `archivos/storage/interface.py`
- [x] `archivos/storage/local.py` (`LocalFileStorage`) + tests using `tmp_path`
- [x] On-rollback cleanup hook (transaction.on_commit / on_rollback equivalent)

### Repository
- [x] `archivos/repositories/archivo/{interface,implementation}.py` + tests

### Service
- [x] `archivos/services/archivo_service/{interface,implementation}.py`
- [x] Validation: extension whitelist per field, size ceiling, comprobante rules
- [x] Authz in `open_for_download`
- [x] Tests with fake `FileStorage` and in-memory repo

### Views & wiring
- [x] `archivos/views/download.py` + tests (auth matrix)
- [x] `archivos/urls.py` mounted under `solicitudes/archivos/`
- [x] `archivos/dependencies.py`

### Integration into intake
- [x] Replace 004's NoOp file handling in `intake/views/create.py`
- [x] Verify atomic rollback: induce failure, assert no orphan files

### Templates
- [x] [P] `templates/solicitudes/_partials/_archivos.html`
- [x] Include partial in intake/detail.html and revision/detail.html

### End-to-end smoke
- [x] Alumno creates with .pdf + .zip + comprobante → all stored and downloadable
- [x] Wrong extension → 422 + form re-render with field error
- [x] Non-owner non-personal hits download URL → 403
- [x] Force a DB error after file write → file deleted (no orphan in `media/`)

### Quality gates
- [x] `ruff` + `mypy` clean
- [x] `pytest` green; coverage targets met


### E2E
- [x] Tier 1 (Client multi-step): Cross-feature: alumno submits intake with FORM attachments and a comprobante → archivos persisted under `media/solicitudes/<folio>/` → owner download OK, unrelated user 403.
- [x] Tier 1 (Client multi-step): Failure path: induce a DB error after the file write → transaction rolls back and the file is removed (no orphans).
- [x] Tier 2 (browser/Playwright): Golden path: alumno attaches a real PDF, sees it listed on the detail page, downloads it.

## Blockers

None (depends on 003 + 004).

## Legend

- `[P]` = parallelizable with siblings in the same section
