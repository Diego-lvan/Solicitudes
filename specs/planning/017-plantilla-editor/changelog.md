# 017 — Plantilla Editor & Asset Library — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-05-17
- Initiative created from `/brainstorm` → `/plan` handoff.
- Brainstorm output at `specs/apps/solicitudes/plantilla_editor/requirements.md`.
- Key decisions captured during brainstorm:
  - Single initiative (editor UX + live preview + image library bundled).
  - Layout: 3-column editor split (panel / textarea / iframe preview), CSS collapsible.
  - Live preview is HTML (debounced 500ms via `POST /admin/plantillas/preview/`); "Ver PDF real" button generates WeasyPrint render on demand in new tab.
  - Image library: dual-scope (`global` + `plantilla`), embedded as `data:` URI to preserve PDF determinism.
  - In-place modal upload from the editor (no full page navigation).
  - New feature folder `solicitudes/plantilla_assets/` for the catalog; `solicitudes/pdf/` extended (does not own assets).
- Open questions closed in plan.md §15:
  - OQ-1: single session key, last-write-wins.
  - OQ-2: reject SVG in MVP; PNG/JPG/WEBP only.
  - OQ-3: tab "Campos" populated only via `?tipo_id=` querystring; no persisted default.
  - OQ-4: show `created_by`/`created_at` columns in global gallery.
  - OQ-5: no hard cap on global assets; UI scrollable.

## 2026-05-17 (implementation)

- Model + migration: `PlantillaAsset` with constraints (`unique_global_asset_slug`, `unique_plantilla_asset_slug`, `plantilla_asset_scope_consistency`). Applied as `0007_plantillaasset`.
- Feature `solicitudes/plantilla_assets` complete: schemas (Pydantic v2), exceptions (inherit `_shared`), constants (`MAX_ASSET_BYTES=2MB`, `ALLOWED_MIME` PNG/JPG/WEBP), forms (`AssetUploadForm`), repository (`OrmAssetRepository` mapping IntegrityError → `DuplicateAssetSlug`), service (`DefaultAssetService` with slug derivation + Pillow validation + dedup logic), admin views (list / upload-global / upload-per-plantilla / delete / list.json, with JSON/HTML content negotiation), URL namespace `plantilla_assets`.
- Discovered during integration: user PK is `matricula` (CharField), so `created_by_id: str` (not int). Linter auto-corrected DTOs and interface accordingly.
- PDF service extended: takes `asset_service: AssetService` via DI; `_dto_to_data_uri(dto)` reads file from `MEDIA_ROOT`, base64-encodes, returns `data:<mime>;base64,...`. Missing files render as empty string (graceful degradation). Both `render_for_solicitud` and `render_sample` resolve assets into the render context.
- PDF context extended: both `build_render_context` and `build_synthetic_context` accept `assets: dict[str, str] | None = None`, injected under `"assets"` key.
- New endpoints: `POST /admin/plantillas/preview/` (renders HTML+CSS+synthetic context to iframe-safe HTML; CSP `default-src 'none'`, sandbox via X-Frame-Options); `GET /admin/plantillas/preview/pdf/` (reads session draft via key `plantilla_draft`, returns inline application/pdf). Template syntax errors return 200 + inline red banner (no 500).
- Tipo fields JSON endpoint: `GET /admin/tipos/<uuid>/fields.json` returns `{fields: [{slug, label, type}]}` admin-only. Used by the editor's "Campos" tab when `?tipo_id=` is present.
- Editor UI rewrite: `templates/solicitudes/admin/plantillas/form.html` → 3-column layout (panel / editor / preview). New partials `_assets_panel.html` (tabs Variables/Campos/Imágenes, click-to-insert chips) and `_asset_upload_modal.html` (in-place upload). Alpine component `static/js/plantilla_editor.js` handles cursor-aware insertion, 500ms debounced live preview via fetch, "Ver PDF real" opens new tab, modal upload with JSON negotiation.
- Sidebar: added "Imágenes de plantillas" entry under Catálogo (admin only) in `templates/components/sidebar.html`.
- Verification via Playwright in development: editor renders cleanly at 1280×900 and 320×800; click-to-insert tested (24 chars added at cursor 0); live preview iframe srcdoc populated; upload returns 201 JSON with thumb URL + snippet; asset resolves to data: URI in preview; full PDF roundtrip returns 3409 bytes of application/pdf.
- Closed open questions:
  - SVG support deferred (PNG/JPG/WEBP only). Reopens as future iniciativa if needed.
  - Tab "Campos" populated only via `?tipo_id=` querystring; no persisted default.
  - Single session key `plantilla_draft`, last-write-wins.
- OQ left from plan §15 unchanged (no new open questions emerged during implementation).

## 2026-05-17 (review + closeout)

- Dispatched `code-reviewer` agent over the full uncommitted diff. Findings: 0 Critical, 5 Important, 6 Suggestions.
- Critical: none.
- Important fixes applied:
  1. **Bare `except Exception:` removed** in `_resolve_assets` (pdf service), `preview_draft`, and `preview_draft_pdf` — narrowed to `_shared.exceptions.AppError` so DB/infra errors bubble to middleware instead of being silently swallowed. Direct architecture-rule remediation (django-code-architect.md §CRITICAL VIOLATIONS).
  2. **`_dto_to_data_uri` promoted to public `asset_to_data_uri`** — was being imported across the layer boundary (private helper consumed by view files). Renamed in-place; one stale import in `pdf/tests/test_pdf_service.py` updated.
  3. **IntegrityError → DuplicateAssetSlug detection hardened** — instead of substring matching `"unique"`/`"duplicate"`, matches the actual constraint names (`unique_global_asset_slug`, `unique_plantilla_asset_slug`) with the original substring patterns as a portable fallback. Robust against PostgreSQL/SQLite/locale variation.
  4. **`_derive_slug` no longer falls back to a sentinel** — if `slugify(nombre)` is empty (emoji-only, CJK-only names), the service raises `InvalidImageType` with a Spanish field error pointing the admin at `nombre`, instead of silently using `"imagen"` and producing a confusing later `DuplicateAssetSlug`.
  5. **Removed unused f-string prefix** in `_validate` size-error path.
- Important #1 (trusted-admin template surface) — accepted as-is and documented in `pdf/design.md` under "Plantilla editor surface (initiative 017) → Trusted-admin template surface". Future hardening pass tracked in design.md, not blocking v1.
- Suggestion: removed dead `{{ … |json_script }}` blocks from `form.html`. The JS consumes the chips server-rendered, no JSON island needed.
- Suite re-run: 785 tests pass (full repo, excluding the unrelated pre-existing `test_home_redirects_anonymous_to_login` failure that asserts `/auth/login` instead of the new `/auth/dev-login` picker — landed in commit `43ad8b6`, not part of this initiative).
- E2E manual verification re-run in browser: editor loads, preview live refresh works, click-to-insert at cursor works, asset upload via XHR returns 201 + JSON, asset resolves to `data:` URI in preview, "Ver PDF real" returns valid `application/pdf` (3409 bytes).
- Spec closeout completed: `pdf/design.md` extended with asset resolution + preview surface; new `plantilla_assets/{requirements,design}.md`; roadmap row flipped to `Done`; `status.md` checklist all checked.
- Initiative complete.
