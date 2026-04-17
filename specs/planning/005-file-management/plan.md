# 005 — File Management

## Summary

Persistent storage for solicitud attachments, including the comprobante de pago. Files are validated at upload (extension, max size per FieldDefinition), stored on disk under `media/solicitudes/<folio>/`, indexed by an `ArchivoSolicitud` row, and downloadable only by the solicitante, the responsible-role personal, or admin. ZIP files are stored as-is (no extraction). Replaces the placeholder discard-with-warning that intake 004 ships with.

## Depends on

- **001** — `_shared/exceptions.py`, `AppErrorMiddleware`
- **003** — `FieldDefinition.accepted_extensions` and `max_size_mb`
- **004** — `Solicitud` model, intake/revision views to integrate downloads

## Affected Apps / Modules

- `solicitudes/archivos/` — new feature package
- `solicitudes/models/archivo_solicitud.py` — new model
- `solicitudes/intake/views/create.py` — wire `archivo_service.store_for_solicitud` (replace 004's NoOp)
- `templates/solicitudes/_partials/_archivos.html` — list/download partial used in detail pages

## References

- [global/requirements.md](../../global/requirements.md) — RF-04 (comprobante), RF-10 (zip + organization), RT-07 (10 MB)
- [global/architecture.md](../../global/architecture.md) — `archivos` feature
- 004 plan, OQ-004-5 — `archivo_service.store_for_solicitud` contract

## Implementation Details

### Model — `models/archivo_solicitud.py`

```python
class ArchivoSolicitud(Model):
    id = UUIDField(primary_key=True, default=uuid4)
    solicitud = ForeignKey(Solicitud, on_delete=CASCADE, related_name="archivos")
    field_id = UUIDField(null=True)              # FieldDefinition id; null when archivo is comprobante
    kind = CharField(max_length=16, choices=ArchivoKind.choices)   # FORM | COMPROBANTE
    original_filename = CharField(max_length=255)
    stored_path = CharField(max_length=500)      # relative to MEDIA_ROOT, e.g. solicitudes/<folio>/<uuid>.pdf
    content_type = CharField(max_length=100)
    size_bytes = PositiveBigIntegerField()
    sha256 = CharField(max_length=64)            # integrity + dedupe debugging
    uploaded_by = ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="+")
    uploaded_at = DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [Index(fields=["solicitud", "kind"])]
        constraints = [
            UniqueConstraint(fields=["solicitud", "field_id"], name="unique_archivo_per_field",
                             condition=Q(kind="FORM")),
            UniqueConstraint(fields=["solicitud"], name="unique_comprobante",
                             condition=Q(kind="COMPROBANTE")),
        ]
```

`ArchivoKind`: `FORM`, `COMPROBANTE`.

### Storage abstraction (`archivos/storage/`)

```python
class FileStorage(ABC):
    @abstractmethod
    def save(self, *, folio: str, suggested_name: str, content: bytes) -> str: ...   # returns stored_path
    @abstractmethod
    def open(self, stored_path: str) -> BinaryIO: ...
    @abstractmethod
    def delete(self, stored_path: str) -> None: ...
```

`LocalFileStorage` — writes under `MEDIA_ROOT / "solicitudes" / folio / f"{uuid4().hex}{ext}"`. Uses `os.fsync` on save to survive crashes. The interface is here so a future S3 / Azure Blob impl drops in without touching services.

### DTOs (`archivos/schemas.py`)

```python
class ArchivoDTO(BaseModel):
    model_config = {"frozen": True}
    id: UUID
    solicitud_folio: str
    field_id: UUID | None
    kind: ArchivoKind
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
```

### Exceptions (`archivos/exceptions.py`)

```python
class ArchivoNotFound(NotFound):                code = "archivo_not_found";        user_message = "El archivo no existe."
class FileTooLarge(DomainValidationError):      code = "file_too_large";           user_message = "El archivo excede el tamaño máximo permitido."
class FileExtensionNotAllowed(DomainValidationError):
                                                code = "file_extension_not_allowed"; user_message = "El tipo de archivo no está permitido para este campo."
```

### Service (`archivos/services/archivo_service`)

```python
class ArchivoService(ABC):
    @abstractmethod
    def store_for_solicitud(self, *, folio: str, field_id: UUID | None, kind: ArchivoKind,
                            uploaded_file: UploadedFile, uploader: UserDTO) -> ArchivoDTO: ...
    @abstractmethod
    def list_for_solicitud(self, folio: str) -> list[ArchivoDTO]: ...
    @abstractmethod
    def open_for_download(self, archivo_id: UUID, requester: UserDTO) -> tuple[ArchivoDTO, BinaryIO]: ...
        # raises Unauthorized if requester is not solicitante / responsible role / admin
    @abstractmethod
    def delete_archivo(self, archivo_id: UUID, requester: UserDTO) -> None: ...
        # only allowed before transition to EN_PROCESO; after that, files are immutable
```

Validation in `store_for_solicitud`:
1. Resolve `Solicitud` (must exist, must be in `CREADA` for FORM uploads, no estado restriction for re-uploads of COMPROBANTE before `EN_PROCESO`).
2. If `kind=FORM`: lookup `field_id` in `solicitud.form_snapshot["fields"]` → assert extension and size against the snapshot's `accepted_extensions` and `max_size_mb`. If `field_id` not in snapshot: `DomainValidationError`.
3. If `kind=COMPROBANTE`: assert `solicitud.requiere_pago AND not solicitud.pago_exento`; extension whitelist `[".pdf", ".png", ".jpg", ".jpeg"]`; max size 5 MB.
4. Compute SHA-256 streaming; persist via `FileStorage.save`; insert `ArchivoSolicitud` row.

Authorization in `open_for_download`:
- `requester.matricula == solicitud.solicitante_matricula` → allowed.
- `requester.role == solicitud.tipo.responsible_role` → allowed.
- `requester.role == Role.ADMIN` → allowed.
- Else `Unauthorized`.

### Views (`archivos/views/`)

| URL | View | Method | Purpose |
|---|---|---|---|
| `solicitudes/archivos/<uuid:archivo_id>/` | `DownloadArchivoView` | GET | Streams the file; `Content-Disposition: attachment; filename=<original>` |

Uploads happen as part of the intake form submission (no dedicated upload URL); the intake view calls `archivo_service.store_for_solicitud` for each file field inside the same `atomic()` block as the `Solicitud` row insert. If file save fails, the whole transaction rolls back — and `LocalFileStorage` deletes any half-written file on rollback via a transaction-on-commit hook.

### Intake integration (replaces 004's NoOp)

`solicitudes/intake/views/create.py`:

```python
def post(self, request, slug):
    ...
    with atomic():
        detail = intake_service.create(input_dto, actor=request.user_dto)
        for field_id_str, uploaded_file in request.FILES.items():
            if field_id_str.startswith("field_"):
                archivo_service.store_for_solicitud(
                    folio=detail.folio,
                    field_id=UUID(field_id_str.removeprefix("field_")),
                    kind=ArchivoKind.FORM,
                    uploaded_file=uploaded_file,
                    uploader=request.user_dto,
                )
        if comprobante_required and "comprobante" in request.FILES:
            archivo_service.store_for_solicitud(
                folio=detail.folio,
                field_id=None,
                kind=ArchivoKind.COMPROBANTE,
                uploaded_file=request.FILES["comprobante"],
                uploader=request.user_dto,
            )
    return redirect("solicitudes:intake:detail", folio=detail.folio)
```

The intake view is the only place that calls `archivo_service.store_for_solicitud`. Per the cross-feature rule, intake imports `ArchivoService` (the interface) — not `ArchivoRepository` or `FileStorage`.

### Cross-app dependencies

- `usuarios.services.UserService` — read solicitante for authz checks.
- Consumed by `solicitudes.intake.views.create` and detail views (read).

### Sequencing

1. Model + migration.
2. `ArchivoKind`, exceptions, schemas.
3. `FileStorage` interface + `LocalFileStorage` impl + tests (using `tmp_path`).
4. Repository + tests.
5. Service + tests (with fake `FileStorage`).
6. Download view + tests.
7. Wire `archivo_service.store_for_solicitud` into intake's `create` view; remove the warning-and-discard placeholder.
8. Update `templates/solicitudes/_partials/_valores_render.html` to render archivos with download links; create `_archivos.html` partial; include in intake/detail and revision/detail.
9. End-to-end: alumno creates a constancia with a PDF + comprobante → downloads visible in detail; non-owner non-personal hits download URL → 403.


## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)
- Cross-feature: alumno submits intake with FORM attachments and a `comprobante` for a `requires_payment` tipo → all archivos persisted under `media/solicitudes/<folio>/` → owner downloads OK; an unrelated user gets 403.
- Failure path: induce a DB error after a file write → transaction rolls back and the file is removed (no orphans on disk).

### Browser (Tier 2 — `pytest-playwright`)
- Golden path: alumno attaches a real PDF via the file input, sees it listed on the solicitud detail page, downloads it.

## Acceptance Criteria

- [ ] Uploading a file with disallowed extension or > size_mb returns 422 with `_shared/error.html` field error.
- [ ] Uploading a `.zip` to a field whose `accepted_extensions` includes `.zip` is stored as-is and downloadable as a `.zip`.
- [ ] Comprobante upload required when `tipo.requires_payment AND not pago_exento`; absence rejects the form with `comprobante_required`.
- [ ] Files for solicitud `SOL-2026-00042` live under `media/solicitudes/SOL-2026-00042/`.
- [ ] `GET /solicitudes/archivos/<id>/` streams the bytes with `Content-Disposition: attachment` to authorized requesters; 403 for unauthorized.
- [ ] If the `Solicitud` insert rolls back, no orphan files remain on disk.
- [ ] Tests: service ≥ 95%, repo ≥ 95%, storage ≥ 90%, view ≥ 80%.

## Open Questions

- **OQ-005-1** — Replacement / re-upload: can a solicitante replace a file while estado=CREADA? Default: yes, replacing deletes the prior `ArchivoSolicitud` row and the file. Confirm.
- **OQ-005-2** — Antivirus scanning: out of scope for v1. If compliance requires it later, plug in a `FileScanner` interface called from `store_for_solicitud`.
- **OQ-005-3** — Total storage cap per solicitud (sum of all files): no cap initially. RT-07's 10MB applies per file.
