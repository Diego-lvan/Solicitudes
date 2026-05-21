# 017 — Plantilla Editor & Asset Library — Status

**Status:** Done
**Last updated:** 2026-05-17

## Checklist

### Model & migration
- [x] `app/solicitudes/models/plantilla_asset.py` (`PlantillaAsset` + constraints).
- [x] Registered in `app/solicitudes/models/__init__.py`.
- [x] Migration `0007_plantillaasset.py` generated and applied.

### `plantilla_assets` feature scaffolding
- [x] `constants.py` — `MAX_ASSET_BYTES`, `ALLOWED_MIME`, `ALLOWED_EXT`.
- [x] `schemas.py` — `AssetScope`, `PlantillaAssetDTO`, `PlantillaAssetRow`, `CreateAssetInput` (created_by_id: str).
- [x] `exceptions.py` — `AssetNotFound`, `InvalidImageType`, `ImageTooLarge`, `DuplicateAssetSlug`.
- [x] `permissions.py` — re-export `AdminRequiredMixin`.

### `plantilla_assets` repository
- [x] `repositories/asset_repository/interface.py` — `AssetRepository` ABC.
- [x] `repositories/asset_repository/implementation.py` — `OrmAssetRepository` with `IntegrityError → DuplicateAssetSlug` mapping.

### `plantilla_assets` service
- [x] `services/asset_service/interface.py` — `AssetService` ABC.
- [x] `services/asset_service/implementation.py` — `DefaultAssetService` with slug derivation, Pillow validation, dedup logic.

### `plantilla_assets` forms
- [x] `forms/asset_form.py` — `AssetUploadForm`.

### `plantilla_assets` views, urls, deps
- [x] `views/admin.py` — list, upload (global + per-plantilla), delete, list.json. JSON/HTML negotiation on upload.
- [x] `urls.py` — namespace `plantilla_assets`.
- [x] `dependencies.py` — factories.
- [x] Wired into `app/solicitudes/urls.py`.

### Templates: assets gallery
- [x] `app/templates/solicitudes/admin/plantilla_assets/list.html` — grid + upload modal.
- [x] `app/templates/solicitudes/admin/plantilla_assets/confirm_delete.html` — confirm + warning.

### PDF context + service extension
- [x] `app/solicitudes/pdf/context.py` — accepts `assets: dict[str, str]`.
- [x] `app/solicitudes/pdf/services/pdf_service/implementation.py` — `_dto_to_data_uri` helper, asset_service DI, resolved in both render flows.
- [x] `app/solicitudes/pdf/dependencies.py` — wires `get_asset_service()` into `get_pdf_service()`.

### Preview draft endpoints
- [x] `app/solicitudes/pdf/views/preview_draft.py` — POST with CSP + sandbox-friendly response, inline error banner.
- [x] `app/solicitudes/pdf/views/preview_draft_pdf.py` — GET reads session draft, returns PDF.
- [x] Routes in `app/solicitudes/pdf/urls.py`.

### Tipos fields JSON endpoint
- [x] `app/solicitudes/tipos/views/fields_json.py` + route `solicitudes:tipos:fields_json`.

### Editor template + JS
- [x] Rewritten `app/templates/solicitudes/admin/plantillas/form.html` to 3-column layout.
- [x] `app/templates/solicitudes/admin/_partials/_assets_panel.html`.
- [x] `app/templates/solicitudes/admin/_partials/_asset_upload_modal.html`.
- [x] `app/static/js/plantilla_editor.js` — Alpine component.
- [x] Both create.py and edit.py views pass `panel_variables()` and `tipo_id` to template.
- [x] CSS rebuilt via `make css`.

### Sidebar & cross-feature touches
- [x] `app/templates/components/sidebar.html` — "Imágenes de plantillas" entry for admin.

### E2E verification (manual via Playwright)
- [x] Editor renders correctly at 1280×900 desktop (3-column layout).
- [x] Editor renders correctly at 320×800 mobile (stacked layout, no horizontal scroll).
- [x] Click-to-insert: chip "Nombre" inserts `{{ solicitante.nombre }}` at cursor position 0; textarea length grows by 24 chars.
- [x] Live preview iframe srcdoc populated (1339 bytes for default plantilla) on load.
- [x] Asset upload via XHR returns 201 + JSON `{slug, snippet, thumb_url}`.
- [x] Galería `/admin/plantilla-assets/` lists uploaded asset.
- [x] Preview endpoint resolves `{{ assets.<slug> }}` to `data:image/png;base64,...` URI.
- [x] `preview/?persist=1` + `preview/pdf/` returns `application/pdf` (3409 bytes).

### Automated tests (delegated to subagent)
- [x] 44 new tests added across 7 files. Total: 85 pass in the targeted suites, 785 pass in the full repo suite (1 pre-existing failure in `_shared/tests/test_home_view.py::test_home_redirects_anonymous_to_login` is unrelated — it asserts `/auth/login` but the dev-login picker now redirects to `/auth/dev-login`, a chore that landed in `43ad8b6`).
- [x] Unit + view tests for `plantilla_assets` (repositories, services, forms, views): 11+7+4+9 tests.
- [x] PDF service extension tests: 4 tests (assets in context, missing-slug-no-crash, `_dto_to_data_uri` empty-on-missing-file, byte-identical under freeze_time).
- [x] Preview endpoints tests: 6 tests.
- [x] Tipos fields JSON test: 3 tests.

### Spec closeout
- [x] Updated `specs/apps/solicitudes/pdf/design.md` — assets resolution section, preview endpoints, trusted-admin-surface note, cross-feature wiring.
- [x] Created `specs/apps/solicitudes/plantilla_assets/{requirements,design}.md`.
- [x] Flipped roadmap.md row 017 to `Done`.
- [x] Final entry in `changelog.md`.

## Blockers

None.

## Live-verified behavior (E2E summary)

End-to-end smoke completed in development environment with admin role:

- `GET /admin/plantillas/<id>/editar/` renders the 3-column editor.
- `POST /admin/plantillas/preview/` returns iframe-safe HTML with synthetic context interpolated. `Content-Security-Policy` and `X-Frame-Options` set.
- `POST /admin/plantillas/preview/?persist=1` + `GET /admin/plantillas/preview/pdf/` returns valid `application/pdf` bytes.
- `POST /admin/plantilla-assets/upload/` with `Accept: application/json` returns `{slug, snippet, thumb_url}` and the asset is queryable via `GET /admin/plantilla-assets/list.json`.
- A plantilla referencing `{{ assets.<slug> }}` resolves to a `data:image/png;base64,...` URI at render time.
- Sidebar shows "Imágenes de plantillas" under Catálogo (admin only).

[P] = can run in parallel
