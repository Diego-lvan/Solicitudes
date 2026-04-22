# 006-pdf-generation — PDF Generation — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25
- Initiative directory created (stub)
- Plan, status, and changelog files created as drafts pending `/brainstorm` + `/plan`
- Plan filled in: `PlantillaSolicitud` model + admin CRUD + Django-template-engine substitution, on-demand WeasyPrint render, no PDF blob persisted, deterministic re-render under frozen clock. Resolves 003's `plantilla_id` placeholder by adding the FK migration.

## 2026-04-26
- Roadmap flipped to `In Progress`; status.md flipped to `In Progress`.
- Worktree `solicitudes-006` created on branch `initiative/006-pdf-generation` with `docker-compose.dev.override.yml` (project `solicitudes006`, ports nginx 8080/8443, db 5435, mailhog 8026) for parallel-run isolation.
- Implemented: `solicitudes/models/plantilla_solicitud.py` (`PlantillaSolicitud` — id, nombre, descripcion, html, css, activo, timestamps; ordered by nombre; `(activo, nombre)` index).
- Implemented: `tipo.plantilla_id` UUIDField → `tipo.plantilla` FK to `PlantillaSolicitud` (nullable, `on_delete=SET_NULL`, `related_name="tipos"`). Existing `plantilla_id` accessors keep working via Django's auto FK column attribute.
- Migration: `solicitudes/migrations/0003_remove_tiposolicitud_plantilla_id_and_more.py` (creates `PlantillaSolicitud`, drops the placeholder UUIDField, adds FK; sweeps unrelated estado-label drift).
- Tests: `pytest --ignore=tests-e2e` → 355/355 pass against the worktree's Postgres on port 5435. Tier 2 not run (pre-existing browser-install gap).
- Open decisions resolved: byte-identical re-render → true byte-identical (WeasyPrint metadata + fixed PDF /ID); "personal triggers PDF" → just GET the URL; no escudo.png shipped (admins embed images as inline base64); `STATIC_ROOT` still wired as WeasyPrint `base_url` as a safety net.
- Implemented: `solicitudes/pdf/schemas.py` (`PlantillaDTO`, `PlantillaRow`, `CreatePlantillaInput`, `UpdatePlantillaInput`, `PdfRenderResult`) and `solicitudes/pdf/exceptions.py` (`PlantillaNotFound` 404, `PlantillaTemplateError` 422 with `field_errors`, `TipoHasNoPlantilla` 409). Added `PlantillaRow` for list views (omits html/css blobs).
- Tests: `solicitudes/pdf/tests/test_schemas.py` (10) + `test_exceptions.py` (3) → 12/12 pass.
- Plantilla CRUD: `pdf/repositories/plantilla/{interface,implementation}.py`, `pdf/services/plantilla_service/{interface,implementation}.py` (template-syntax validation at save via `engines["django"].from_string`), `pdf/forms/plantilla_form.py` (Bootstrap monospace textareas), `pdf/views/{list,create,detail,edit,delete}.py`, `pdf/urls.py`, `pdf/dependencies.py`, mounted at `/solicitudes/admin/plantillas/`.
- Templates: `templates/solicitudes/admin/plantillas/{list,form,detail,confirm_deactivate}.html`, all WCAG-ish (skip link inherited from base, h1, required indicators, role="alert" errors, button hierarchy, table-responsive, empty state with icon+sentence+CTA).
- PDF rendering core: `pdf/context.py` (`slug_for_label` normalizing to underscores, `build_render_context` for `{solicitante, solicitud, valores, now, firma_lugar_fecha}` with America/Mexico_City TZ, `assemble_html` wrapper), `pdf/services/pdf_service/{interface,implementation}.py` (DefaultPdfService composes lifecycle + plantilla repo + user service + WeasyPrint). Authz matrix: solicitante only on FINALIZADA; personal/admin any estado.
- Determinism: `_shared/pdf.render_pdf` extended with `pdf_identifier` parameter; PdfService passes `folio.encode("utf-8")` so two renders under freezegun are byte-identical (verified by `test_two_renders_under_frozen_clock_are_byte_identical`).
- Schema change: `TipoSolicitudRow.plantilla_id: UUID | None = None` (default) — exposed via `OrmTipoRepository._to_row` and `OrmSolicitudRepository`'s `SolicitudDetail.tipo` builder. Backwards-compatible (default None). Comment updated.
- Hookups: tipo create/edit views populate `TipoForm(plantilla_choices=...)` with active plantillas; `_helpers.build_*_input` thread `plantilla_id` into Create/UpdateTipoInput. `templates/solicitudes/admin/tipos/form.html` adds plantilla select. `templates/solicitudes/revision/detail.html` and `intake/detail.html` show contextual "Generar PDF" / "Descargar PDF" links gated on `detail.tipo.plantilla_id` (and FINALIZADA + is_owner for the alumno view).
- Migration noise: 0003 also alters `historialestado.estado_*` and `solicitud.estado` choices to update label casing ("En Proceso" → "En proceso"). Pre-existing label drift swept up by makemigrations; no behavioural change.
- **Migration cutover decision (acknowledged after review):** 0003 does `RemoveField('tiposolicitud','plantilla_id')` followed by `AddField('tiposolicitud','plantilla', ForeignKey)`. The plan said "convert" but no `RunPython` data step copies UUIDs across, so any value stored in the 003 placeholder column is dropped. Accepted because the placeholder column has been NULL in every environment to date (dev only, no real plantillas existed before 006). Pre-launch destructive cutover, not a runtime concern. Documented here so a future operator reading the migration doesn't assume the conversion preserves data.
- Tests added: `pdf/tests/test_plantilla_repository.py` (8), `test_plantilla_service.py` (4), `test_context.py` (6), `test_pdf_service.py` (7), `test_views.py` (10), `factories.py`. Total pdf-feature tests: 47.
- Quality gates: ruff clean, mypy clean across 298 source files, pytest 402 passed in 3.4s.
- Live verification: brought up worktree stack (`solicitudes006` project, web on :8001), seeded admin + plantilla "Constancia de Estudios" + tipo + finalizada solicitud SOL-2026-99999. Browser fetch of `/solicitudes/SOL-2026-99999/pdf/` returned 200 application/pdf 7473 bytes; intake/detail.html showed the "Descargar PDF" button conditionally; admin views (list, form, detail) screenshot-verified at 1280×900 and 320×800 via Playwright MCP. Screenshots at `/tmp/006-screenshots/`.

## 2026-04-26 (review pass)

Code-reviewer dispatched against `b87ba5c..HEAD` (worktree). Findings addressed:

- **Critical (acknowledged):** 0003 migration is a destructive cutover — `RemoveField` then `AddField` rather than a `RunPython`-backed conversion. Accepted because the placeholder column has been NULL in every environment to date. Documented above so a future operator doesn't read the migration as data-preserving.
- **Important (fixed):** Implemented the plan-spec'd sample-PDF preview on the plantilla detail page. New `PdfService.render_sample(plantilla_id)` (synthetic context, deterministic via `pdf_identifier=plantilla_id`), new `PlantillaPreviewView` mounted at `/admin/plantillas/<id>/preview.pdf` (admin-only, inline disposition), and an `<iframe>` embed on `templates/.../plantillas/detail.html`. Added view tests (admin 200/inline/%PDF, alumno 403). Live preview returned 200 application/pdf 7303 bytes.
- **Important (fixed):** Added `test_docente_non_owner_cannot_render_finalizada` to pin the authz matrix. A future refactor that broadens the personal set to include DOCENTE will fail this test.
- **Important (fixed):** Constrained the PDF download URL with `re_path(r"^(?P<folio>[A-Z]+-\d{4}-\d{4,})/pdf/$", ...)` so a folio literally equal to "pdf" can't collide with the intake catch-all.
- **Suggestion (fixed):** Replaced `# type: ignore[attr-defined]` on `tipo_form.py` choices assignment with `cast(forms.ChoiceField, ...).choices = choices`.
- **Suggestion (fixed):** Documented in `DefaultPdfService` docstring that determinism holds within an environment, not across deployments — `STATIC_ROOT`-resolved assets can vary; plantillas requiring byte-stability should embed images as `data:` URIs (already the OQ-006-1 resolution).
- **Suggestion (push back):** Reviewer suggested `Field(alias="bytes")` on `PdfRenderResult.bytes_`. Declined: the trailing underscore is the Python idiom for shadowing a builtin and is documented in the schema docstring; switching to an alias adds a serialisation surface that no consumer reads (we never JSON-serialise `PdfRenderResult` — it's a transport between service and view and the bytes go straight into `HttpResponse`). Net change: more API surface for no gain.

Final gates after fixes: ruff clean, mypy 299 source files clean, pytest 405 passed in 5.25s.

## 2026-04-26 (second review pass)

Code-reviewer re-dispatched on the patched tree. Assessment: **"Ready to proceed."**

Three Suggestions returned; addressed:

- **Suggestion (fixed):** `_synthetic_context` had been placed in `pdf_service/implementation.py` and imported the private `_firma_lugar_fecha` from `pdf/context.py`. Promoted to a public helper `build_synthetic_context(now=...)` inside `pdf/context.py` next to `build_render_context`, and updated `DefaultPdfService.render_sample` to import and call it. No more cross-module reach into `_private` symbols.
- **Suggestion (already done):** Reviewer asked for `title` on the iframe. Already present (`title="Vista previa de la plantilla"`).
- **Suggestion (declined as optional):** Parametrized `RESPONSABLE_PROGRAMA` matricula-mismatch test for symmetric matrix coverage. Reviewer flagged as optional; the asymmetry is documented in the docstring and the existing personal-can-render tests already cover the broad direction. Declined for scope.

Final gates: ruff clean, mypy 299 source files clean, pytest 405/405 in 3.02s.

## 2026-04-26 (post-review hardening)

Three follow-ups discovered after the formal review passes, applied directly on `main`:

- **Sidebar wiring:** `templates/components/sidebar.html` gained an admin-only "Plantillas de PDF" link under the existing **Catálogo** group, between "Tipos de solicitud" and "Mentores". Same `nav-link app-sidebar-link` pattern, `bi-file-earmark-text` icon, `'/solicitudes/admin/plantillas' in request.path` active-state test.
- **`X-Frame-Options` regression on `PlantillaPreviewView`:** Django's default `XFrameOptionsMiddleware` set `X-Frame-Options: DENY`, which silently blanked the iframe embed on `templates/.../plantillas/detail.html`. Fixed by decorating the view's `dispatch` with `xframe_options_sameorigin` so the response carries `SAMEORIGIN` for that one endpoint only. Added regression assertion `assert resp["X-Frame-Options"].upper() == "SAMEORIGIN"` to `test_admin_can_preview_plantilla`. Lesson: the prior "live verified" claim was based on a JS `fetch()`, not a real iframe load — Playwright screenshots showed the frame chrome but didn't rasterize PDF inside it, so the block went unnoticed.
- **Plantilla seed data:** Extended `app/solicitudes/seeders.py` with two `PlantillaSolicitud` rows ("Constancia de Estudios" and "Solicitud de Cambio de Programa") and wired them to the corresponding seeded tipos via `tipo.plantilla = plantilla; tipo.save()`. Idempotent via `update_or_create`; `--fresh` flow extends to the new rows.

Gates after these: 3 `E501` line-too-long lint regressions in the seeder CSS strings (since fixed by reflowing); mypy 299 files clean; `pytest --ignore=tests-e2e` 412/412 in 24s.

Demonstration plantillas created at runtime (not seeded) during PDF-flexibility validation: "Horario Académico (test)" (single-page, navy table band, highlighted weekday cell) and "Constancia de Situación Fiscal (test)" (2-page, black header band, HACIENDA/SAT wordmarks, embedded SVG QR + barcode placeholders, `@page { @bottom-right }` page numbering, kv tables). Both rendered byte-stably; documented elsewhere as proof WeasyPrint can reproduce arbitrary fixed-format institutional documents from HTML+CSS alone.
