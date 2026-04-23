# 005-file-management — File Management — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25
- Initiative directory created (stub)
- Plan, status, and changelog files created as drafts pending `/brainstorm` + `/plan`
- Plan filled in: `ArchivoSolicitud` model (FORM/COMPROBANTE kinds), `FileStorage` ABC + `LocalFileStorage`, per-FieldDefinition validation, ZIP stored as-is, transaction-on-rollback file cleanup, replaces 004's discard placeholder.

## 2026-04-26
- Created isolated worktree stack: `docker-compose.worktree.yml` overrides ports (web 8000, db 5433) and project name `solicitudes-005` so this initiative runs alongside `main`'s dev stack.
- OQ-005-1 resolved: re-upload while CREADA replaces (delete prior row + bytes, then insert).
- Decision: global 10 MB cap applies to all archivos (form fields + comprobante). Per-field `max_size_mb` from `FieldDefinition` snapshot still enforced; smaller wins.
- OQ-005-3 resolved: rollback cleanup uses temp + `transaction.on_commit` rename (no orphans on rollback).
- Implemented: `ArchivoKind` enum + module constants (`solicitudes/archivos/constants.py`), `ArchivoSolicitud` model with partial unique constraints, registered in `solicitudes/models/__init__.py`.
- Migration: `solicitudes/migrations/0003_archivosolicitud.py` (clean — pre-existing label drift on `historialestado.estado_*` choices is out of scope and left for a separate cleanup).
- Tests/evidence: `manage.py migrate` applied cleanly; ORM smoke test confirmed table `solicitudes_archivosolicitud`, kind enum values, and both partial unique constraints.
- Implemented: `archivos/schemas.py` (`ArchivoDTO`, `ArchivoRecord`, `SolicitudContext`), `archivos/exceptions.py` (`ArchivoNotFound`, `FileTooLarge`, `FileExtensionNotAllowed`).
- Implemented: `archivos/storage/{interface,local}.py`. `LocalFileStorage` writes to a `.partial` sibling and registers `transaction.on_commit` to atomically rename to final on commit; thread-local pending list lets the view call `cleanup_pending()` from an `except` to delete leftover partials on rollback. 6/6 storage tests pass.
- Implemented: `archivos/repositories/archivo/{interface,implementation}.py` with `OrmArchivoRepository`. Added `get_solicitud_context(folio)` so the service can validate + authorise without touching `Solicitud` ORM. 11/11 repo tests pass (incl. partial-unique constraint coverage).
- Implemented: `archivos/services/archivo_service/{interface,implementation}.py`. Validates extension whitelist + size cap (smaller of per-field `max_size_mb` and global 10 MB), enforces comprobante rules, replaces prior FORM/COMPROBANTE on re-upload (delete row + bytes), authorises `open_for_download` for solicitante / responsible role / admin. 16/16 service tests pass with in-memory fakes.
- Implemented: `archivos/views/download.py` (`DownloadArchivoView`, `Content-Disposition: attachment`, RFC 5987 UTF-8 filename), `archivos/urls.py` mounted under `/solicitudes/archivos/`, `archivos/dependencies.py`. 5/5 view auth-matrix tests pass.
- Wired intake create view: replaced 004's NoOp warning with real archivo persistence inside an outer `transaction.atomic()` covering both the Solicitud insert and per-FILE archivo writes; on `AppError` or unexpected exceptions, `storage.cleanup_pending()` runs to delete partials.
- Templates: `templates/solicitudes/_partials/_archivos.html` (Bootstrap list-group, Bootstrap Icons, Spanish copy, accessible empty state). Included in `intake/detail.html` and `revision/detail.html`. Visual verification via Playwright at 1280×900 and 320×800 captured a multi-line `{# #}` rendering bug, fixed by switching to `{% comment %}` block; re-screenshot confirms clean rendering.
- E2E: 2 Tier-1 cross-feature tests (happy path + rollback-no-orphans) and 1 Tier-2 Playwright golden path (PDF upload, listed in detail, real download). All pass with `pytest.mark.django_db(transaction=True)` (required because `on_commit` doesn't fire in the default per-test rollback transaction).
- Quality gates: `ruff check .` (whole project) and `mypy .` (292 source files) both clean. Full `pytest` suite: 403/403 passing.

### Code-reviewer agent — round 1 (2026-04-26)
- **Critical 1 fixed**: replace-on-reupload was deleting prior file bytes synchronously inside the surrounding `transaction.atomic()`. On rollback the row was restored but the file was gone. Wrapped in `transaction.on_commit` so the prior bytes only disappear after the new write commits. Same fix applied to `delete_archivo`'s already-correct on_commit hook for symmetry. Regression test: `test_replace_on_reupload_leaves_prior_file_intact_on_rollback` (forces `OrmArchivoRepository.create` to raise mid-transaction; asserts prior file still on disk).
- **Critical 2 fixed**: archivos repo was reaching across features into `Solicitud`/`TipoSolicitud` ORM via `get_solicitud_context()`. Per `.claude/rules/django-code-architect.md` cross-feature rule, data access goes through the other feature's *service interface*. Refactored `ArchivoServiceImpl` to depend on `LifecycleService.get_detail` for solicitud context (estado, requiere_pago, pago_exento, form_snapshot, responsible_role, solicitante.matricula). Removed `get_solicitud_context` from `ArchivoRepository` interface; the impl no longer imports `Solicitud` and no longer joins `solicitud__tipo`. `ArchivoRecord` slimmed to storage fields only. Added `InMemoryLifecycleService` to `archivos/tests/fakes.py`; service tests now build a real `SolicitudDetail` via `_detail()` helper.
- **Important 1 fixed**: `intake/forms/intake_form.py::COMPROBANTE_MAX_SIZE_MB` raised from 5 to 10 to match the service-side global ceiling and RT-07; help-text now says "máx. 10 MB".
- **Important 2 addressed**: plan acceptance criterion #1 amended to specify 400 (form-level extension/size validators) vs 422 (service-level rejection). Pinned with `test_form_field_rejects_disallowed_extension_at_form_level`.
- **Important 3 fixed**: added `test_zip_stored_as_zip_and_round_trips` (uploads a real minimal ZIP, asserts stored extension, round-trips bytes through download).
- **Important 5 fixed**: storage's `_commit` hook now logs `archivos.commit_missing_partial` and `archivos.commit_rename_failed` with structured `extra` (folio, partial, final). Storage docstring documents the post-commit ENOSPC/EACCES limitation.
- **Important 6 fixed**: bare `except Exception:` removed from `intake/views/create.py`; replaced with `try/finally` around the `transaction.atomic()` block. `cleanup_pending()` runs in `finally` (no-op on success because the on_commit hook drains the pending list).
- **Important 4 deferred (with rationale, not fixed)**: reviewer suggested changing `FileStorage.save` to accept a chunk iterator instead of `bytes`. Pushed back: with the global 10 MB cap, in-memory cost is bounded; the interface change ripples through fakes and tests; the natural time to redesign for streaming is when an actual cloud-backed storage adapter (S3 / Azure Blob) lands. Documented as a TODO in the service implementation. Open for the user to override if they want it now.
- **Suggestions noted, not blocking**: deduplicate owner/responsible/admin authz between `intake/views/detail.py` and `_authorise_read` (lifecycle helper); explicit migration index name; module-level singleton storage. Captured for future cleanup.
- Re-verified: `ruff check .` clean, `mypy .` clean (292 files), `pytest`: **407/407** passing (4 new tests added — ZIP, form-level 400, replace-rollback, comprobante 10 MB cap), Tier-2 Playwright golden path still green.

## 2026-04-26 — Merge into main + SDD closeout

- Worktree torn down (isolated docker stack on ports 8000/5433 removed; project `solicitudes-005`).
- Stash brought across to `main` (which had advanced from `b87ba5c` to `76a3f97` with initiative 006 PDF Generation merged in between). Conflict resolved on `app/solicitudes/urls.py` — kept both 005's `archivos/` mount and 006's `admin/plantillas/` mount. Auto-merged template files (`intake/detail.html`, `revision/detail.html`) verified by reading the result: PDF download → Datos → Archivos → Historial/Acciones, no stray markers.
- Migration renumbered: `0003_archivosolicitud.py` → `0004_archivosolicitud.py`, dependency rewritten to chain off 006's `0003_remove_tiposolicitud_plantilla_id_and_more` (both initiatives had originally taken `0003`). Applied cleanly on the main dev DB; `migrate --check` exit 0.
- `docker-compose.worktree.yml` deleted (worktree-specific dev override; not useful on `main`).
- Safety stash dropped after verification.
- Full `pytest` against `main` post-merge: **457/457** passing.
- Specs:
  - Created `specs/apps/solicitudes/archivos/{requirements,design}.md` as the canonical reference for the feature (layer wiring, model + DTOs, service + repo + storage surfaces, transactional contract, post-commit failure mode, known limitations + follow-ups).
  - Updated `specs/apps/solicitudes/intake/design.md` — replaced the "until 005 ships" stub with the real wiring (outer atomic, FORM/COMPROBANTE dispatch, `try/finally` for `cleanup_pending`).
  - Updated `specs/flows/solicitud-lifecycle.md` — flipped 005 from "future" to "shipped"; replaced the file-discard failure-mode note with the partial-rename-on-rollback story.
  - Flipped 005 to **Done** in `specs/global/roadmap.md`.
  - Flipped status.md to **Done**, dated 2026-04-26.
- Initiative 005 closed.
