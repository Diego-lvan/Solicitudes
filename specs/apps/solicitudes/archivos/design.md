# archivos — Design

> Canonical reference for the file-management feature. Updated after initiative 005 closed.

## Layer wiring

```
Intake view (multipart POST) ─── store_for_solicitud(...)  ──┐
Detail / revision views     ─── list_for_solicitud(folio) ───┤
Download view (GET)         ─── open_for_download(id, user) ─┤
                                                              ▼
                          ArchivoService (services/archivo_service/interface.py)
                                       │
                       ┌───────────────┼─────────────────────┐
                       ▼               ▼                     ▼
            ArchivoRepository    FileStorage          LifecycleService
            (own ORM)            (LocalFileStorage)   (cross-feature read)
                       │               │                     │
                       ▼               ▼                     ▼
                ArchivoSolicitud  MEDIA_ROOT/...     SolicitudDetail
```

`archivos/dependencies.py` wires the three deps as factory functions: `get_archivo_repository()`, `get_file_storage()`, `get_archivo_service()` (composes the previous two plus `lifecycle.dependencies.get_lifecycle_service`). Views call the factory once per request.

## Data shapes

### Model (`solicitudes/models/archivo_solicitud.py`)

`ArchivoSolicitud` — `id` (UUID), `solicitud` (FK CASCADE → `Solicitud`, `related_name="archivos"`), `field_id` (UUID, nullable; the `FieldDefinition.id` for FORM, NULL for COMPROBANTE — **not** a real FK because the form is snapshotted on the solicitud and the live `FieldDefinition` can be edited or deleted later), `kind` (`ArchivoKind`), `original_filename` (≤255), `stored_path` (≤500, relative to MEDIA_ROOT), `content_type` (≤100), `size_bytes` (PositiveBigInt), `sha256` (≤64), `uploaded_by` (FK PROTECT → `User`, `related_name="+"`), `uploaded_at` (auto_now_add).

Index: `(solicitud, kind)`.

Two **partial unique constraints**:
- `archivo_unique_per_field` — `unique (solicitud, field_id)` where `kind='FORM'`
- `archivo_unique_comprobante` — `unique (solicitud)` where `kind='COMPROBANTE'`

The partials force replace-on-reupload semantics: a second upload for the same `(folio, field_id)` (or a second comprobante) requires the service to delete the prior row first.

### DTOs (`archivos/schemas.py`)

- **`ArchivoDTO`** — frozen Pydantic, public surface: `id, solicitud_folio, field_id, kind, original_filename, content_type, size_bytes, uploaded_at`. Never carries bytes.
- **`ArchivoRecord`** — frozen, **internal**: same as `ArchivoDTO` plus `stored_path` and `sha256`. Used by the service to talk to the storage backend; never leaves the feature package. Authz/validation context for the parent solicitud is fetched separately via `LifecycleService.get_detail` so the archivos repo never reaches into another feature's ORM.

### Constants (`archivos/constants.py`)

- `ArchivoKind` (StrEnum): `FORM`, `COMPROBANTE`.
- `GLOBAL_MAX_SIZE_BYTES = 10 * 1024 * 1024` (RT-07).
- `COMPROBANTE_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")`.

## Service surface

`ArchivoService` (`services/archivo_service/interface.py`):

| Method | Purpose | Raises |
|---|---|---|
| `store_for_solicitud(*, folio, field_id, kind, uploaded_file, uploader)` | Validate, persist bytes via storage, insert row. Replace-on-reupload semantics. | `SolicitudNotFound`, `FileExtensionNotAllowed`, `FileTooLarge`, `DomainValidationError` (state, missing field_id, comprobante-not-required) |
| `list_for_solicitud(folio)` | Oldest-first list of archivos (DTO projection). | — |
| `open_for_download(archivo_id, requester)` | Returns `(ArchivoDTO, BinaryIO)`. Authorises read access. | `ArchivoNotFound`, `Unauthorized` |
| `delete_archivo(archivo_id, requester)` | Delete row + (on commit) bytes. Allowed only in `CREADA`. | `ArchivoNotFound`, `Unauthorized`, `DomainValidationError` |

### Validation rules in `store_for_solicitud`

1. `lifecycle.get_detail(folio)` — fetches `SolicitudDetail`. Raises `SolicitudNotFound` if absent.
2. Estado guard:
   - FORM uploads require `estado == CREADA`.
   - COMPROBANTE uploads require `estado == CREADA`.
3. Kind-specific guards:
   - FORM: `field_id` must be in the solicitud's `form_snapshot.fields`. Extension whitelist + per-field `max_size_mb` come from the snapshot (frozen at intake — admin edits to the live `FieldDefinition` after the fact never apply retroactively).
   - COMPROBANTE: `requiere_pago AND not pago_exento`. Whitelist = `COMPROBANTE_EXTENSIONS`. Per-field cap = 10 MB.
4. Effective size cap = `min(GLOBAL_MAX_SIZE_BYTES, field_max_mb * 1024 * 1024)`. Smaller wins.
5. Replace-on-reupload: if a prior row exists for the same `(folio, field_id, FORM)` or `(folio, COMPROBANTE)`, delete the row synchronously and **schedule** the file deletion via `transaction.on_commit`. Critical: doing the file delete synchronously would orphan the file on rollback (the row gets restored but the bytes are gone).
6. Stream-hash (`sha256`), persist via `FileStorage.save`, insert the row.

### Authorization rules in `open_for_download`

- `requester.matricula == detail.solicitante.matricula` → allowed
- `requester.role == detail.tipo.responsible_role` → allowed
- `requester.role == Role.ADMIN` → allowed
- else `Unauthorized` (HTTP 403)

The view layer applies the same rule through the service — no duplicated auth in the view itself.

## Repository surface

`ArchivoRepository` (`repositories/archivo/interface.py`) — owns reads/writes of `ArchivoSolicitud` only:

`create(...)`, `get_record(id)`, `list_by_folio(folio)`, `find_form_archivo(*, folio, field_id)`, `find_comprobante(*, folio)`, `delete(id) → stored_path`.

Per the cross-feature dependency rule (`.claude/rules/django-code-architect.md`), this repo never queries `Solicitud` or `TipoSolicitud`. The service composes solicitud context via `LifecycleService.get_detail`.

## Storage layer

`FileStorage` (`storage/interface.py`):

```python
def save(*, folio: str, suggested_name: str, content: bytes) -> str
def open(stored_path: str) -> BinaryIO
def delete(stored_path: str) -> None
def cleanup_pending() -> None
```

### Transactional contract — temp + on_commit rename

`LocalFileStorage.save` writes the bytes to a `.partial` sibling of the final path and registers a `transaction.on_commit` hook that atomically renames `.partial` → final via `os.replace`. The pending list is a thread-local; concurrent requests do not see each other's partials.

- **Success path**: outer atomic commits → on_commit fires → rename → file is live; the pending entry is drained.
- **Rollback path**: outer atomic raises → on_commit hooks **do not** fire → the `.partial` is orphaned in the filesystem until `cleanup_pending()` is called from the caller's `try/finally`. Intake calls it unconditionally after the atomic block; on the success path the pending list is already empty so this is a no-op.

`save` accepts `bytes` today (the global 10 MB cap bounds memory). Switching to a chunk iterator is the natural redesign point when an S3/Azure Blob adapter lands.

### Known limitation — post-commit rename failure

If `os.replace` raises **inside** the on_commit callback (ENOSPC, EACCES at rename time), the DB transaction has already committed — the row points at a non-existent path. The hook logs `archivos.commit_missing_partial` (FileNotFoundError) or `archivos.commit_rename_failed` (other OSError) with structured `extra={folio, partial, final}` and re-raises so Django marks the request as errored. Operationally these dangling rows must be reconciled by ops; eventual hardening (write the row inside on_commit, or content-addressed storage) is out of scope for v1.

### Path safety

`LocalFileStorage._abs` resolves the requested `stored_path` against `MEDIA_ROOT` and rejects any path that escapes the root (defense-in-depth against a stored_path crafted to do `../etc/passwd`).

## Exceptions (`archivos/exceptions.py`)

All inherit from `_shared.exceptions.AppError`:

- **`ArchivoNotFound`** (`NotFound`, 404) — `code="archivo_not_found"`.
- **`FileTooLarge`** (`DomainValidationError`, 422) — `code="file_too_large"`. Carries `size_bytes`, `max_bytes`, optional `field` for `field_errors`.
- **`FileExtensionNotAllowed`** (`DomainValidationError`, 422) — `code="file_extension_not_allowed"`. Carries `extension`, `allowed`, optional `field`.

## Views & URLs

URLs (mounted via `solicitudes/urls.py` → `archivos/urls.py`, namespace `solicitudes:archivos`):

| URL | View | Methods | Purpose |
|---|---|---|---|
| `solicitudes/archivos/<uuid:archivo_id>/` | `DownloadArchivoView` | GET | Streams file to authorised requester |

`DownloadArchivoView` returns a `FileResponse` with `Content-Disposition: attachment; filename*=UTF-8''<encoded-name>` (RFC 5987 — preserves Spanish accents). Auth via `LoginRequiredMixin` + `archivo_service.open_for_download`.

Uploads are **not** a separate URL: the intake view's `multipart/form-data` POST carries the bytes; intake calls `archivo_service.store_for_solicitud(...)` for each file inside the same atomic block as the `Solicitud` row insert. See `apps/solicitudes/intake/design.md` for the wiring.

## Templates

`templates/solicitudes/_partials/_archivos.html` — Bootstrap list-group of archivos with paperclip icon, original filename, `filesizeformat` size, COMPROBANTE badge, outline-primary "Descargar" button per row, accessible empty state. Included in `intake/detail.html` and `revision/detail.html` inside a card; both detail views inject `archivos = archivo_service.list_for_solicitud(folio)` into the template context.

## File layout on disk

`MEDIA_ROOT/solicitudes/<folio>/<uuid>.<ext>`

Example: `media/solicitudes/SOL-2026-00042/f5dd66c9422244ca9d1a5d377e216874.pdf`. The UUID prefix avoids original-filename collisions and prevents directory enumeration from leaking the user-chosen names.

## Cross-feature dependencies

- **Inbound (consumes archivos)**: `solicitudes.intake.views.create.CreateSolicitudView` (calls `store_for_solicitud`), `solicitudes.intake.views.detail.SolicitudDetailView` and `solicitudes.revision.views.detail.RevisionDetailView` (call `list_for_solicitud`).
- **Outbound (archivos consumes)**: `solicitudes.lifecycle.services.lifecycle_service.LifecycleService.get_detail(folio)` for solicitud context (estado, requiere_pago, pago_exento, form_snapshot, responsible_role, solicitante.matricula). Per the cross-feature rule, archivos depends on `LifecycleService` (the interface), not on `SolicitudRepository`.

## Open follow-ups (not blocking 005)

- **Streaming `FileStorage.save`** — refactor to accept a chunk iterator when an S3/Azure adapter lands.
- **Per-instance pending list** — currently `_pending` is module-level thread-local. Move to per-instance state if a second concrete `FileStorage` is wired alongside `LocalFileStorage`.
- **Auth helper consolidation** — owner / responsible / admin check is duplicated between `intake/views/detail.py` and `archivos.services._authorise_read`. Extract to a `lifecycle` helper if a third caller appears.
- **Antivirus port** — slot a `FileScanner` ABC into `store_for_solicitud` if compliance requires it.

## Related Specs

- [requirements.md](./requirements.md) — WHAT/WHY for this feature
- [planning/005-file-management](../../../planning/005-file-management/plan.md) — implementation initiative
- [apps/solicitudes/intake/design.md](../intake/design.md) — the only caller of `store_for_solicitud`
- [apps/solicitudes/lifecycle/design.md](../lifecycle/design.md) — source of `SolicitudDetail`
- [apps/solicitudes/tipos/design.md](../tipos/design.md) — `FieldDefinition.accepted_extensions` / `max_size_mb` (snapshotted into the solicitud at intake)
- [flows/solicitud-lifecycle.md](../../../flows/solicitud-lifecycle.md) — end-to-end flow (intake now persists archivos atomically)
