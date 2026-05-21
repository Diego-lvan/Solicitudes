# plantilla_assets — Requirements

> WHAT/WHY for this feature. The cohesive user-facing rationale (editor UX + image library bundled into one cohesive flow) lives in the umbrella feature folder. This file scopes the requirements that are specific to the asset module.

## Purpose

Hosts admin-uploaded images (institutional logo, sellos, firmas, per-plantilla figures) on the server's own filesystem so plantillas can embed them deterministically as `data:` URIs without depending on public external URLs. Replaces the previous workflow where plantilla authors could only reference external `https://` URLs (broken when the source site went down, slow at render time, impossible for internal-only assets).

## User stories

See [`specs/apps/solicitudes/plantilla_editor/requirements.md`](../plantilla_editor/requirements.md) — the asset-library stories ("Como admin quiero subir imágenes al servidor...", "Como admin quiero también subir imágenes específicas a una plantilla...", "Como admin quiero subir una imagen sin salir del editor...") are part of the same brainstorm/initiative output.

## Constraints

- **Admin-only** end to end. Any other role receives 403.
- **Allowed formats**: PNG, JPG, WEBP only. SVG explicitly rejected in MVP (would execute inline scripts in the preview iframe).
- **Max size**: 2 MB per asset (configurable via `plantilla_assets/constants.py::MAX_ASSET_BYTES`). Tighter than the 10 MB RT-07 limit for solicitud attachments because asset bytes get embedded in every PDF.
- **Determinism preserved**: the PDF resolver reads the file from `MEDIA_ROOT`, base64-encodes, and returns `data:<mime>;base64,...`. Identical inputs under a frozen clock produce byte-identical PDFs.
- **Graceful degradation on deletion**: if an asset is deleted but a plantilla still references its slug, the PDF renders `<img src="">` (browser-defined broken-image glyph) rather than crashing.
- **Two scopes**: `global` (visible to every plantilla editor; institutional reusable images) and `plantilla` (visible only when editing that plantilla; cascade-deleted with the plantilla).
- **Slugs are admin-chosen**: derived from the asset's `nombre` (`slugify(nombre).replace("-","_")`). Collisions within a scope raise `DuplicateAssetSlug` (409); non-slugifiable names raise `InvalidImageType`.

## Non-goals

- Sanitization, sandboxing, or any kind of SVG support in v1.
- Thumbnail generation. Stored bytes are served directly.
- Cross-deployment or cross-instance asset sync.
- A public read endpoint. The gallery is admin-only; the preview iframe and the rendered PDF embed bytes inline.

## Related modules

- → `apps/solicitudes/pdf` — consumes `AssetService.list_for_render` and the `asset_to_data_uri` helper for both per-solicitud and synthetic-context (preview) renders.
- → `apps/solicitudes/plantilla_editor` (umbrella feature folder) — drives the user-facing requirements.

## Open questions

None at initiative closeout (2026-05-17). See planning/017-plantilla-editor/plan.md §15 for the resolutions of OQ-1..OQ-5.
