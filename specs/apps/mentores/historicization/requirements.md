# mentores · historicization — Requirements

> Drafted from the in-conversation exchange of 2026-04-25 (option 2, "full historicization"). Feeds initiative **012 — Mentor Catalog Historicization** in `specs/planning/012-mentor-historicization/`.

## Why

The mentor catalog shipped in initiative **008** stores **only the current state**: one row per matrícula, with `fecha_alta` rewritten on reactivation and `fecha_baja` cleared. Reactivating a previously-deactivated matrícula erases the prior `(alta, baja)` range. Consequences:

- The catalog cannot answer **"was matrícula M a mentor on 2024-04-15?"** — the current row only knows the latest period.
- Admins lose context: who first registered the mentor, when, from which import; who deactivated and when; and whether this is a long-tenured mentor or a recently-reinstated one.
- Reports and audits that need historical mentor coverage (per-period, per-program, year-over-year) cannot be derived from the catalog. Today they're not derivable from anywhere.

Downstream **snapshot integrity** for `Solicitud.pago_exento` is preserved (it's stamped at creation per OQ-008-2), so this is not a correctness bug for intake. It's a missing capability for catalog-side reporting and audit.

## What

Replace the single-row-per-matrícula model with a **per-period model**: each `(alta, baja)` range becomes its own row in a new `MentorPeriodo` table. The catalog can answer point-in-time membership queries and produce per-mentor timelines. The current `Mentor` table is retired.

### User stories

- **As an admin**, I open a mentor's detail page and see the **complete timeline** of every period the matrícula was active (alta date, baja date, source — MANUAL or CSV — note, who started/ended each period). Each period is read-only history.
- **As an admin**, when I reactivate a previously-deactivated matrícula (manually or via CSV), the system **opens a new period** rather than rewriting the old one. The previous period stays in the timeline.
- **As an admin**, the existing list view continues to show **currently-active mentors by default**, with no change in the default landing experience.
- **As a future report consumer (009)**, I can ask the catalog `was_mentor_at(matricula, when)` and get a correct answer for any `when` ≥ system epoch.

### Acceptance criteria

- [x] `MentorPeriodo` exists; each row is a single `(matricula, fecha_alta, fecha_baja)` triple. `fecha_baja IS NULL` denotes "currently active".
- [x] At most **one active period per matrícula** at any time (database-enforced).
- [x] **Reactivation** (manual add of an inactive matrícula, or CSV import including one) inserts a **new** `MentorPeriodo` row. Older periods stay intact.
- [x] **Deactivation** updates only the currently-active period (sets `fecha_baja = now()` and records `desactivado_por`).
- [x] `is_mentor(matricula)` returns the same boolean it does today (currently-active check). No behavior change for downstream consumers (intake, `pago_exento`).
- [x] **New** read API on the service layer:
  - `get_history(matricula)` returns the full timeline, newest-first.
  - `was_mentor_at(matricula, when)` returns whether the matrícula was active at `when`.
- [x] **New detail view** `/mentores/<matricula>/` renders the timeline (read-only).
- [x] **List view** continues to show currently-active mentors as default; the existing `filtered=1` sentinel pattern is preserved.
- [x] **CSV import counts** (`inserted`, `reactivated`, `skipped_duplicates`, `invalid_rows`) keep the same external semantics.
- [x] **Existing data is migrated** without loss: each pre-existing `Mentor` row becomes one `MentorPeriodo` row carrying the original `fecha_alta`, `fecha_baja`, `fuente`, `nota`, `creado_por` (with `desactivado_por = NULL` since legacy data didn't capture it).
- [x] After the migration, the `Mentor` table is dropped. Repository, service, importer, views, and tests reference only `MentorPeriodo`.
- [x] **Cross-feature regression tests pass**: the 008 snapshot-integrity scenario (deactivate a mentor → existing solicitudes keep `pago_exento=True`) continues to pass against the new schema.

### Bulk deactivation (added during 012 implementation)

- [x] **As an admin**, on the list view I can tick checkboxes on currently-active mentors and click a single "Desactivar" button to close all selected periods in one action.
- [x] **As an admin**, a "Seleccionar todos" master button toggles every checkbox on the current page (and toggles them all off on a second click).
- [x] **As an admin**, the bulk deactivation requires a server-side confirmation step that I cannot bypass: the second POST is rejected unless it carries a fresh signed token emitted by the confirmation page.
- [x] **Per-row "Desactivar" link removed**; the only deactivation paths are the bulk flow and the still-routable `/mentores/<matricula>/desactivar/` URL (no UI exposure today).
- [x] Outcome counts (`closed`, `already_inactive`) honestly report what happened. Duplicates in the input do not inflate `already_inactive`. Already-closed and unknown matrículas are lumped into `already_inactive` because the catalog cannot distinguish them post-hoc.

### Out of scope

- **Editing past periods.** The detail view is read-only for closed periods. Admins cannot rewrite history.
- **Per-period notes editing UI.** Notes are set at the time the period starts (manual add or CSV import). A separate initiative can add note-edit-while-active if needed.
- **Bulk reactivation across many matrículas at a time** beyond what CSV import already supports.
- **Audit log for non-period changes.** Editing nota on an active period is in-place; if a richer audit log is needed, that's a separate initiative wiring `_shared/audit.py`.
- **Per-period UI badges in the existing list view.** The detail view is the only new UI; the list view stays minimal to avoid a big rework.

## Cross-references

- 008 — Mentors (`specs/planning/008-mentors/plan.md`) — current implementation that this initiative extends and partially replaces.
- 004 — Solicitud Lifecycle (`specs/planning/004-solicitud-lifecycle/plan.md`) — owner of the `pago_exento` snapshot. This initiative must not break that contract.
- Future 009 — Reports & Dashboard — the most likely first consumer of `was_mentor_at`.

## Open Questions (resolved here for the plan)

- **Q: Should the model retain a "current state" denormalized cache row, or do we always derive from `MentorPeriodo`?**
  → Always derive. A partial unique index on `MentorPeriodo(matricula) WHERE fecha_baja IS NULL` enforces "at most one active per matrícula", and the hot-path query is a one-row indexed read.
- **Q: When reactivating, does fuente/nota carry over from the prior period?**
  → No. Each new period captures the source and note that *triggered* it. The history is honest about each period's provenance.
- **Q: When an admin deactivates, do we capture *who*?**
  → Yes — new field `desactivado_por`. Legacy rows migrate with `NULL` (provenance unknown for those). Required for new periods closed after the migration.
