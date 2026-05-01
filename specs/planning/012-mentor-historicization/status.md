# 012 — Mentor Catalog Historicization — Status

**Status:** Implementation Complete (awaiting review)
**Last updated:** 2026-04-26

## Checklist

### Model & migrations
- [x] `mentores/models/mentor_periodo.py` — `MentorPeriodo` with partial unique index + `(matricula, fecha_baja)` index. **No `auto_now_add` on `fecha_alta`** (repo stamps explicitly).
- [x] Update `mentores/models/__init__.py` to export `MentorPeriodo` (and stop exporting `Mentor` once the drop migration runs)
- [x] Migration `0002_mentor_periodo` — schema add, both old `Mentor` and new `MentorPeriodo` coexist
- [x] Migration `0003_backfill_mentor_periodos` — data migration carries `Mentor.fecha_alta` verbatim into `MentorPeriodo.fecha_alta`
- [x] Migration `0003` test — empty source `Mentor` table runs as no-op without error
- [x] Migration `0003` test — populated source `Mentor` table (≥3 rows including one with `fecha_baja` set) backfills with original `fecha_alta` values preserved (regression guard for the `auto_now_add` footgun)
- [x] Migration `0004_drop_mentor` — schema drop of `Mentor`; **docstring explicitly states the migration is forward-only and rolling back past `0002` destroys history**
- [x] All three migrations apply cleanly forward; reverse is `noop` for the data migration; `0004` reverse re-creates an empty `Mentor` table for migration-graph completeness only
- [x] Confirm Postgres-only assumption (partial unique index + `DISTINCT ON`) is documented in the dev README/CLAUDE.md (or add a one-liner if missing)

### Schemas
- [x] [P] Replace `MentorDTO` with `MentorPeriodoDTO` in `schemas.py`; keep `MentorUpsertInput` and `CsvImportResult` unchanged
- [x] [P] Update factories in `tests/factories.py` (`make_mentor` → `make_mentor_periodo`)

### Repository
- [x] Rewrite `repositories/mentor/interface.py` with new method set (7 methods)
- [x] Rewrite `repositories/mentor/implementation.py` against `MentorPeriodo`
- [x] Update `repositories/mentor/__init__.py` exports
- [x] Tests `test_mentor_repository.py` rewritten — covers each method, partial-index enforcement (`IntegrityError`), point-in-time edge cases, history ordering

### Services
- [x] [P] Extend `services/mentor_service/interface.py` with `get_history`, `was_mentor_at`
- [x] [P] Update `services/mentor_service/implementation.py` to delegate the new methods and pass `actor_matricula` to `deactivate`
- [x] [P] `tests/fakes.py` — `InMemoryMentorRepository` rewritten to mirror the new contract (per-period storage; partial-uniqueness emulated)
- [x] [P] `tests/test_mentor_service.py` extended with `get_history` and `was_mentor_at` cases
- [x] [P] `tests/test_csv_importer.py` — update fixtures and any direct ORM assertions (e.g. `Mentor.objects.*` → `MentorPeriodo.objects.*`); outcome counts (`inserted`, `reactivated`, `skipped_duplicates`, `invalid_rows`) keep their external semantics; 100-row acceptance test passes
- [x] Service test: concurrent-reactivation `IntegrityError` recovery path (mock repo's `create` to raise once; service returns `(dto, ALREADY_ACTIVE)` instead of surfacing 500)
- [x] Repository test: `was_mentor_at` boundary semantics — pin `[fecha_alta, fecha_baja)` half-open with three explicit cases (`==fecha_alta` is True; `==fecha_baja - 1µs` is True; `==fecha_baja` is False)

### Views & templates
- [x] [P] `mentores/views/list.py` — pass `only_active` through to the rewritten `MentorService.list`; `MentorPeriodoDTO` in context
- [x] [P] `mentores/views/detail.py` — **NEW** `MentorDetailView`
- [x] `mentores/views/deactivate.py` — pass `actor` through to service so `desactivado_por` is recorded
- [x] `mentores/urls.py` — add `path("<str:matricula>/", DetailView.as_view(), name="detail")`
- [x] `templates/mentores/list.html` — link matrícula cell to `mentores:detail`; replace `m.activo` reads with `m.fecha_baja is None` (or expose a small `is_currently_active` template tag)
- [x] [P] `templates/mentores/detail.html` — **NEW** timeline template
- [x] `mentores/tests/test_views.py` — list view assertions updated for the link; new tests for `MentorDetailView` (admin-only; 404 for unknown matrícula)

### Cross-feature regression
- [x] `mentores/tests/test_intake_wiring.py` setup helpers updated: `_seed_mentor` uses `MentorPeriodo`; the in-test `Mentor.objects.filter(...).update(activo=False)` becomes `MentorPeriodo.objects.filter(matricula=..., fecha_baja__isnull=True).update(fecha_baja=timezone.now())`; the `creado_por` count assertion updates to filter `fecha_baja__isnull=True`. **All behavioral assertions stay identical.**
- [x] All cross-feature tests still green after the setup-helper updates
- [x] No edits to `solicitudes/intake/` runtime code — confirmed by `git diff` on `solicitudes/intake/{adapters,services,views,forms,permissions,exceptions,schemas,mentor_port,urls}.py` and `solicitudes/intake/dependencies.py`

### Quality gates
- [x] `ruff` clean
- [x] `mypy` clean (target the rewritten files explicitly)
- [x] Full `pytest` green; coverage targets met (services ≥ 95%, repo ≥ 95%, views ≥ 80%)

### E2E
- [x] Tier 1 (Client multi-step): Reactivation creates a new period — admin adds → deactivates → re-adds; `MentorPeriodo.objects.filter(matricula=M).count() == 2`; `service.get_history(M)` returns both newest-first.
- [x] Tier 1 (Client multi-step): CSV reactivation path — same scenario via the import form; result counts confirm `reactivated == 1`; second period exists.
- [x] Tier 1 (Client multi-step): Cross-feature regression — `test_intake_wiring.py::test_mentor_deactivation_preserves_existing_solicitud_snapshot` passes against the new schema after its setup helpers are updated to `MentorPeriodo`. Behavioral assertions (snapshot integrity) unchanged.
- [x] Tier 1 (Client multi-step): Point-in-time `was_mentor_at` returns correct booleans for in-period, gap, and post-reactivation timestamps. Boundaries pinned per the half-open `[fecha_alta, fecha_baja)` semantics.
- [x] Tier 1 (Client multi-step): Partial unique index enforced at the DB — attempting two open periods for the same matrícula raises `IntegrityError`.
- [x] Tier 1 (Client multi-step): Concurrent reactivation race — repo-level `IntegrityError` is recovered into `ALREADY_ACTIVE` (no 500 surfaces).
- [x] Tier 2 (browser/Playwright): Admin views a mentor's history at `/mentores/<matricula>/` — timeline with two entries, status pill correct, screenshots at 1280×900 and 320×800.
- [x] Tier 2 (browser/Playwright): Admin reactivates a deactivated mentor via CSV import → opens history page → sees the new period at the top of the timeline.

### Bulk deactivation (added 2026-04-26)
- [x] `schemas.py` — add `BulkDeactivateResult` DTO (frozen; total_attempted, closed, already_inactive)
- [x] [P] Repo: `deactivate_many(matriculas, *, actor_matricula) -> int` — single UPDATE filtered by `matricula__in` + `fecha_baja__isnull=True`
- [x] [P] Repo: `deactivate_all_active(*, actor_matricula) -> int` — single UPDATE on every open period
- [x] [P] Update `InMemoryMentorRepository` (fakes.py) with both methods
- [x] [P] Service: `bulk_deactivate(matriculas, actor)` and `deactivate_all_active(actor)` returning `BulkDeactivateResult`
- [x] `views/bulk_deactivate.py` — **NEW** `BulkDeactivateMentorsView` POST-only with two-step confirm. Step 1 (no `token`) emits a `django.core.signing.dumps` payload; step 2 (with `token`) verifies via `signing.loads(salt="mentores.bulk_deactivate", max_age=300)` and applies → flash → redirect.
- [x] `urls.py` — add `path("desactivar-bulk/", BulkDeactivateMentorsView.as_view(), name="deactivate_bulk")`
- [x] `templates/mentores/list.html` — wrap table in form; per-row checkbox on currently-open periods only; toolbar above the table with "Seleccionar todos" (master toggle, `type="button"`, small inline IIFE script for the click handler) + single "Desactivar" submit button (`action=selected`, selection implicit). Acciones column removed.
- [x] `templates/mentores/confirm_bulk_deactivate.html` — **NEW** confirmation template carrying one signed `token` hidden field (no per-matrícula inputs to tamper with).
- [x] Repo tests: deactivate_many subset/empty/already-closed; deactivate_all_active leaves closed periods untouched
- [x] Service tests: counts assemble correctly for both variants; dedup of duplicate input matrículas verified
- [x] View tests: admin-only; step 1 emits token in context; step 2 with valid token closes + flashes + redirects; tampered/expired/unknown-action tokens rejected with no DB writes
- [x] Tier 1 e2e: bulk-deactivate-selected closes 3 of 5 active matriculas, list view reflects updated state. Tier 2 browser test additionally exercises the master "Seleccionar todos" toggle (check-all + uncheck-all).

## Blockers

- **008 — Mentors** must be merged to `main` before this initiative starts. Currently 008 is implementation-complete on `main` as pending changes (per the user's review workflow); flip to `Done` first.

## Legend

- `[P]` = parallelizable with siblings in the same section
