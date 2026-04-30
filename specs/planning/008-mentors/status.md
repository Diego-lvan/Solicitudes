# 008 — Mentors — Status

**Status:** Implementation complete (pending user review)
**Last updated:** 2026-04-25

## Checklist

### App skeleton
- [x] Create `mentores/` package + `apps.py`
- [x] Register in `INSTALLED_APPS`

### Model & migration
- [x] `models/mentor.py`
- [x] `MentorSource` enum
- [x] Migration applies cleanly

### Schemas, exceptions
- [x] [P] `schemas.py` (MentorDTO, CsvImportResult)
- [x] [P] `exceptions.py` (MentorNotFound, MentorAlreadyActive, CsvParseError)

### Repository
- [x] `repositories/mentor/{interface,implementation}.py` + tests (incl. `exists_active` hot path)

### Services
- [x] `services/mentor_service/{interface,implementation}.py` + tests
- [x] `services/csv_importer/{interface,implementation}.py` + tests (multiple fixtures: clean, bad header, bad rows mixed)
- [x] `dependencies.py`

### Forms & views
- [x] [P] `forms/add_mentor_form.py`
- [x] [P] `forms/csv_import_form.py`
- [x] [P] `views/list.py` + tests
- [x] [P] `views/add.py` + tests
- [x] [P] `views/deactivate.py` + tests
- [x] [P] `views/import_csv.py` + tests
- [x] `urls.py` + mount in `config/urls.py`
- [x] [P] `templates/mentores/list.html`
- [x] [P] `templates/mentores/add.html`
- [x] [P] `templates/mentores/import_csv.html`
- [x] [P] `templates/mentores/import_result.html`
- [x] [P] `templates/mentores/confirm_deactivate.html`

### Cross-app wiring
- [x] Replace `FalseMentorService` in `solicitudes/intake/dependencies.py`
- [x] Verify intake form behavior: mentor + mentor_exempt tipo → no comprobante; non-mentor + mentor_exempt → comprobante required

### End-to-end smoke
- [x] CSV import 100 rows → result counts add up; invalid rows surfaced
- [x] Manual add duplicates → 409 with friendly error
- [x] Reactivate a deactivated matricula via CSV → counts as `reactivated`

### Quality gates
- [x] `ruff` + `mypy` clean
- [x] `pytest` green; coverage targets met (mentores total 98%; services 100%, repo 100%, views ≥88%)


### E2E
- [x] Tier 1 (Client multi-step): Cross-feature: admin adds matricula `M` as mentor → alumno `M` intakes a `mentor_exempt` tipo → no comprobante in the form → `Solicitud.pago_exento == True`.
- [x] Tier 1 (Client multi-step): Cross-feature: non-mentor alumno intakes the same tipo → comprobante required; submitting without it returns `comprobante_required`.
- [x] Tier 1 (Client multi-step): Cross-feature: admin deactivates mentor `M` → new solicitud requires comprobante; older solicitudes keep `pago_exento=True` (snapshot integrity).
- [x] Tier 2 (browser/Playwright): Golden path: admin imports a CSV of mentor matrículas via the upload form; success page shows counts; list shows entries.
- [x] Tier 2 (browser/Playwright): Golden path: admin deactivates a mentor from the list view (browser).

## Blockers

None (depends on 002 + 004).

## Merge-back ordering (worktree note)

This branch (`feat/008-mentors`) is being built in parallel with initiative 004 in a separate worktree. The `mentores/` app is fully self-contained and can be built end-to-end without 004. **However**, the following sections in this checklist depend on `solicitudes/intake/` (created by 004) and MUST be deferred until 004 lands on `main` and this branch is rebased on top:

- **Cross-app wiring** — both items (replacing `FalseMentorService` in `solicitudes/intake/dependencies.py`; verifying intake form behavior).
- **End-to-end smoke** — the three scenarios all touch the intake form.
- **E2E** — all five tasks (Tier 1 + Tier 2) are cross-feature with intake.

**Order of operations when 004 merges:**
1. Rebase `feat/008-mentors` onto the new `main`.
2. Re-run quality gates (`ruff`, `mypy`, `pytest`) to confirm nothing regressed.
3. Execute the Cross-app wiring + End-to-end smoke + E2E sections above.
4. Flip `roadmap.md` 008 → `Done` only after `/review` passes (per closeout convention).

## Legend

- `[P]` = parallelizable with siblings in the same section
