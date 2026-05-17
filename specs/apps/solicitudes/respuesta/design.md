# respuesta — Design

> Canonical reference for the response-upload feature. Updated after initiative 016 closed.

## Scope

The `respuesta` feature owns the personal-side delivery of a solicitud's deliverable:

- The `RespuestaSolicitud` ORM model (the **batch**: actor + actor_role + comentario + timestamp).
- The `ArchivoRespuesta` ORM model (one **file** in a batch).
- The HTTP surface for **creating a batch** (`POST /solicitudes/<folio>/respuestas/nueva/`) and **downloading a file** (`GET /solicitudes/<folio>/respuestas/<respuesta_uuid>/archivos/<archivo_uuid>/`).
- The **visibility matrix** that gates batch and file access by requester role + solicitud estado.

It does **not** own:

- The auto-rendered template PDF (that's `pdf/`). After 016, the PDF is a *draft* for personal/admin; the solicitante never downloads it.
- File-storage mechanics. Bytes go through `archivos/storage/FileStorage` (the same interface that `archivos/` uses).
- Notifications. Upload batches emit no email; the existing `EN_PROCESO → FINALIZADA` notification (`notificaciones/`) is the only signal to the solicitante.

The feature is **append-only at the app layer**: no service method or view deletes a batch or a file. Django admin remains the escape hatch.

## Layer wiring

```
revision detail view → renders RespuestaUploadForm + lists existing batches
intake detail view   → lists batches only when estado == FINALIZADA
        │
        ▼
CreateRespuestaView (POST)            DownloadArchivoRespuestaView (GET)
        │                                          │
        ▼                                          ▼
              RespuestaService (services/respuesta_service/interface.py)
                          │
        ┌─────────────────┼─────────────────────┐
        ▼                 ▼                     ▼
   RespuestaRepository    FileStorage           LifecycleService
   (own ORM)              (LocalFileStorage,    (cross-feature read)
                          reused from archivos)
        │                 │                     │
        ▼                 ▼                     ▼
   RespuestaSolicitud   MEDIA_ROOT/...     SolicitudDetail
   ArchivoRespuesta
```

`respuesta/dependencies.py` wires `OrmRespuestaRepository → DefaultRespuestaService`. The service composes `archivos.dependencies.get_file_storage()` and `lifecycle.dependencies.get_lifecycle_service()`. `FileStorage` is documented as cross-feature infrastructure (it conceptually belongs in `_shared/` and was placed under `archivos/` historically) — the import is at boot time, not in runtime code, so it does not violate the cross-feature-service rule.

## Data shapes

### Models (`solicitudes/models/`)

**`RespuestaSolicitud`** (`respuesta_solicitud.py`):

- `id` UUIDField PK (uuid4).
- `solicitud` FK → `Solicitud`, `on_delete=CASCADE`, `related_name="respuestas"`.
- `actor` FK → `usuarios.User`, `on_delete=PROTECT`, `related_name="+"`.
- `actor_role` CharField(32, choices=`Role.choices()`) — snapshotted alongside the actor so reporting survives role changes; mirrors `HistorialEstado.actor_role`.
- `comentario` TextField(blank=True) — capped at 2000 chars by the DTO and the form.
- `created_at` auto_now_add.
- Meta: `ordering = ["created_at"]` (oldest first, timeline-friendly), index `(solicitud, created_at)`, `db_table = "solicitudes_respuestasolicitud"`.

**`ArchivoRespuesta`** (`archivo_respuesta.py`):

- `id` UUIDField PK (uuid4).
- `respuesta` FK → `RespuestaSolicitud`, `on_delete=CASCADE`, `related_name="archivos"`.
- `nombre_original` CharField(255).
- `stored_path` CharField(500) — path relative to `MEDIA_ROOT`, returned by `FileStorage.save`. `LocalFileStorage` writes to `solicitudes/<folio>/<uuid>.<ext>`; the storage layer ignores any subdirectory portion of `suggested_name`, so the layout is intentionally flat (resolved during 016 from the plan's OQ).
- `content_type` CharField(120).
- `size_bytes` PositiveBigIntegerField.
- `sha256` CharField(64).
- `created_at` auto_now_add.
- Meta: `ordering = ["created_at"]`, index `(respuesta, created_at)`, `db_table = "solicitudes_archivorespuesta"`.

No unique constraints — duplicate filenames within a batch are allowed (rare but possible).

### Constants (`respuesta/constants.py`)

```python
MAX_FILES_PER_BATCH = 10
MAX_COMENTARIO_CHARS = 2000
GLOBAL_MAX_SIZE_BYTES = 10 * 1024 * 1024   # mirrors archivos.constants (RT-07)
ALLOWED_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png",
    ".doc", ".docx", ".xls", ".xlsx", ".zip",
)
```

The constants are intentionally duplicated rather than lifted into a `_shared` module — only two callers and the surface is small. If a third caller appears, extract.

### DTOs (`respuesta/schemas.py`)

All frozen Pydantic v2 unless stated. `UploadedFile` is intentionally non-frozen because it briefly carries bytes across the view→service seam.

- **`UploadedFile`** — `nombre_original`, `content_type`, `size_bytes`, `content: bytes`. Discarded after the service hashes + persists the bytes.
- **`CreateRespuestaInput`** — `folio`, `actor_matricula`, `actor_role`, `comentario` (≤2000), `archivos: list[UploadedFile]` (≤10). `@model_validator(mode="after")` enforces "at least one file OR a non-empty comentario".
- **`ArchivoRespuestaDTO`** (frozen) — public surface for a stored file row; never carries bytes or `stored_path`.
- **`ArchivoRespuestaRecord`** (frozen, internal) — `ArchivoRespuestaDTO` + `stored_path` + `sha256` + `folio`. Used by the service to talk to storage; never leaves the feature.
- **`RespuestaDTO`** (frozen) — hydrated batch: `actor_matricula`, `actor_nombre`, `actor_role`, `comentario`, `created_at`, `archivos: list[ArchivoRespuestaDTO]`.

## Service surface

`RespuestaService` (`services/respuesta_service/interface.py`):

| Method | Purpose | Raises |
|---|---|---|
| `create_batch(input_dto)` | Validate, persist bytes via storage, insert `RespuestaSolicitud` + `ArchivoRespuesta` rows in one transaction. | `SolicitudNotFound`, `InvalidStateForRespuesta`, `Unauthorized`, `EmptyRespuestaBatch`, `TooManyFilesInBatch`, `ResponseFileTooLarge`, `ResponseFileExtensionNotAllowed` |
| `list_for_solicitud(folio, *, requester)` | Return batches the requester may see (visibility matrix below). Returns `[]` for forbidden combinations rather than raising — the template can ask without throwing. | `SolicitudNotFound` |
| `open_for_download(archivo_id, *, requester)` | Authorise read, return `(ArchivoRespuestaDTO, BinaryIO)` from storage. | `ArchivoRespuestaNotFound`, `SolicitudNotFound`, `Unauthorized` |

### `create_batch` flow

1. Defensive re-assertion of empty-batch / 10-file caps (the DTO validator enforces them at parse time; the service re-checks so callers that constructed via `model_construct` still get correct errors).
2. `lifecycle_service.get_detail(folio)` — `SolicitudNotFound` propagates.
3. **State guard**: `detail.estado != Estado.EN_PROCESO` → `InvalidStateForRespuesta`.
4. **Authz guard**: `actor_role` must be `ADMIN` or `detail.tipo.responsible_role` → `Unauthorized`.
5. **Per-file validation**: extension against `ALLOWED_EXTENSIONS`; size against `GLOBAL_MAX_SIZE_BYTES`. Raises `ResponseFileExtensionNotAllowed` / `ResponseFileTooLarge` with `field_errors={"archivos": [...]}`.
6. **Persist transactionally**: open `transaction.atomic()`, stream-hash each file (sha256), call `FileStorage.save(folio, suggested_name, content)` (returns `stored_path`), build `ArchivoRespuestaRecord` per file, then `repository.create(...)` inserts the batch row + child rows.
7. On any exception inside the `with` block: re-raise → `transaction.on_commit` rename hooks queued by `LocalFileStorage.save` do **not** fire → outer `try/finally` calls `file_storage.cleanup_pending()` to delete any orphaned `.partial` files.
8. Log `respuesta.created` with structured `extra=`. **No** notification dispatch.

### Visibility matrix (`list_for_solicitud` and `open_for_download`)

| Requester role                          | Same matrícula as solicitante? | Estado | Outcome |
| ---                                     | ---                            | ---    | --- |
| ADMIN                                   | any                            | any    | allowed |
| Personal in `tipo.responsible_role`     | any                            | any    | allowed |
| ALUMNO / DOCENTE (non-personal)         | yes (owner)                    | FINALIZADA | allowed |
| ALUMNO / DOCENTE (non-personal)         | yes (owner)                    | not FINALIZADA | `list_for_solicitud` returns `[]`; `open_for_download` raises `Unauthorized` |
| anyone else                             | no                             | any    | `list_for_solicitud` returns `[]`; `open_for_download` raises `Unauthorized` |

Pinned by `test_service.py`'s parametrised matrix.

## Repository (`respuesta/repositories/respuesta/`)

`OrmRespuestaRepository` exposes:

- `create(folio, actor_matricula, actor_role, comentario, archivos)` — opens its own `transaction.atomic()` and `bulk_create`s the file rows; returns the hydrated DTO after a `select_related("actor") + prefetch_related("archivos")` re-fetch.
- `list_for_solicitud(folio)` — ordered by `created_at` ascending, ≤2 SQL queries via `select_related/prefetch_related`.
- `get_archivo_record(archivo_id)` — returns the internal `ArchivoRespuestaRecord`; raises `ArchivoRespuestaNotFound` on miss.

There is **no** delete method on the interface (append-only contract; pinned by `test_repository_interface_has_no_delete_method`).

## Forms (`respuesta/forms/respuesta_upload_form.py`)

`RespuestaUploadForm` is a plain Django `Form` with a `_MultipleFileField` (subclass of `FileField` with `widget=_MultipleFileInput` that sets `allow_multiple_selected=True`). `clean()` enforces "at least one of (file, comentario)" and the 10-file cap, exposing `archivos_list` on `cleaned_data` for the view to consume.

The view converts `cleaned_data` into `CreateRespuestaInput`, reading `f.read()` for each `UploadedFile` (bounded by the 10 MB cap).

## Exceptions (`respuesta/exceptions.py`)

All inherit from `_shared.exceptions`:

| Exception | Base | Status | Notes |
|---|---|---|---|
| `RespuestaNotFound` | `NotFound` | 404 | Reserved for future per-batch endpoints. |
| `ArchivoRespuestaNotFound` | `NotFound` | 404 | Repository wraps `Model.DoesNotExist`. |
| `InvalidStateForRespuesta` | `Conflict` | 409 | `estado != EN_PROCESO`. |
| `TooManyFilesInBatch` | `DomainValidationError` | 422 | `field_errors={"archivos": [...]}`. |
| `EmptyRespuestaBatch` | `DomainValidationError` | 422 | `field_errors={"__all__": [...]}`. |
| `ResponseFileTooLarge` | `DomainValidationError` | 422 | Carries `size_bytes`, `max_bytes`. |
| `ResponseFileExtensionNotAllowed` | `DomainValidationError` | 422 | Carries `extension`, `allowed`. |

## Views & URLs

URLs (mounted via `solicitudes/urls.py` → `respuesta/urls.py`, namespace `solicitudes:respuesta`):

| URL | View | Methods | Mixin |
|---|---|---|---|
| `solicitudes/<folio>/respuestas/nueva/` | `CreateRespuestaView` | POST | `ReviewerRequiredMixin` (reused from `revision`) |
| `solicitudes/<folio>/respuestas/<uuid:respuesta_id>/archivos/<uuid:archivo_id>/` | `DownloadArchivoRespuestaView` | GET | `LoginRequiredMixin` (service-level authz) |

`CreateRespuestaView` is POST-only. On invalid form → flash errors + redirect to `solicitudes:revision:detail`. On valid form → build `CreateRespuestaInput`, call `service.create_batch`, flash success + redirect. `AppError` is caught and converted to a `messages.error(exc.user_message)` flash.

`DownloadArchivoRespuestaView` returns a `FileResponse` with `Content-Disposition: attachment; filename*=UTF-8''<encoded-name>` (RFC 5987, preserving Spanish accents) — matches `archivos`' download view.

## Templates

`templates/solicitudes/_partials/_respuestas.html` — list of batches:

- One block per batch with actor name + role badge + timestamp + optional comentario (`whitespace-pre-line`).
- File list with paperclip icon, original filename, size, "Descargar" button per file pointing at `solicitudes:respuesta:download`.
- Empty state: "Aún no hay respuestas."

Used by:

- `templates/solicitudes/revision/detail.html` — visible whenever `respuestas` is non-empty, under a "Respuestas entregadas" card. The "Adjuntar respuesta" card with the upload form is gated on `detail.estado.value == "EN_PROCESO"`. Both cards live under the **"Respuesta del personal"** eyebrow + hairline-top divider that visually separates the petition (Datos + Archivos del solicitante) from the personal-side response.
- `templates/solicitudes/intake/detail.html` — visible only when `detail.estado.value == "FINALIZADA"` AND `respuestas` is non-empty, under a "Documentos de respuesta" card under the **"Respuesta de la institución"** eyebrow. The pre-016 "Descargar PDF" affordance is gone from this template.

## File layout on disk

```
MEDIA_ROOT/solicitudes/<folio>/<uuid>.<ext>
```

Flat layout, shared with `archivos/`. `LocalFileStorage.save` ignores subdirectory portions of `suggested_name` and uses a uuid4 hex with the file's extension. This resolves the plan's open question — no nested `respuestas/<uuid>/` segment.

## Tests

- `respuesta/tests/test_schemas.py` — DTO validation (empty-batch + 10-file caps + 2000-char comentario cap).
- `respuesta/tests/test_exceptions.py` — HTTP status sentinels + `field_errors` shape.
- `respuesta/tests/test_forms.py` — valid combos, empty rejection, 11-file rejection.
- `respuesta/tests/test_repository.py` — real DB; create with files + comment-only, list ordering, folio isolation, `get_archivo_record`, append-only interface assertion.
- `respuesta/tests/test_service.py` — fakes (`InMemoryRespuestaRepository`, `RecordingFileStorage`, `InMemoryLifecycleService`); state guards, role authz, per-file validation, transactional rollback on storage failure, full visibility matrix.
- `respuesta/tests/test_views.py` — HTTP layer (`Client` + JWT-cookie minting); upload + download authz matrix; **Tier 1 integration** `test_personal_uploads_two_batches_and_finalizes_alumno_then_sees_responses` covers `lifecycle` (atender + finalizar) + `respuesta` (upload + list) + intake/revision templates.
- `respuesta/tests/{fakes,factories,conftest}.py` — fake repos + factories + JWT/MEDIA_ROOT fixture.

`tests-e2e/test_respuesta_golden_path.py` — Tier 2 Playwright: handler atender → upload 2 files + comment → finalizar → alumno-side download. Screenshots written to `/tmp/screenshots-016/` at 1280×900 and 320×800.

## Cross-feature consumers

- **`solicitudes/intake/views/detail.py`** — populates `respuestas = respuesta_service.list_for_solicitud(folio, requester=actor)` into the intake detail context.
- **`solicitudes/revision/views/detail.py`** — populates `respuestas` and `upload_form = RespuestaUploadForm()` into the revision detail context.
- **`solicitudes/pdf`** — its authz matrix dropped the owner-FINALIZADA branch in 016; the affordance was relabelled "Descargar borrador" in revision and removed from the alumno's intake detail.

## Related Specs

- [requirements.md](./requirements.md) — WHAT/WHY
- [Initiative 016 plan](../../../planning/016-respuesta/plan.md)
- [`../pdf/design.md`](../pdf/design.md) — authz matrix amended by 016
- [`../lifecycle/design.md`](../lifecycle/design.md) — `LifecycleService.get_detail` source
- [`../archivos/design.md`](../archivos/design.md) — `FileStorage` contract reused
- [`../revision/design.md`](../revision/design.md) — hosts the upload form + entregadas listing
- [`../intake/design.md`](../intake/design.md) — hosts the alumno-side documentos de respuesta listing
- [`../../../flows/solicitud-lifecycle.md`](../../../flows/solicitud-lifecycle.md) — end-to-end flow extended with the response-upload step
