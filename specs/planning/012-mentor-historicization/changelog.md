# 012 — Mentor Catalog Historicization — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25
- Initiative created from an in-conversation exchange about mentor catalog history (option 2 — full historicization). Drafted `specs/apps/mentores/historicization/requirements.md` capturing WHAT/WHY; this `plan.md` carries the HOW.
- Key design decisions:
  - **Replace** `Mentor` (single-row-per-matrícula) with `MentorPeriodo` (one row per `(alta, baja)` range). No denormalized "current" cache table — current state is derived via the partial unique index + `fecha_baja IS NULL` predicate.
  - **Reactivation opens a new period**, never overwrites the old one. Each period captures its own `fuente` and `nota` so history is honest about provenance.
  - **`is_mentor` semantics preserved.** Returns the same boolean. Cross-feature regression suite (`mentores/tests/test_intake_wiring.py`) re-runs unmodified.
  - **`pago_exento` snapshot integrity preserved** because the snapshot lives on `Solicitud`, not the catalog.
  - **CSV importer outcomes preserved.** External counts unchanged; internal call switches to `add_or_reactivate`.
  - Three-step migration: schema add `MentorPeriodo` → backfill `0003` → drop `Mentor`. Empty-DB and populated-DB cases tested.
  - **New service methods** `get_history(matricula)` and `was_mentor_at(matricula, when)` for catalog-side reporting and audit. Future 009 (Reports & Dashboard) is the most likely first consumer.
  - **New detail view** at `/mentores/<matricula>/` renders the read-only timeline. List view stays minimal; each row links to the detail page.
- Open questions captured (OQ-012-1 through OQ-012-3) for legacy `desactivado_por`, in-place nota edits, and `list(only_active=False)` shape. None of them gate `/implement`.
- Roadmap updated with row 012, depends-on 008.
- Blocker noted: 008 must merge to `main` before /implement starts (the new model rewrites 008's table).
- **Plan revisions after code-reviewer pass (same day):**
  - **Critical fix #1 — `auto_now_add` footgun:** dropped `auto_now_add=True` from `MentorPeriodo.fecha_alta`. Django's `pre_save` for `auto_now_add` fires unconditionally on insert (even via `bulk_create`), which would have silently overwritten every backfilled `fecha_alta` with the migration timestamp — destroying the very history this initiative exists to keep. Repository now stamps `fecha_alta = timezone.now()` explicitly in `add_or_reactivate`. Data migration `0003` carries the original value verbatim. Added a regression test guarding this.
  - **Critical fix #2 — cross-feature regression test:** restated the "re-runs unmodified" claim. `test_intake_wiring.py` imports `from mentores.models import Mentor` and uses `Mentor.objects.*` — those break the moment migration `0004` drops the table. Plan now explicitly says the setup helpers update to `MentorPeriodo` while behavioral assertions stay identical. Same for `test_csv_importer.py`.
  - **Important fix — concurrent-reactivation race:** added `try/except IntegrityError` recovery to the `add_or_reactivate` pseudocode and a corresponding service test that mocks the repo to raise once. Without it, the partial unique index would surface as a 500 under simultaneous reactivation.
  - **Important fix — `was_mentor_at` boundary semantics:** pinned `[fecha_alta, fecha_baja)` half-open. Three explicit boundary tests added to status.md.
  - **Important fix — Postgres-only assumption:** documented in the model section. Status task added: confirm dev README/CLAUDE.md notes the partial-index + `DISTINCT ON` requirement.
  - **Important fix — migration `0004` is forward-only:** plan calls this out and requires the migration's docstring to declare it. Rolling back past `0002` destroys history; the reverse path re-creates an empty `Mentor` table for migration-graph completeness only.
  - **Status task split:** migration `0003` empty-DB and populated-DB cases promoted to separate visible checkboxes (was a parenthetical).
