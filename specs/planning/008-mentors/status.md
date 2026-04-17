# 008 — Mentors — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

### App skeleton
- [ ] Create `apps/mentores/` package + `apps.py`
- [ ] Register in `INSTALLED_APPS`

### Model & migration
- [ ] `models/mentor.py`
- [ ] `MentorSource` enum
- [ ] Migration applies cleanly

### Schemas, exceptions
- [ ] [P] `schemas.py` (MentorDTO, CsvImportResult)
- [ ] [P] `exceptions.py` (MentorNotFound, MentorAlreadyActive, CsvParseError)

### Repository
- [ ] `repositories/mentor/{interface,implementation}.py` + tests (incl. `exists_active` hot path)

### Services
- [ ] `services/mentor_service/{interface,implementation}.py` + tests
- [ ] `services/csv_importer/{interface,implementation}.py` + tests (multiple fixtures: clean, bad header, bad rows mixed)
- [ ] `dependencies.py`

### Forms & views
- [ ] [P] `forms/add_mentor_form.py`
- [ ] [P] `forms/csv_import_form.py`
- [ ] [P] `views/list.py` + tests
- [ ] [P] `views/add.py` + tests
- [ ] [P] `views/deactivate.py` + tests
- [ ] [P] `views/import_csv.py` + tests
- [ ] `urls.py` + mount in `config/urls.py`
- [ ] [P] `templates/mentores/list.html`
- [ ] [P] `templates/mentores/add.html`
- [ ] [P] `templates/mentores/import_csv.html`
- [ ] [P] `templates/mentores/import_result.html`
- [ ] [P] `templates/mentores/confirm_deactivate.html`

### Cross-app wiring
- [ ] Replace `FalseMentorService` in `apps/solicitudes/intake/dependencies.py`
- [ ] Verify intake form behavior: mentor + mentor_exempt tipo → no comprobante; non-mentor + mentor_exempt → comprobante required

### End-to-end smoke
- [ ] CSV import 100 rows → result counts add up; invalid rows surfaced
- [ ] Manual add duplicates → 409 with friendly error
- [ ] Reactivate a deactivated matricula via CSV → counts as `reactivated`

### Quality gates
- [ ] `ruff` + `mypy` clean
- [ ] `pytest` green; coverage targets met


### E2E
- [ ] Tier 1 (Client multi-step): Cross-feature: admin adds matricula `M` as mentor → alumno `M` intakes a `mentor_exempt` tipo → no comprobante in the form → `Solicitud.pago_exento == True`.
- [ ] Tier 1 (Client multi-step): Cross-feature: non-mentor alumno intakes the same tipo → comprobante required; submitting without it returns `comprobante_required`.
- [ ] Tier 1 (Client multi-step): Cross-feature: admin deactivates mentor `M` → new solicitud requires comprobante; older solicitudes keep `pago_exento=True` (snapshot integrity).
- [ ] Tier 2 (browser/Playwright): Golden path: admin imports a CSV of mentor matrículas via the upload form; success page shows counts; list shows entries.
- [ ] Tier 2 (browser/Playwright): Golden path: admin deactivates a mentor from the list view (browser).

## Blockers

None (depends on 002 + 004).

## Legend

- `[P]` = parallelizable with siblings in the same section
