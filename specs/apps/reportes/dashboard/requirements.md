# reportes · dashboard — Requirements

> WHAT this feature does and WHY. No implementation details. Shipped by initiative **009 — Reports & Dashboard**.

## Purpose

Give administrators an at-a-glance view of solicitud volume across the institution and the tools to extract that data for offline use. Without this feature, the only way to answer "how many constancia requests did we process last month?" is by running ad-hoc SQL — unsafe, slow, and inaccessible to the people who need the answer.

The feature satisfies **RNF-05** (dashboard with statistics by tipo/estado/period; CSV/PDF export) and is the only admin-wide reporting surface in the system.

## Why this lives in its own app

Reporting reads through every solicitud in the system, which is a fundamentally different access pattern from intake (per-user) and revision (per-role). Keeping it in `solicitudes` would either:

- Duplicate aggregation logic across features, or
- Force `solicitudes` to know about admin-wide concerns that don't belong there.

Splitting `reportes` out keeps `solicitudes` focused on the per-solicitud lifecycle and lets `reportes` evolve its own filtering, export, and presentation surface without churning the lifecycle layer.

## In scope

- An **admin dashboard** showing aggregate counts of solicitudes broken down by **estado**, by **tipo**, and by **month** for a filterable date/role/estado/tipo window.
- An **admin-wide paginated list** of solicitudes (the bypass-the-role-queue view for admins who need to see everything).
- A **CSV export** of the full filtered set — the bulk data path, designed to handle datasets larger than the dashboard renders.
- A **PDF export** of the dashboard summary plus a row table, capped at 1000 rows; above the cap the PDF directs the user to CSV instead.
- A **filter form** consumed by all four surfaces (dashboard, list, CSV, PDF) so the same querystring drives every view.
- A **default month window** for the by-month chart when the user has not chosen a date range, so the dashboard always renders something meaningful on first load.

## Out of scope

- Aggregate SQL itself. This feature is a **consumer** of the lifecycle service's aggregation methods (`aggregate_by_estado`, `aggregate_by_tipo`, `aggregate_by_month`, `iter_for_admin`). Adding new aggregates means extending lifecycle, not duplicating queries here.
- Any new ORM model. Reportes adds zero tables.
- Per-user reporting (alumno seeing their own metrics). The dashboard is admin-wide; per-user history lives in intake's "Mis solicitudes" surface.
- Real-time/streaming updates. Refresh-on-load is acceptable.
- Saved filters, scheduled reports, email digests. Possible future work, not in v1.
- Charts beyond the three panels (estado, tipo, month). Visualization complexity stays minimal.
- Internationalization beyond Spanish.

## Functional requirements

| ID | Requirement | Source |
|---|---|---|
| RF-REP-01 | The admin dashboard must show counts of solicitudes grouped by **estado** for the active filter set. | RNF-05 |
| RF-REP-02 | The admin dashboard must show counts of solicitudes grouped by **tipo** for the active filter set. | RNF-05 |
| RF-REP-03 | The admin dashboard must show counts of solicitudes grouped by **calendar month** for the active filter set. | RNF-05 |
| RF-REP-04 | When neither `created_from` nor `created_to` is supplied, the by-month series defaults to the **last 12 calendar months ending today** (inclusive of the current month). When either bound is set, the user's range is honored exactly. | RNF-05, UX |
| RF-REP-05 | The filter must accept any combination of: `estado`, `tipo`, `responsible_role`, `created_from`, `created_to`. Filters compose with AND semantics. | RNF-05 |
| RF-REP-06 | Invalid filter input from the querystring (bad UUID, bad date, unknown enum, inverted date range) must **not** error out the page; the bad parameter must degrade silently to "not set" so a stale bookmark or hand-edited URL renders an empty result instead of a 400. | UX (admin tooling tolerance) |
| RF-REP-07 | The admin paginated list must show a row per solicitud with folio, tipo, solicitante, estado, requires-pago/exemption flags, and timestamps, scoped to the same filter as the dashboard. | RNF-05 |
| RF-REP-08 | The CSV export must contain the **full filtered set** (no pagination cap), be UTF-8 with a BOM so Excel renders accents correctly, and use Excel-compatible newlines. | RNF-05, RT-08 |
| RF-REP-09 | The PDF export must contain the dashboard summary plus a row table; when the filtered set exceeds **1000 rows**, the row table is replaced with a Spanish notice directing the user to the CSV export. | RNF-05, perf budget |
| RF-REP-10 | All four surfaces (dashboard, list, CSV, PDF) must be admin-only. Non-admin access returns 403. | RNF-06 |
| RF-REP-11 | Selected filter values must persist through re-render (the form re-marks the active option after submit). | UX |

## Non-functional requirements

- **Performance budget.** RNF-05 sets a 5-second budget for rendering a PDF over 1000 rows on native dev hardware. The implementation is held to this budget by the test suite; in containers (Docker on ARM64 macOS) the empirical measurement is ~5.5–6 s, so the perf test ceiling is 10 s.
- **No N+1 queries on the dashboard.** The three aggregates plus the tipo dropdown plus auth/savepoint overhead must total at most ~12 queries; this is regression-pinned in the view test.
- **Bulk data is streamed.** The CSV exporter must not load the full filtered set into memory; it walks a server-side cursor (on PostgreSQL) and emits rows as it reads. SQLite materializes — acceptable for dev only.
- **Filter parsing is permissive.** The dashboard tolerates malformed input rather than rejecting it. This is a deliberate trade-off: an admin landing on a bad URL should see "no results, adjust filters" rather than a 400 page.
- **Cross-feature direction is one-way.** `reportes` consumes `solicitudes.lifecycle`; the inverse must never happen. New aggregates must extend lifecycle's interface (additive `SolicitudFilter` / `SolicitudRow` fields, additional `aggregate_*` methods), and the projection from lifecycle DTOs to feature-facing DTOs happens at the `reportes` service boundary.
- **Exports are reproducible.** The PDF export is byte-stable for a given filter and frozen clock (the WeasyPrint determinism contract from `_shared/pdf`). The CSV ordering is stable (the same query produces the same row order on subsequent runs).
- **Accessibility & responsive.** Bootstrap 5 layout reflows to 320 px without horizontal scroll; status badges convey estado via both color **and** text (WCAG color-as-only-signal); estado/role labels are Spanish; mobile hamburger collapses the sidebar.
- **Spanish UI copy** end-to-end. Code identifiers in English.

## Open questions

None at initiative closeout (2026-04-26).

## Related Specs

- [design.md](./design.md) — HOW.
- [`specs/planning/009-reports/plan.md`](../../../planning/009-reports/plan.md) — implementation blueprint.
- [`specs/apps/solicitudes/lifecycle/design.md`](../../solicitudes/lifecycle/design.md) — provides the aggregation methods and the admin-wide cursor that this feature consumes.
- [`specs/apps/solicitudes/tipos/design.md`](../../solicitudes/tipos/design.md) — provides the tipo dropdown source.
- [`specs/apps/usuarios/design.md`](../../usuarios/design.md) — provides `AdminRequiredMixin`.
- [`specs/global/requirements.md`](../../../global/requirements.md) — RNF-05, RNF-06, RT-08.
