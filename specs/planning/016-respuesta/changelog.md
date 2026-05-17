# 016 — Response Files & Comments — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-05-15
- Initiative created.
- Source: `/brainstorm` produced `specs/apps/solicitudes/respuesta/requirements.md` after a six-question clarification arc covering who-uploads-and-when, fate of the template PDF, comments-per-batch, append-only, solicitante visibility window, and tipo scope.
- Key decisions:
  - **Approach B**: dedicated `solicitudes/respuesta/` vertical slice (over extending `archivos` or piggybacking on lifecycle `HistorialEstado`).
  - **Upload window**: `EN_PROCESO` only; not `CREADA`.
  - **Append-only at the app layer**: no in-app delete/replace; Django admin is the escape hatch.
  - **Batch shape**: comentario (≤2000 chars) + up to 10 files; not both empty.
  - **Solicitante visibility**: hidden until `FINALIZADA`.
  - **PDF authz amendment**: drop the owner-FINALIZADA download branch; alumno button removed; personal button relabeled to "Descargar borrador".
  - **No new notification** on upload; the existing FINALIZADA email is unchanged.
  - **File rules**: mirror `archivos` (10 MB cap, existing extension allow-list). Constants duplicated locally instead of extracting a shared util.
  - **Storage**: reuse `archivos.dependencies.get_file_storage` (acceptable cross-feature factory import; FileStorage refactor to `_shared` deferred).
- Files created: `plan.md`, `status.md`, this changelog, `specs/apps/solicitudes/respuesta/requirements.md` (from brainstorm), `specs/apps/solicitudes/respuesta/design.md` (placeholder).
- Roadmap updated: row 016 added with status `Not Started`.

## 2026-05-15 — Implementation

- Models: `RespuestaSolicitud` and `ArchivoRespuesta` added under `app/solicitudes/models/`, migration `0006_respuestasolicitud_archivorespuesta_and_more.py` created and applied.
- Feature scaffold: `app/solicitudes/respuesta/` with `constants.py`, `exceptions.py` (6 classes), `schemas.py` (`UploadedFile`, `CreateRespuestaInput`, `ArchivoRespuestaDTO`, `ArchivoRespuestaRecord`, `RespuestaDTO`), `repositories/respuesta/{interface,implementation}.py`, `services/respuesta_service/{interface,implementation}.py`, `forms/respuesta_upload_form.py`, `views/{personal,shared}.py`, `urls.py`, `dependencies.py`. URLs mounted from `solicitudes/urls.py` so namespace is `solicitudes:respuesta:{create,download}`.
- PDF authz amendment: `pdf_service._authorise` no longer allows owner downloads (initiative 016 rule). Existing tests in `pdf/tests/test_pdf_service.py` and `pdf/tests/test_views.py` rewritten — owner/FINALIZADA happy path replaced with personal happy path; owner now expected 403 in any estado; `test_no_plantilla_returns_409_for_personal` switched to a personal requester so the no-plantilla path is reachable before the new authz guard.
- Templates: `intake/detail.html` lost the "Descargar PDF" button; gained "Documentos de respuesta" section gated on `estado == FINALIZADA AND respuestas`. `revision/detail.html` relabel "Generar PDF" → "Descargar borrador"; gained "Adjuntar respuesta" card (visible only in `EN_PROCESO`) and "Respuestas entregadas" listing card. New shared partial `_partials/_respuestas.html` reused by both. Cleaned up pre-existing leaked `{# … #}` comment in `components/alerts.html` (the multi-line opener was rendering literally).
- View context: `intake/views/detail.py` and `revision/views/detail.py` now populate `respuestas` (and `upload_form` on revision) via `respuesta.dependencies.get_respuesta_service`.
- Tests: 56 new respuesta tests (`test_schemas`, `test_exceptions`, `test_forms`, `test_repository` real-DB, `test_service` with `RecordingFileStorage` + `InMemoryRespuestaRepository` + `InMemoryLifecycleService`, `test_views` HTTP + Tier 1 cross-feature integration). PDF test suite kept green (53 tests). Full suite: 724 pass + 1 pre-existing unrelated failure (`_shared/tests/test_home_view.py::test_home_redirects_anonymous_to_login`, expects `/auth/login` while config points to `/auth/dev-login`).
- Tier 2 Playwright: `tests-e2e/test_respuesta_golden_path.py` covers atender → upload 2 files + comment → finalizar → alumno-side download. Screenshots captured at 1280×900 and 320×800 under `/tmp/screenshots-016/`; visual verification confirmed sidebar, hairline borders, Lucide icons, monochrome aesthetic, mobile reflow at 320 px, no horizontal scroll, no purple gradients or AI-look tells.

Open question OQ from plan resolved: `LocalFileStorage.save` ignores `suggested_name` beyond extension; the storage layout stays flat (`media/solicitudes/<folio>/<uuid>.<ext>`). No subdirectory fallback needed.

## 2026-05-17 — Closeout

- `/review` ran clean against the full initiative — no CRITICAL, no WARNING items. Full non-e2e suite: 724 pass + 1 pre-existing unrelated failure (`_shared/tests/test_home_view.py`). Tier 2 Playwright golden path passes.
- Design docs promoted:
  - `specs/apps/solicitudes/respuesta/design.md` — full canonical doc (layer wiring, models, DTOs, service surface, visibility matrix, views/URLs, template references, tests, cross-feature consumers).
  - `specs/apps/solicitudes/pdf/design.md` — authz matrix amended (owner branch removed); templates section updated for the relabel; cross-feature consumers gained a `solicitudes.respuesta` entry.
  - `specs/apps/solicitudes/revision/design.md` — `detail.html` description gained the 016 paragraph (eyebrows, hairline divider, "Adjuntar respuesta" / "Respuestas entregadas" cards) and Related Specs gained 016 + respuesta.
  - `specs/apps/solicitudes/intake/design.md` — `detail.html` description gained the 016 paragraph ("Tu petición" / "Respuesta de la institución" groups, removed PDF affordance) and Related Specs gained 016 + respuesta.
- `specs/flows/solicitud-lifecycle.md` — appended the 016 cross-app row describing the personal-side delivery step, visibility window, no-new-notification rule, and the pdf affordance reframe.
- `specs/global/roadmap.md` — row 016 flipped to `Done`.
- `specs/planning/016-respuesta/status.md` — top status line flipped to `Done`, last-updated bumped, closeout checkboxes marked.

Initiative closed.
