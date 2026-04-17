# 009 — Reports & Dashboard

## Summary

Admin-only dashboard with aggregate counts (per estado, per tipo, per month) over a date range, plus CSV/PDF export of the filtered solicitud list. No charts — Bootstrap tables and progress bars convey magnitudes. Uses the existing solicitud data; adds no new tables. Reads through `solicitudes` repositories via service interfaces, never touching the ORM directly from `reportes`.

## Depends on

- **001** — `_shared/pdf.py`, pagination
- **002** — `AdminRequiredMixin`
- **004** — `Solicitud`, `SolicitudFilter`, lifecycle service

## Affected Apps / Modules

- `reportes/` — new app
- `solicitudes/lifecycle/services/lifecycle_service` — extend with aggregation methods (interface change, additive)

## References

- [global/requirements.md](../../global/requirements.md) — RNF-05
- [global/architecture.md](../../global/architecture.md) — `reportes` responsibilities

## Implementation Details

### Layout

```
reportes/
├── __init__.py
├── apps.py
├── urls.py
├── exceptions.py
├── schemas.py
├── permissions.py            # re-export AdminRequiredMixin
├── dependencies.py
├── services/
│   ├── report_service/{interface,implementation}.py
│   └── export_service/{interface,csv_implementation,pdf_implementation}.py
├── views/
│   ├── dashboard.py
│   ├── list.py               # filtered solicitud list (admin-wide)
│   ├── export_csv.py
│   └── export_pdf.py
├── templates/                # under templates/reportes/
└── tests/
```

### Aggregate DTOs (`schemas.py`)

```python
class ReportFilter(BaseModel):
    estado: Estado | None = None
    tipo_id: UUID | None = None
    responsible_role: Role | None = None
    created_from: date | None = None
    created_to: date | None = None

class CountByEstado(BaseModel):
    model_config = {"frozen": True}
    estado: Estado
    count: int

class CountByTipo(BaseModel):
    model_config = {"frozen": True}
    tipo_id: UUID
    tipo_nombre: str
    count: int

class CountByMonth(BaseModel):
    model_config = {"frozen": True}
    year: int
    month: int                 # 1-12
    count: int

class DashboardData(BaseModel):
    model_config = {"frozen": True}
    filter: ReportFilter
    total: int
    by_estado: list[CountByEstado]
    by_tipo: list[CountByTipo]
    by_month: list[CountByMonth]   # last 12 months filtered
```

### Aggregation methods on `LifecycleService` (additive interface change)

```python
class LifecycleService(ABC):
    ...
    @abstractmethod
    def aggregate_by_estado(self, *, filter: ReportFilter) -> list[CountByEstado]: ...
    @abstractmethod
    def aggregate_by_tipo(self, *, filter: ReportFilter) -> list[CountByTipo]: ...
    @abstractmethod
    def aggregate_by_month(self, *, filter: ReportFilter) -> list[CountByMonth]: ...
    @abstractmethod
    def list_for_admin(self, *, filter: ReportFilter, page: PageRequest) -> Page[SolicitudRow]: ...
```

The repository (`OrmSolicitudRepository`) gains corresponding methods using `.values(...).annotate(Count("folio"))` — single SQL queries, no Python aggregation.

### `ReportService`

```python
class ReportService(ABC):
    @abstractmethod
    def dashboard(self, filter: ReportFilter) -> DashboardData: ...
    @abstractmethod
    def list_paginated(self, filter: ReportFilter, page: PageRequest) -> Page[SolicitudRow]: ...
```

`DefaultReportService` composes the four `LifecycleService` methods. Total = sum of `by_estado.count`.

### `ExportService`

```python
class ExportService(ABC):
    @abstractmethod
    def export(self, format: ExportFormat, *, filter: ReportFilter) -> bytes: ...    # CSV bytes or PDF bytes
```

- `CsvExportImpl` writes UTF-8-BOM CSV with columns: `folio, tipo, solicitante_matricula, solicitante_nombre, estado, requiere_pago, pago_exento, created_at, updated_at`. Streams in chunks of 500 rows via the repository's pagination.
- `PdfExportImpl` renders `templates/reportes/export_pdf.html` (a printable summary + table) via `_shared/pdf.render_pdf`. Caps at 1000 rows; if more match, renders a friendly message in the PDF and recommends CSV.

### Views (admin only)

| URL | View | Method | Purpose |
|---|---|---|---|
| `reportes/` | `DashboardView` | GET | Render counts + filter form |
| `reportes/lista/` | `ReportListView` | GET | Paginated filtered list |
| `reportes/exportar/csv/` | `ExportCsvView` | GET | Streams CSV with `Content-Disposition: attachment` |
| `reportes/exportar/pdf/` | `ExportPdfView` | GET | Streams PDF |

All accept the same filter query params (`estado`, `tipo_id`, `responsible_role`, `created_from`, `created_to`); a single `ReportFilterForm` parses them and converts to `ReportFilter`.

### Templates

```
templates/reportes/
├── dashboard.html             # filter form on top, three tables/cards underneath
├── list.html                  # paginated list with same filters
├── export_pdf.html            # printable layout
└── _filter_form.html          # shared GET form
```

Bootstrap progress bars convey the per-tipo and per-estado distributions.

### Sequencing

1. Schemas, exceptions.
2. Extend `OrmSolicitudRepository` with aggregate methods + tests.
3. Extend `LifecycleService` interface and impl with aggregate methods + tests.
4. `ReportService` + tests (using fakes).
5. `ExportService` (csv + pdf impls) + tests (CSV asserts content; PDF asserts bytes start with `%PDF`).
6. Forms + views + templates.
7. End-to-end: load fixture of 30 solicitudes across tipos, estados, dates → dashboard counts match; CSV export rows match filter; PDF export renders.


## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)
- Cross-feature: with a fixture of N solicitudes spanning estados, tipos, and dates, admin hits `/reportes/` → counts in `DashboardData` match a hand-computed aggregate; date-range filter narrows them correctly.
- Cross-feature: admin hits `/reportes/exportar/csv/` with the same filter → response is `Content-Type: text/csv` with UTF-8 BOM, rows match the filtered list, accents preserved.
- Negative: non-admin user hits `/reportes/` → 403 via `_shared/error.html`.

### Browser (Tier 2 — `pytest-playwright`)
- Golden path: admin opens the dashboard, applies a filter (estado + date range), then triggers CSV export and asserts the download (browser).

## Acceptance Criteria

- [ ] `/reportes/` returns 403 for non-admin, 200 for admin.
- [ ] Counts match a hand-computed answer over a fixture set; date-range filter respected.
- [ ] CSV export returns UTF-8-BOM file readable by Excel; columns and rows match the filter; `Content-Type: text/csv`.
- [ ] PDF export renders within 5 seconds for 1000 rows on dev hardware.
- [ ] Aggregate queries are single SQL statements (verified by `django_assert_num_queries(<=4)` per dashboard render).
- [ ] Coverage: service ≥ 95%, exporters ≥ 90%, views ≥ 80%.

## Open Questions

- **OQ-009-1** — Per-responsable filter (e.g., "show only solicitudes whose responsible_role = CONTROL_ESCOLAR")? Yes, included as `responsible_role` filter.
- **OQ-009-2** — Time-of-day breakdown / hour-of-day chart: out of scope for v1.
- **OQ-009-3** — Cached / pre-aggregated counts: not needed at current volumes; revisit when dashboard render exceeds 1 second.
