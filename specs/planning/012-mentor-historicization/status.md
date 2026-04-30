# 012 — Mentor Catalog Historicization — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

### Model & migrations
- [ ] `mentores/models/mentor_periodo.py` — `MentorPeriodo` with partial unique index + `(matricula, fecha_baja)` index. **No `auto_now_add` on `fecha_alta`** (repo stamps explicitly).
- [ ] Update `mentores/models/__init__.py` to export `MentorPeriodo` (and stop exporting `Mentor` once the drop migration runs)
- [ ] Migration `0002_mentor_periodo` — schema add, both old `Mentor` and new `MentorPeriodo` coexist
- [ ] Migration `0003_backfill_mentor_periodos` — data migration carries `Mentor.fecha_alta` verbatim into `MentorPeriodo.fecha_alta`
- [ ] Migration `0003` test — empty source `Mentor` table runs as no-op without error
- [ ] Migration `0003` test — populated source `Mentor` table (≥3 rows including one with `fecha_baja` set) backfills with original `fecha_alta` values preserved (regression guard for the `auto_now_add` footgun)
- [ ] Migration `0004_drop_mentor` — schema drop of `Mentor`; **docstring explicitly states the migration is forward-only and rolling back past `0002` destroys history**
- [ ] All three migrations apply cleanly forward; reverse is `noop` for the data migration; `0004` reverse re-creates an empty `Mentor` table for migration-graph completeness only
- [ ] Confirm Postgres-only assumption (partial unique index + `DISTINCT ON`) is documented in the dev README/CLAUDE.md (or add a one-liner if missing)

### Schemas
- [ ] [P] Replace `MentorDTO` with `MentorPeriodoDTO` in `schemas.py`; keep `MentorUpsertInput` and `CsvImportResult` unchanged
- [ ] [P] Update factories in `tests/factories.py` (`make_mentor` → `make_mentor_periodo`)

### Repository
- [ ] Rewrite `repositories/mentor/interface.py` with new method set (7 methods)
- [ ] Rewrite `repositories/mentor/implementation.py` against `MentorPeriodo`
- [ ] Update `repositories/mentor/__init__.py` exports
- [ ] Tests `test_mentor_repository.py` rewritten — covers each method, partial-index enforcement (`IntegrityError`), point-in-time edge cases, history ordering

### Services
- [ ] [P] Extend `services/mentor_service/interface.py` with `get_history`, `was_mentor_at`
- [ ] [P] Update `services/mentor_service/implementation.py` to delegate the new methods and pass `actor_matricula` to `deactivate`
- [ ] [P] `tests/fakes.py` — `InMemoryMentorRepository` rewritten to mirror the new contract (per-period storage; partial-uniqueness emulated)
- [ ] [P] `tests/test_mentor_service.py` extended with `get_history` and `was_mentor_at` cases
- [ ] [P] `tests/test_csv_importer.py` — update fixtures and any direct ORM assertions (e.g. `Mentor.objects.*` → `MentorPeriodo.objects.*`); outcome counts (`inserted`, `reactivated`, `skipped_duplicates`, `invalid_rows`) keep their external semantics; 100-row acceptance test passes
- [ ] Service test: concurrent-reactivation `IntegrityError` recovery path (mock repo's `create` to raise once; service returns `(dto, ALREADY_ACTIVE)` instead of surfacing 500)
- [ ] Repository test: `was_mentor_at` boundary semantics — pin `[fecha_alta, fecha_baja)` half-open with three explicit cases (`==fecha_alta` is True; `==fecha_baja - 1µs` is True; `==fecha_baja` is False)

### Views & templates
- [ ] [P] `mentores/views/list.py` — pass `only_active` through to the rewritten `MentorService.list`; `MentorPeriodoDTO` in context
- [ ] [P] `mentores/views/detail.py` — **NEW** `MentorDetailView`
- [ ] `mentores/views/deactivate.py` — pass `actor` through to service so `desactivado_por` is recorded
- [ ] `mentores/urls.py` — add `path("<str:matricula>/", DetailView.as_view(), name="detail")`
- [ ] `templates/mentores/list.html` — link matrícula cell to `mentores:detail`; replace `m.activo` reads with `m.fecha_baja is None` (or expose a small `is_currently_active` template tag)
- [ ] [P] `templates/mentores/detail.html` — **NEW** timeline template
- [ ] `mentores/tests/test_views.py` — list view assertions updated for the link; new tests for `MentorDetailView` (admin-only; 404 for unknown matrícula)

### Cross-feature regression
- [ ] `mentores/tests/test_intake_wiring.py` setup helpers updated: `_seed_mentor` uses `MentorPeriodo`; the in-test `Mentor.objects.filter(...).update(activo=False)` becomes `MentorPeriodo.objects.filter(matricula=..., fecha_baja__isnull=True).update(fecha_baja=timezone.now())`; the `creado_por` count assertion updates to filter `fecha_baja__isnull=True`. **All behavioral assertions stay identical.**
- [ ] All cross-feature tests still green after the setup-helper updates
- [ ] No edits to `solicitudes/intake/` runtime code — confirmed by `git diff` on `solicitudes/intake/{adapters,services,views,forms,permissions,exceptions,schemas,mentor_port,urls}.py` and `solicitudes/intake/dependencies.py`

### Quality gates
- [ ] `ruff` clean
- [ ] `mypy` clean (target the rewritten files explicitly)
- [ ] Full `pytest` green; coverage targets met (services ≥ 95%, repo ≥ 95%, views ≥ 80%)

### E2E
- [ ] Tier 1 (Client multi-step): Reactivation creates a new period — admin adds → deactivates → re-adds; `MentorPeriodo.objects.filter(matricula=M).count() == 2`; `service.get_history(M)` returns both newest-first.
- [ ] Tier 1 (Client multi-step): CSV reactivation path — same scenario via the import form; result counts confirm `reactivated == 1`; second period exists.
- [ ] Tier 1 (Client multi-step): Cross-feature regression — `test_intake_wiring.py::test_mentor_deactivation_preserves_existing_solicitud_snapshot` passes against the new schema after its setup helpers are updated to `MentorPeriodo`. Behavioral assertions (snapshot integrity) unchanged.
- [ ] Tier 1 (Client multi-step): Point-in-time `was_mentor_at` returns correct booleans for in-period, gap, and post-reactivation timestamps. Boundaries pinned per the half-open `[fecha_alta, fecha_baja)` semantics.
- [ ] Tier 1 (Client multi-step): Partial unique index enforced at the DB — attempting two open periods for the same matrícula raises `IntegrityError`.
- [ ] Tier 1 (Client multi-step): Concurrent reactivation race — repo-level `IntegrityError` is recovered into `ALREADY_ACTIVE` (no 500 surfaces).
- [ ] Tier 2 (browser/Playwright): Admin views a mentor's history at `/mentores/<matricula>/` — timeline with two entries, status pill correct, screenshots at 1280×900 and 320×800.
- [ ] Tier 2 (browser/Playwright): Admin reactivates a deactivated mentor via CSV import → opens history page → sees the new period at the top of the timeline.

## Blockers

- **008 — Mentors** must be merged to `main` before this initiative starts. Currently 008 is implementation-complete on `main` as pending changes (per the user's review workflow); flip to `Done` first.

## Legend

- `[P]` = parallelizable with siblings in the same section
