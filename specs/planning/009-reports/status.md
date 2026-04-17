# 009 — Reports & Dashboard — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

### App skeleton
- [ ] Create `apps/reportes/` package + `apps.py`
- [ ] Register in `INSTALLED_APPS`

### Schemas, exceptions
- [ ] [P] `schemas.py` (ReportFilter, CountByEstado, CountByTipo, CountByMonth, DashboardData)
- [ ] [P] `exceptions.py` (placeholders if any)

### Repository extension (apps/solicitudes)
- [ ] Add aggregate methods to `OrmSolicitudRepository.aggregate_by_*`
- [ ] Tests assert single-query behavior (`django_assert_num_queries`)

### LifecycleService extension
- [ ] Add aggregate methods to interface + impl + tests (additive, no breaking change)

### Services (apps/reportes)
- [ ] `services/report_service/{interface,implementation}.py` + tests (uses fakes)
- [ ] `services/export_service/interface.py`
- [ ] `services/export_service/csv_implementation.py` + tests (UTF-8 BOM, streaming)
- [ ] `services/export_service/pdf_implementation.py` + tests (smoke: %PDF prefix)
- [ ] `dependencies.py`

### Forms & views
- [ ] [P] `forms/report_filter_form.py` + tests
- [ ] [P] `views/dashboard.py` + tests (admin-only, query count)
- [ ] [P] `views/list.py` + tests
- [ ] [P] `views/export_csv.py` + tests
- [ ] [P] `views/export_pdf.py` + tests
- [ ] `urls.py`, mounted in `config/urls.py`

### Templates
- [ ] [P] `templates/reportes/dashboard.html`
- [ ] [P] `templates/reportes/list.html`
- [ ] [P] `templates/reportes/_filter_form.html`
- [ ] [P] `templates/reportes/export_pdf.html`

### End-to-end smoke
- [ ] Seed 30 solicitudes (mix of tipos, estados, dates) → dashboard counts match hand calc
- [ ] CSV export via Excel: opens cleanly, columns aligned, accents preserved
- [ ] PDF export with 100-row fixture: renders, looks decent
- [ ] Non-admin → 403

### Quality gates
- [ ] `ruff` + `mypy` clean
- [ ] `pytest` green; coverage targets met


### E2E
- [ ] Tier 1 (Client multi-step): Cross-feature: fixture of N solicitudes → admin hits `/reportes/` → counts in `DashboardData` match a hand-computed aggregate; date-range filter narrows correctly.
- [ ] Tier 1 (Client multi-step): Cross-feature: admin hits `/reportes/exportar/csv/` → `Content-Type: text/csv`, UTF-8 BOM, rows match filter, accents preserved.
- [ ] Tier 1 (Client multi-step): Negative: non-admin → 403 via `_shared/error.html`.
- [ ] Tier 2 (browser/Playwright): Golden path: admin opens dashboard, applies a filter, exports CSV (browser; assert download).

## Blockers

None (depends on 001 + 002 + 004).

## Legend

- `[P]` = parallelizable with siblings in the same section
