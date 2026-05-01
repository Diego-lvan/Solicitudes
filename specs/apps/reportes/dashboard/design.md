# reportes/dashboard — Design

> Canonical reference for the admin reports + exports feature. Promoted from initiative 009's plan after closeout (2026-04-26).

## Scope

The `reportes` app owns:

- The admin-only dashboard at `/reportes/` — aggregate counts (per estado, per tipo, per month) over a filterable solicitud set.
- The admin-wide paginated list at `/reportes/lista/`.
- CSV export at `/reportes/exportar/csv/` (UTF-8 BOM, full filtered set, streamed via DB-side cursor).
- PDF export at `/reportes/exportar/pdf/` (WeasyPrint, capped at 1000 rows; above the cap renders a "use CSV" notice in place of the row table).
- The `ReportFilter` form-facing DTO and its translation to `solicitudes.lifecycle.SolicitudFilter`.

What this feature does **not** own:

- Aggregate SQL — lives in `solicitudes.lifecycle.repositories.solicitud.implementation` (single-query `.values().annotate(Count)` + `TruncMonth`). Reportes consumes those via `LifecycleService`.
- Any new model. Reportes adds zero tables; it reads through existing `Solicitud` data.

## Layer wiring

```
DashboardView / ReportListView / ExportCsvView / ExportPdfView
        │  (all gated by AdminRequiredMixin, re-exported through
        │   reportes/permissions.py)
        ▼
ReportService (services/report_service/interface.py)
        │   ── translates ReportFilter → SolicitudFilter at the boundary
        ▼
LifecycleService (solicitudes.lifecycle)
        │
        ▼
SolicitudRepository (solicitudes.lifecycle.repositories.solicitud)
        │
        ▼
ORM (Solicitud, joined to TipoSolicitud for the responsible_role filter)

ExportService (services/export_service/{csv,pdf}_implementation.py)
        │   ── consumes ReportService.iter_for_admin (DB-side cursor)
        ▼   ── PDF additionally calls ReportService.dashboard
   bytes (CSV with UTF-8 BOM, or PDF rendered via _shared/pdf.render_pdf)
```

`reportes/dependencies.py` wires `LifecycleService → DefaultReportService → {CsvExportImpl, PdfExportImpl}`. The exporter factories accept an optional `report_service=` so each export view constructs **one** `DefaultReportService` and shares it across the dashboard query and the iterator walk — single composed graph per request.

`reportes` never imports from `solicitudes.lifecycle.repositories` or `solicitudes.models`. The only cross-feature import is the lifecycle service interface + its DTOs (`SolicitudFilter`, `SolicitudRow`, `AggregateBy*`).

## Data shapes (`reportes/schemas.py`)

All DTOs are `frozen=True`.

```python
class ExportFormat(StrEnum):
    CSV = "csv"
    PDF = "pdf"

class ReportFilter(BaseModel):
    estado: Estado | None = None
    tipo_id: UUID | None = None
    responsible_role: Role | None = None
    created_from: date | None = None
    created_to: date | None = None
    # @model_validator: created_from must be on or before created_to.

class CountByEstado(BaseModel):
    estado: Estado
    count: int

class CountByTipo(BaseModel):
    tipo_id: UUID
    tipo_nombre: str
    count: int

class CountByMonth(BaseModel):
    year: int
    month: int           # 1..12
    count: int

class DashboardData(BaseModel):
    filter: ReportFilter
    total: int           # sum of by_estado.count
    by_estado: list[CountByEstado]
    by_tipo: list[CountByTipo]
    by_month: list[CountByMonth]
```

The `CountBy*` types are deliberately distinct from the lifecycle layer's `AggregateBy*` types so `solicitudes` never imports from `reportes`. `DefaultReportService.dashboard()` does the (one-line) projection at the layer boundary.

## Filter translation

```python
def _to_solicitud_filter(report_filter: ReportFilter) -> SolicitudFilter:
    return SolicitudFilter(
        estado=report_filter.estado,
        tipo_id=report_filter.tipo_id,
        responsible_role=report_filter.responsible_role,
        created_from=report_filter.created_from,
        created_to=report_filter.created_to,
    )
```

The `responsible_role` filter is honored at the repo via `tipo__responsible_role=...`; the existing `(activo, responsible_role)` index on `TipoSolicitud` covers the lookup, so no schema change.

## Month-window default

When the user supplies neither `created_from` nor `created_to`, the dashboard's `by_month` series defaults to **the last 12 calendar months ending today** (inclusive of the current month). When either bound is set, the user's range is honored exactly with no clamping. Implemented in `_default_month_window(today)` and applied only inside `dashboard()` — `list_paginated()` and `iter_for_admin()` always use the user's filter as-is.

## Form parser (`forms/report_filter_form.py`)

`parse_report_filter(query: QueryDict) -> ReportFilter` is a pure-Python parser, not a `Django Form`. It silently coerces invalid inputs (bad UUID, bad ISO date, unknown enum value, `from > to`) to `None` so a stale bookmark or hand-edited URL never blocks an admin with a 400. This is a deliberate trade-off documented in `test_report_filter_form.py`.

## Exporters

### CSV (`services/export_service/csv_implementation.py`)

- Walks `ReportService.iter_for_admin(filter, chunk_size=500)` — Django `.iterator(chunk_size=...)` opens a server-side cursor on PostgreSQL (silently materialises all rows on SQLite — dev-only concern, noted at the iterator's call site).
- Header (in this exact order): `folio, tipo, solicitante_matricula, solicitante_nombre, estado, requiere_pago, pago_exento, created_at, updated_at`.
- Writer uses `lineterminator="\r\n"` (Excel's expected newline).
- Returns `b"\xef\xbb\xbf" + body` so Excel recognizes UTF-8 and accents survive.
- `content_type = "text/csv; charset=utf-8"`, `filename = "solicitudes.csv"`.

### PDF (`services/export_service/pdf_implementation.py`)

- Calls `ReportService.dashboard(filter)` once for the summary block, then walks `iter_for_admin` until exhaustion or until row 1001 — the iterator is the **single source of truth** for the truncation flag (no separate comparison against `dashboard.total` that could disagree under concurrent writes).
- When `truncated`, `rows=[]` is passed to the template and the Spanish notice "Demasiados registros — use la exportación CSV" fully replaces the row table.
- Renders `templates/reportes/export_pdf.html` via `_shared/pdf.render_pdf`.
- `content_type = "application/pdf"`, `filename = "solicitudes.pdf"`.
- **Performance note:** RNF-05 sets a 5s budget for 1000 rows on native dev hardware. Empirical container measurement (Docker on ARM64 macOS) is ~5.5–6s; the perf test uses a 10s ceiling.

## Views (admin only)

| URL | View | Method | Purpose |
|---|---|---|---|
| `reportes/` | `DashboardView` | GET | Render counts + filter form |
| `reportes/lista/` | `ReportListView` | GET | Paginated filtered list (page_size=25) |
| `reportes/exportar/csv/` | `ExportCsvView` | GET | Stream CSV with `Content-Disposition: attachment` |
| `reportes/exportar/pdf/` | `ExportPdfView` | GET | Stream PDF |

All four views inherit `AdminRequiredMixin` (re-exported through `reportes/permissions.py`); non-admin requests raise `Unauthorized` (mapped to 403 by `AppErrorMiddleware` via `_shared/error.html`). All four accept the same querystring params (`estado`, `tipo_id`, `responsible_role`, `created_from`, `created_to`).

## Frontend

- Templates: `templates/reportes/{dashboard,list,_filter_form,export_pdf}.html`. Bootstrap 5 + Bootstrap Icons; UAZ green primary; outline-secondary for export buttons; per-estado/per-tipo cards with progress bars; `table-hover` for the list.
- Estado labels rendered through the shared partial `templates/solicitudes/_partials/_estado_badge.html` (Spanish `display_name` + semantic badge color).
- Responsible-role labels mapped through `views/_helpers.py:_ROLE_DISPLAY` (Spanish: "Control Escolar" / "Responsable de Programa" / "Docente").
- Filter form re-marks the active option after submit by passing pre-stringified `selected_estado` / `selected_tipo_id` / `selected_role` from `views/_helpers.py:filter_form_choices(filter)` (UUID/StrEnum vs string equality is type-strict in templates).
- Sidebar wiring: `templates/components/sidebar.html` adds a `REPORTES → Dashboard` section under the admin block (with `bi-bar-chart` icon, active-state highlighting, offcanvas mobile parity).
- Mobile reflow verified at 320px: cards stack, navbar hamburger collapses, no horizontal scroll. Visual regression captured by `tests-e2e/test_reportes_golden_path.py` and `tests-e2e/test_reportes_sidebar_link.py` (screenshots at 1280x900 and 320x800).

## Service contract

`ReportService`:

- `dashboard(filter: ReportFilter) -> DashboardData` — composes the three lifecycle aggregates + computes `total = sum(by_estado.count)`. Applies the 12-month default month window iff both date bounds are unset.
- `list_paginated(filter, page) -> Page[SolicitudRow]` — admin-scoped paginated list (the bound is `PageRequest.page_size <= 100`, set in `_shared/pagination.py`).
- `iter_for_admin(filter, chunk_size=500) -> Iterator[SolicitudRow]` — server-side cursor for exporters; bypasses the HTTP page cap and skips the `count()` round trip.

`ExportService` (one per format):

- `export(filter: ReportFilter) -> bytes`
- `content_type: str` (property)
- `filename: str` (property)

## Tests

- `tests/test_report_service.py` — dashboard composition, total = Σ by_estado, `_default_month_window` boundary cases, list_paginated.
- `tests/test_csv_exporter.py` — UTF-8 BOM prefix, header column order, accent round-trip via `decode("utf-8-sig")`.
- `tests/test_pdf_exporter.py` — `%PDF` magic, content-type, filename, truncation rendering when `iter` yields > cap rows (uses `monkeypatch` on `render_pdf` and a stub `ReportService` to skip real rendering), and a 1000-row perf benchmark.
- `tests/test_views.py` — 200 for admin / 403 for non-admin (dashboard, list, export_csv), Spanish-accent round-trip, estado-filter narrowing, `tipo_id` re-selected-option regression, query-count bound (`max <= 12`).
- `tests/test_report_filter_form.py` — every parser branch: valid combos, malformed UUID, malformed date, unknown enum, inverted date range.
- `tests-e2e/test_reportes_golden_path.py` — Tier 2 browser: admin opens dashboard → applies estado filter → exports CSV via the browser; captures desktop + mobile screenshots.
- `tests-e2e/test_reportes_sidebar_link.py` — Tier 2 browser: admin sees `REPORTES → Dashboard` in the sidebar and clicking it lands on `/reportes/`.

Coverage (initiative closeout 2026-04-26): services 100%, exporters 100%, forms 100%, views 100%, total **99%** for the `reportes` package — exceeds plan targets (≥95% / ≥90% / ≥80%).

## Key design decisions

- **`SolicitudFilter` extended additively** with `responsible_role: Role | None`. The `reportes` `ReportFilter` is the form-facing DTO; translation happens at the service boundary so `solicitudes` never imports from `reportes`.
- **`SolicitudRow` extended additively** with `pago_exento: bool = False` so the CSV row can be written from a list query without per-row `get_by_folio` hydration.
- **Aggregate DTOs split across layers**: `solicitudes.lifecycle.AggregateBy{Estado,Tipo,Month}` (repo-layer) vs `reportes.CountBy{Estado,Tipo,Month}` (feature-layer). One mapping in `DefaultReportService.dashboard()`.
- **PDF row cap is 1000**, fixed in `pdf_implementation._PDF_ROW_CAP`. Above the cap the exporter emits a Spanish notice instead of a row table; CSV is the bulk-data path.
- **Filter parsing is permissive**: invalid query params silently degrade to `None` rather than 400. Stale bookmarks render an empty result instead of breaking.

## Related Specs

- [Initiative 009 plan](../../../planning/009-reports/plan.md) — the implementation blueprint this design promotes from.
- [solicitudes/lifecycle/design.md](../../solicitudes/lifecycle/design.md) — provides the additive aggregation methods and the `iter_for_admin` cursor used by the exporters.
- [solicitudes/tipos/design.md](../../solicitudes/tipos/design.md) — `TipoService.list_for_admin` powers the Tipo filter dropdown.
- [usuarios/design.md](../../usuarios/design.md) — `AdminRequiredMixin` re-exported through `reportes/permissions.py`.
- [global/architecture.md](../../../global/architecture.md) — `reportes` responsibilities at the system level.
- [global/requirements.md](../../../global/requirements.md) — RNF-05 (PDF render budget).
