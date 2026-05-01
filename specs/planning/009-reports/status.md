# 009 — Reports & Dashboard — Status

**Status:** Done
**Last updated:** 2026-04-26

## Checklist

### App skeleton
- [x] Create `reportes/` package + `apps.py`
- [x] Register in `INSTALLED_APPS`

### Schemas, exceptions
- [x] [P] `schemas.py` (ReportFilter, CountByEstado, CountByTipo, CountByMonth, DashboardData)
- [x] [P] ~~`exceptions.py`~~ — dropped (no feature exception was actually raised; filter parser silently coerces invalid input by design)

### Repository extension (solicitudes)
- [x] Add aggregate methods to `OrmSolicitudRepository.aggregate_by_*`
- [x] Tests assert single-query behavior (`django_assert_num_queries`)

### LifecycleService extension
- [x] Add aggregate methods to interface + impl + tests (additive, no breaking change)

### Services (reportes)
- [x] `services/report_service/{interface,implementation}.py` + tests (uses fakes)
- [x] `services/export_service/interface.py`
- [x] `services/export_service/csv_implementation.py` + tests (UTF-8 BOM, streaming)
- [x] `services/export_service/pdf_implementation.py` + tests (smoke: %PDF prefix)
- [x] `dependencies.py`

### Forms & views
- [x] [P] `forms/report_filter_form.py` + tests
- [x] [P] `views/dashboard.py` + tests (admin-only, query count)
- [x] [P] `views/list.py` + tests
- [x] [P] `views/export_csv.py` + tests
- [x] [P] `views/export_pdf.py` + tests
- [x] `urls.py`, mounted in `config/urls.py`

### Templates
- [x] [P] `templates/reportes/dashboard.html`
- [x] [P] `templates/reportes/list.html`
- [x] [P] `templates/reportes/_filter_form.html`
- [x] [P] `templates/reportes/export_pdf.html`

### End-to-end smoke
- [x] Seed 30 solicitudes (mix of tipos, estados, dates) → dashboard counts match hand calc *(covered by Tier 1 view tests)*
- [x] CSV export via Excel: opens cleanly, columns aligned, accents preserved *(BOM + accent round-trip test)*
- [x] PDF export with 100-row fixture: renders, looks decent *(smoke + browser screenshot)*
- [x] Non-admin → 403

### Quality gates
- [x] `ruff` clean (mypy not part of CI yet for this initiative)
- [x] `pytest` green; 385 passed (377 unit/integration + 8 reportes-only) and Tier 2 E2E passes


### E2E
- [x] Tier 1 (Client multi-step): Cross-feature: fixture of N solicitudes → admin hits `/reportes/` → counts in `DashboardData` match a hand-computed aggregate; date-range filter narrows correctly.
- [x] Tier 1 (Client multi-step): Cross-feature: admin hits `/reportes/exportar/csv/` → `Content-Type: text/csv`, UTF-8 BOM, rows match filter, accents preserved.
- [x] Tier 1 (Client multi-step): Negative: non-admin → 403 via `_shared/error.html`.
- [x] Tier 2 (browser/Playwright): Golden path: admin opens dashboard, applies a filter, exports CSV (browser; assert download).

## Blockers

None (depends on 001 + 002 + 004).

## Legend

- `[P]` = parallelizable with siblings in the same section
