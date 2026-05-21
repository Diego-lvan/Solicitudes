# plantilla_assets — Design

> Canonical reference for the plantilla_assets feature. Promoted from initiative **017** plan after `/review` cleared.

## Scope

The `plantilla_assets` feature owns:

- The `PlantillaAsset` ORM model — admin-uploaded images (PNG/JPG/WEBP) that plantillas reference by slug via `{{ assets.<slug> }}`.
- Two scopes: `global` (institutional reusable images — logo, sellos, firmas — available to every plantilla) and `plantilla` (specific to one plantilla, cascade-deleted with it).
- An admin CRUD surface at `/admin/plantilla-assets/` (list, upload, delete) plus a per-plantilla upload endpoint and a JSON feed (`list.json`) consumed by the plantilla editor.
- The `AssetService` interface that the `pdf` feature consumes to resolve `{{ assets.<slug> }}` into `data:<mime>;base64,...` URIs at render time.

The feature does **not** generate thumbnails, redimension, watermark, sign, or sanitize uploads beyond the validation pipeline below. It is admin-only end to end.

## Layer wiring

```
admin views (list / upload / upload_for_plantilla / delete / list_json)
        │
        ▼
AssetService (services/asset_service/interface.py)
        │
        ▼
AssetRepository (repositories/asset_repository/) ─── ORM (PlantillaAsset)
                                                ─── FileField storage (MEDIA_ROOT)
```

`plantilla_assets/dependencies.py` wires `OrmAssetRepository → DefaultAssetService` as factory functions. The `pdf` feature consumes the service interface (never the repository) — see `pdf/dependencies.py::get_pdf_service`.

## Data shapes

### Model (`solicitudes/models/plantilla_asset.py`)

`PlantillaAsset`:

- `id` UUIDv4 primary key.
- `slug` CharField(64) — derived from `nombre` by `slugify().replace("-","_")`. Reachable as `{{ assets.<slug> }}` in templates.
- `nombre` CharField(120) — display name.
- `scope` CharField(10) choices=(`global`, `plantilla`).
- `plantilla` FK → `PlantillaSolicitud`, nullable, `on_delete=CASCADE`, `related_name="assets"`. Only set when `scope=plantilla`.
- `imagen` FileField, `upload_to=plantilla_assets/%Y/%m/`.
- `mime_type` CharField(50) — persisted at upload so the resolver doesn't re-sniff at render.
- `size_bytes` PositiveIntegerField.
- `created_at` auto_now_add; `created_by` FK → user, on_delete=PROTECT.
- Ordering: `scope, nombre`.

Constraints:

- `unique_global_asset_slug` — UNIQUE(`slug`) WHERE `scope='global'`.
- `unique_plantilla_asset_slug` — UNIQUE(`plantilla_id`, `slug`) WHERE `scope='plantilla'`.
- `plantilla_asset_scope_consistency` — CHECK that `scope='global' ⇒ plantilla IS NULL` and `scope='plantilla' ⇒ plantilla IS NOT NULL`.

Migration: `0007_plantillaasset` (single `CreateModel`, no data migration).

### DTOs (`schemas.py`)

All frozen Pydantic v2 models.

- **`AssetScope`** StrEnum: `GLOBAL`, `PLANTILLA`.
- **`PlantillaAssetDTO`** — full asset detail (`id`, `slug`, `nombre`, `scope`, `plantilla_id`, `file_path`, `mime_type`, `size_bytes`, `created_at`, `created_by_id: str`). `created_by_id` is the matrícula (string) because the user model PK is `matricula`, not an autoincrementing integer.
- **`PlantillaAssetRow`** — trimmed for list views and the JSON feed (adds `thumb_url`, omits `file_path`).
- **`CreateAssetInput`** — service create input (`nombre`, `scope`, `plantilla_id?`, `file_bytes`, `original_filename`, `mime_type`, `created_by_id`).

## Service surface

`AssetService` (`services/asset_service/interface.py`):

| Method | Purpose | Raises |
|---|---|---|
| `get(asset_id)` | Full DTO. | `AssetNotFound` |
| `list_global()` | Rows for the global gallery. | — |
| `list_for_plantilla(plantilla_id)` | Rows scoped to a plantilla. | — |
| `list_for_render(plantilla_id \| None)` | DTOs for the PDF render context. Plantilla-scoped assets shadow globals with the same slug; service deduplicates by `slug`. | — |
| `create(input_dto)` | Validates + persists. Slug is derived from `nombre`; rejected if slugify returns empty. | `ImageTooLarge`, `InvalidImageType`, `DuplicateAssetSlug` |
| `delete(asset_id)` | Removes the row and the stored file (file deletion is best-effort). | `AssetNotFound` |

### Validation pipeline (defense in depth)

1. **Form-level** (`AssetUploadForm.clean_imagen`): extension ∈ `{.png, .jpg, .jpeg, .webp}`, declared MIME ∈ `{image/png, image/jpeg, image/webp}`, size ≤ `MAX_ASSET_BYTES` (2 MB).
2. **Service-level** (`_validate`): re-checks size, MIME, extension, and runs `PIL.Image.open(...).verify()` against the actual bytes — catches renamed payloads and corrupt files. Errors raised as `InvalidImageType`/`ImageTooLarge` (subclasses of `DomainValidationError`) so the middleware maps them to 422.
3. **Slug derivation** (`_derive_slug`): `slugify(nombre).replace("-","_")`. Non-slugifiable names (emoji-only, CJK-only) raise `InvalidImageType` rather than colliding to a sentinel.

SVG explicitly rejected in MVP (per initiative 017 OQ-2 closure) because the inline-iframe preview would execute embedded `<script>`/`on*=` attributes. Reopens as a future iniciativa if needed.

## Repository (`repositories/asset_repository/`)

`OrmAssetRepository` exposes `get`, `list_global`, `list_for_plantilla`, `list_for_render`, `create`, `delete`. Returns frozen DTOs only; never models or querysets. `Model.DoesNotExist` is wrapped to `AssetNotFound` at every site.

`create` persists via `row.imagen.save(filename, ContentFile(bytes), save=False)` then `row.save()`. `IntegrityError` is mapped to `DuplicateAssetSlug` by matching constraint names (`unique_global_asset_slug`, `unique_plantilla_asset_slug`) and falling back to the substrings `"unique constraint"`/`"duplicate key"` (cross-DB compatible: SQLite says "UNIQUE constraint failed", PostgreSQL says "duplicate key value violates unique constraint <name>").

## Exceptions (`exceptions.py`)

All inherit from `_shared.exceptions`:

- **`AssetNotFound`** (NotFound, 404).
- **`InvalidImageType`** (DomainValidationError, 422) — wraps `field_errors` so the form/view can attach the error to the `imagen` or `nombre` widget.
- **`ImageTooLarge`** (DomainValidationError, 422).
- **`DuplicateAssetSlug`** (Conflict, 409).

## Views

| URL | View | Methods | Purpose |
|---|---|---|---|
| `/admin/plantilla-assets/` | `AssetListView` | GET | Global gallery (grid of thumbnails + upload-modal trigger) |
| `/admin/plantilla-assets/upload/` | `AssetUploadView` | POST | Upload a global asset. Content-negotiates: JSON 201 with `{slug, snippet, thumb_url}` if `Accept: application/json`, otherwise redirect with flash. |
| `/admin/plantilla-assets/plantilla/<uuid>/upload/` | `AssetUploadForPlantillaView` | POST | Upload an asset scoped to one plantilla. Same JSON/HTML negotiation. |
| `/admin/plantilla-assets/<uuid>/delete/` | `AssetDeleteView` | GET, POST | Confirm + delete. |
| `/admin/plantilla-assets/list.json` | `AssetListJsonView` | GET | JSON feed `{global: [...], plantilla: [...]}` consumed by the plantilla editor's lateral panel. `plantilla` is empty unless `?plantilla_id=<uuid>` is present. |

All views require admin (`AdminRequiredMixin` from `usuarios.permissions`). Any other role gets 403.

## Cross-feature consumers

- **`solicitudes.pdf`** — `DefaultPdfService.__init__` accepts `asset_service: AssetService` via DI. Both `render_for_solicitud` and `render_sample` call `asset_service.list_for_render(plantilla_id)` and pass the resulting `dict[slug, data_uri]` to `build_render_context`/`build_synthetic_context` under the `"assets"` key. The data-URI helper is the module-public `asset_to_data_uri(dto)` (in `pdf/services/pdf_service/implementation.py`) — reads `MEDIA_ROOT / dto.file_path`, base64-encodes, returns `data:<mime>;base64,...`. Returns empty string when the file is missing so a deleted asset renders as `<img src="">` rather than crashing the render.
- **Plantilla editor preview** (also under `pdf`) — `PlantillaPreviewDraftView` and `PlantillaPreviewDraftPdfView` use the same `asset_to_data_uri` helper.

## Determinism

`asset_to_data_uri` is a pure function of `(file_bytes, mime_type)`. Under `freezegun` two renders of the same plantilla with the same asset produce byte-identical PDF bytes (pinned by a test in `pdf/tests/test_pdf_service.py::test_two_renders_with_same_asset_under_frozen_clock_are_byte_identical`).

## Tests

- `plantilla_assets/tests/factories.py` — `make_global_asset`, `make_plantilla_asset` + valid 1×1 PNG bytes.
- `plantilla_assets/tests/test_repositories.py` — 11 tests (real DB, constraints, scope consistency).
- `plantilla_assets/tests/test_services.py` — 7 tests with `InMemoryAssetRepository` (fake) covering slug derivation, validation pipeline, dedup logic, slug-empty rejection.
- `plantilla_assets/tests/test_forms.py` — 4 tests.
- `plantilla_assets/tests/test_views.py` — 9 tests (auth, JSON/HTML negotiation, list_json, delete confirm flow).

## Related Specs

- [requirements.md](./requirements.md)
- [planning/017-plantilla-editor](../../../planning/017-plantilla-editor/plan.md)
- [pdf/design.md](../pdf/design.md) — consumes `AssetService.list_for_render` and the `asset_to_data_uri` helper.
- [django-code-architect.md](../../../../.claude/rules/django-code-architect.md) — architectural rules.
