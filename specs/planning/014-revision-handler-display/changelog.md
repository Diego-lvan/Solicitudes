# 014 — Revision Handler Display — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-26

- Initiative created.
- Brainstorm settled in-session: surface "who is handling this" in the revision queue + detail, drop the "Acción" column, and render solicitante context (nombre · matrícula · email) on the revision detail page.
- Key decisions:
  - "Atendida por" is **derived** from `HistorialEstado` (actor of the most recent `atender` transition). No `assigned_to` field; shared-queue invariant preserved.
  - Display populated for EN_PROCESO, FINALIZADA, and CANCELADA-from-EN_PROCESO; blank for CREADA and CANCELADA-from-CREADA (Option B from brainstorm).
  - Scope is **revision only** (not "Mis solicitudes" / intake list).
  - Queue path keeps the existing 3-query cap via `Subquery` annotation on `_base_queryset()`. Detail path takes zero extra SQL (historial is already loaded).
  - DTO shape split: flat strings on `SolicitudRow` (queue), structured `HandlerRef` on `SolicitudDetail` (detail) — keeps the queue template trivial while letting the detail render `name (matrícula) · date`.
- Out of scope captured: no `assigned_to` semantics, no intake-side changes, no separate finalizer/canceller attribution, no notification copy changes, no new "atendida por" filter on the queue.

## 2026-04-26 — implementation

- Worktree at `.worktrees/014-revision-handler-display`, branch `initiative/014-revision-handler-display`. Dev stack on alt ports 8014/8445/5434, project name `solicitudes014`, isolated network `solicitudes014_solicitudes-net`. The compose port/network edits are local working-tree-only and will be reverted before merge.
- DTOs: added `HandlerRef`, `SolicitudRow.atendida_por_matricula` / `atendida_por_nombre` (default `""`), `SolicitudDetail.atendida_por: HandlerRef | None = None` in `lifecycle/schemas.py`.
- Repository (`lifecycle/repositories/solicitud/implementation.py`):
  - `_base_queryset()` now annotates two `Subquery` columns sourced from `HistorialEstado` (filtered to `estado_nuevo=EN_PROCESO`, ordered `-created_at`) — keeps queue rendering at the existing 3-query cap.
  - `_to_row()` reads annotations into the DTO fields (defaulting to `""`).
  - `_derive_handler()` builds `HandlerRef` from the in-memory historial; `_to_detail()` calls it with zero extra SQL (`django_assert_num_queries(2)` confirms).
  - Implementation comment documents that `iter_for_admin` inherits the harmless subquery, bounded by the existing `(solicitud, -created_at)` historial index.
- Fakes (`lifecycle/tests/fakes.py`): `InMemorySolicitudRepository._row` and `get_by_folio` derive both the row strings and `HandlerRef` from the in-memory historial via a shared `_derive_handler()` matching the ORM derivation.
- Tests added:
  - `test_solicitud_repository.py` — 7 new cases: handler empty for CREADA, populated for EN_PROCESO, preserved through FINALIZADA, empty for CANCELADA-from-CREADA, preserved for CANCELADA-from-EN_PROCESO, `get_by_folio` populates `atendida_por` with no extra SQL, `atendida_por is None` for CREADA detail. Existing `test_list_uses_at_most_three_queries` still passes (Subquery is inlined in the SELECT).
  - `test_revision_views.py` — 3 new cases: queue exposes "Atendida por" header and no "Acción"/"Revisar"; detail renders Solicitante card with matrícula + mailto link and the handler line for EN_PROCESO; handler line absent for CREADA.
  - `tests-e2e/test_solicitud_golden_path.py::test_personal_takes_and_finalizes_solicitud` extended: clicks the folio link (no longer "Revisar"), asserts queue's "Atendida por" header and absence of "Acción"/"Revisar", asserts Solicitante card visible with mailto link, asserts handler line surfaces after the atender transition. Captures `revision_detail_after_atender_{desktop,mobile}.png`.
- Templates:
  - `queue.html` — replaced `Acción` column with `Atendida por` (between Solicitante and Fecha; same `d-none d-lg-table-cell` responsive class). Empty cell renders `—` muted, not blank, for screen-reader clarity. Removed the trailing "Revisar" cell. Folio remains the navigation link.
  - `detail.html` — replaced subtitle `tipo · Solicitante: ...` with `tipo` only; added a conditional handler line under the heading (`Atendida por **name** (matrícula) · dd/mm/yyyy hh:mm`) shown only when `detail.atendida_por`. Added a Solicitante card in the right column above Historial: SOLICITANTE eyebrow (text-muted text-uppercase), full_name fw-semibold, matrícula muted, email as `mailto:`. Mobile reflow verified at 320×800.
- Verification:
  - Tier 1 (`make test`): 616 passed, 2 failed — both preexisting on main (`mentores backfill_migration` and `tests-e2e/test_field_autofill_golden_path[chromium]`), reproduced on the main checkout. No regressions introduced by 014.
  - Tier 2 (`pytest -m e2e tests-e2e/test_solicitud_golden_path.py::test_personal_takes_and_finalizes_solicitud`): passes; screenshots captured.
  - Postgres tier (`make e2e-postgres`): 15 e2e passed, only the same preexisting autofill failure. Subquery annotation works correctly under Postgres.
  - Visual verification: read `revision_queue_{desktop,mobile}.png`, `revision_detail_desktop.png`, and `revision_detail_after_atender_{desktop,mobile}.png`. Layout, contrast, mobile reflow, and accessibility (h1, mailto link, em-dash placeholder) all clean.
- Acceptance criteria from `plan.md` all met. Pending: `code-reviewer` agent dispatch on the section boundaries, then `/review` for final initiative validation.

## 2026-04-26 — code-reviewer round 1

- **Important — accepted:** `test_list_uses_at_most_three_queries` now seeds an EN_PROCESO row with a real atender historial entry before the `CaptureQueriesContext` block, so the new Subquery annotations actually resolve to a non-NULL value. The cap claim is now exercised in a populated state. The test additionally asserts `atendida_por_nombre == "Personal Q"` so a future regression that silently breaks the Subquery fails the test instead of passing silently.
- **Suggestion — accepted:** Hoisted inline `Estado as E` and `OrmHistorialRepository` imports from the body of the two new revision view tests to the file's import header (project convention); also collapsed the `E` alias since `Estado` is already imported at module scope.
- **Suggestion — declined (stylistic / not worth churn), with reasoning:**
  - Fakes O(N) historial scan in `_row`: behavior is correct, only the cost shape differs from the ORM. Test suites stay small, no measurable impact.
  - `&nbsp;·` in detail subtitle: cosmetic, current break behavior is fine at 320px (verified visually).
  - Helper functions vs pytest fixtures inside the new repo tests: matches the file's existing in-test-helper style (`_seed_creada` / `_atender`); converting would churn signatures without a real readability gain.
- Re-verified: `pytest solicitudes/lifecycle/tests/test_solicitud_repository.py solicitudes/revision/tests/test_revision_views.py` — 32/32 pass, including the strengthened query-count test.
