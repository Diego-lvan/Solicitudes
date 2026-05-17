# 016 — Response Files & Comments

## Summary

Replace the implicit "auto-rendered template PDF = the solicitud's output" model with an explicit **response upload** mechanism. Personal that atiende a solicitud uploads one or more response files (optionally with a comment) during `EN_PROCESO`; uploads are append-only batches; the solicitante sees them only after `FINALIZADA`. The existing `pdf` feature stays in place but is reframed as a **draft** for the handler (button relabeled "Descargar borrador") and the solicitante's PDF download is removed.

## Depends on

- **004 — Solicitud Lifecycle** — provides `LifecycleService.get_detail(folio)` (read-only consumer), `Estado` constants, `Solicitud` model FK target.
- **005 — File Management** — provides the `FileStorage` interface in `_shared/storage` reused for response bytes; size/extension validation rules are mirrored from `archivos.constants`.
- **006 — PDF Generation** — the `pdf` feature's authz matrix is amended (drop the "owner / FINALIZADA → allowed" row); the alumno's "Descargar PDF" button is removed and the personal's button relabeled to "Descargar borrador".
- **014 — Revision Handler Display** — the revision detail template that hosts the new upload form already underwent its restructuring; this initiative adds a card alongside the existing Acciones / Historial / Solicitante cards.

## Affected Modules

- `app/solicitudes/respuesta/` — **new feature package** (this initiative's main deliverable)
- `app/solicitudes/models/` — two new models: `respuesta_solicitud.py`, `archivo_respuesta.py`
- `app/solicitudes/migrations/` — one new migration creating the two tables
- `app/solicitudes/pdf/services/pdf_service/implementation.py` — drop the owner-FINALIZADA branch from `_authorize_render_for_solicitud`
- `app/solicitudes/pdf/tests/test_pdf_service.py` — update the authz matrix tests accordingly
- `app/templates/solicitudes/intake/detail.html` — remove the "Descargar PDF" button (alumno never sees it again); add a "Documentos de respuesta" section gated on `estado == FINALIZADA`
- `app/templates/solicitudes/revision/detail.html` — relabel the PDF button to "Descargar borrador"; add an "Adjuntar respuesta" card with the upload form; add a "Respuestas entregadas" listing card
- `app/solicitudes/urls.py` — include `respuesta/urls.py`

## References

- [requirements.md](../../apps/solicitudes/respuesta/requirements.md) — WHAT/WHY for this feature
- [apps/solicitudes/archivos/design.md](../../apps/solicitudes/archivos/design.md) — `FileStorage` contract, transactional `save` semantics (temp + on_commit rename) reused here
- [apps/solicitudes/lifecycle/design.md](../../apps/solicitudes/lifecycle/design.md) — `LifecycleService.get_detail`, `Estado`, `SolicitudDetail` shape consumed for authz/state checks
- [apps/solicitudes/revision/design.md](../../apps/solicitudes/revision/design.md) — `RevisionDetailView` is where the new upload form lives
- [apps/solicitudes/pdf/design.md](../../apps/solicitudes/pdf/design.md) — current authz matrix being amended
- [.claude/rules/django-code-architect.md](../../../.claude/rules/django-code-architect.md)
- [.claude/rules/django-test-architect.md](../../../.claude/rules/django-test-architect.md)

## Implementation Details

### Data model

Two new models in `app/solicitudes/models/`, one per file (per the one-public-class-per-file rule).

**`respuesta_solicitud.py`** — `RespuestaSolicitud`:

| Column | Type | Notes |
|---|---|---|
| `id` | UUIDField, PK, `default=uuid4` | |
| `solicitud` | FK → `Solicitud`, `on_delete=CASCADE`, `related_name="respuestas"` | |
| `actor` | FK → `usuarios.User`, `on_delete=PROTECT`, `related_name="+"` | the personal that uploaded |
| `actor_role` | CharField(`Role.choices()`) | snapshotted alongside the actor so reporting survives role changes (mirrors `HistorialEstado.actor_role`) |
| `comentario` | TextField(blank=True) | optional; DTO caps at 2000 chars |
| `created_at` | DateTimeField, `auto_now_add=True` | |

Meta: `ordering = ["created_at"]` (oldest-first, timeline-friendly). Index `(solicitud, created_at)`. `db_table = "solicitudes_respuestasolicitud"`.

**`archivo_respuesta.py`** — `ArchivoRespuesta`:

| Column | Type | Notes |
|---|---|---|
| `id` | UUIDField, PK, `default=uuid4` | |
| `respuesta` | FK → `RespuestaSolicitud`, `on_delete=CASCADE`, `related_name="archivos"` | |
| `nombre_original` | CharField(255) | as uploaded |
| `stored_path` | CharField(500) | relative to `MEDIA_ROOT`, returned by `FileStorage.save` |
| `content_type` | CharField(120) | |
| `size_bytes` | PositiveBigIntegerField | |
| `sha256` | CharField(64) | streamed during save |
| `created_at` | DateTimeField, `auto_now_add=True` | |

Meta: `ordering = ["created_at"]`. Index `(respuesta, created_at)`. `db_table = "solicitudes_archivorespuesta"`.

No unique constraints — duplicate filenames within a batch are allowed (rare but possible).

### Migration

`app/solicitudes/migrations/<NNNN>_respuestasolicitud_archivorespuesta.py` — single migration. No data migration. Run order: after `archivos`' last migration (no FK between them, but keep the sequence tidy). Verify locally with `python manage.py makemigrations solicitudes --dry-run` then commit the file.

### Feature package layout

```
app/solicitudes/respuesta/
├── __init__.py
├── apps.py                                  # not needed; the parent `solicitudes` AppConfig already covers models
├── urls.py
├── dependencies.py
├── schemas.py
├── exceptions.py
├── constants.py                             # MAX_FILES_PER_BATCH = 10, MAX_COMENTARIO_CHARS = 2000
├── permissions.py                           # reuses revision.permissions.ReviewerRequiredMixin via re-export
├── forms/
│   ├── __init__.py
│   └── respuesta_upload_form.py
├── views/
│   ├── __init__.py
│   ├── personal.py                          # CreateRespuestaView
│   └── shared.py                            # DownloadArchivoRespuestaView
├── repositories/
│   └── respuesta/
│       ├── __init__.py
│       ├── interface.py                     # RespuestaRepository(ABC)
│       └── implementation.py                # OrmRespuestaRepository
├── services/
│   └── respuesta_service/
│       ├── __init__.py
│       ├── interface.py                     # RespuestaService(ABC)
│       └── implementation.py                # DefaultRespuestaService
└── tests/
    ├── __init__.py
    ├── fakes.py                             # InMemoryRespuestaRepository, RecordingFileStorage
    ├── factories.py                         # make_respuesta(...), make_archivo_respuesta(...)
    ├── test_schemas.py
    ├── test_exceptions.py
    ├── test_forms.py
    ├── test_respuesta_repository.py
    ├── test_respuesta_service.py
    └── test_views.py
```

`app/solicitudes/urls.py` gains `path("", include("solicitudes.respuesta.urls"))` so the namespace becomes `solicitudes:respuesta:*`.

### DTOs (`respuesta/schemas.py`)

All frozen Pydantic v2 unless stated.

```python
class UploadedFile(BaseModel):
    nombre_original: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(gt=0)
    content: bytes                                # not frozen; carries bytes for the service

class CreateRespuestaInput(BaseModel):
    folio: str
    actor_matricula: str
    actor_role: str
    comentario: str = Field(default="", max_length=2000)
    archivos: list[UploadedFile] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _at_least_one_payload(self) -> "CreateRespuestaInput":
        if not self.archivos and not self.comentario.strip():
            raise ValueError("Adjunta al menos un archivo o escribe un comentario.")
        return self

class ArchivoRespuestaDTO(BaseModel):
    model_config = {"frozen": True}
    id: UUID
    respuesta_id: UUID
    nombre_original: str
    content_type: str
    size_bytes: int
    created_at: datetime

class RespuestaDTO(BaseModel):
    model_config = {"frozen": True}
    id: UUID
    folio: str
    actor_matricula: str
    actor_nombre: str
    actor_role: str
    comentario: str
    created_at: datetime
    archivos: list[ArchivoRespuestaDTO]

class ArchivoRespuestaRecord(BaseModel):
    model_config = {"frozen": True}
    # internal: same as ArchivoRespuestaDTO + stored_path + sha256, never leaves the feature
    id: UUID
    respuesta_id: UUID
    folio: str
    nombre_original: str
    content_type: str
    size_bytes: int
    sha256: str
    stored_path: str
    created_at: datetime
```

### Constants (`respuesta/constants.py`)

```python
MAX_FILES_PER_BATCH = 10
MAX_COMENTARIO_CHARS = 2000
GLOBAL_MAX_SIZE_BYTES = 10 * 1024 * 1024          # mirrors archivos.constants.GLOBAL_MAX_SIZE_BYTES (RT-07)
ALLOWED_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx", ".zip")
```

**Decision on the duplication vs. extraction open question from the requirements.md:** duplicate the constants locally. Two tuples of strings and one int is not enough surface area to justify a `_shared/files.py` module; if a third caller appears, extract then.

### Exceptions (`respuesta/exceptions.py`)

All inherit from `_shared.exceptions`:

```python
class RespuestaNotFound(NotFound):
    code = "respuesta_not_found"
    user_message = "El envío de respuesta no existe."

class ArchivoRespuestaNotFound(NotFound):
    code = "archivo_respuesta_not_found"
    user_message = "El archivo de respuesta no existe."

class InvalidStateForRespuesta(Conflict):
    code = "invalid_state_for_respuesta"
    user_message = "La solicitud debe estar En proceso para adjuntar respuesta."

class TooManyFilesInBatch(DomainValidationError):
    code = "too_many_files_in_batch"
    user_message = "Máximo 10 archivos por envío."

class EmptyRespuestaBatch(DomainValidationError):
    code = "empty_respuesta_batch"
    user_message = "Adjunta al menos un archivo o escribe un comentario."

class ResponseFileTooLarge(DomainValidationError):
    code = "response_file_too_large"
    # carries size_bytes, max_bytes; field_errors keyed by "archivos"

class ResponseFileExtensionNotAllowed(DomainValidationError):
    code = "response_file_extension_not_allowed"
    # carries extension, allowed; field_errors keyed by "archivos"
```

### Repository surface (`respuesta/repositories/respuesta/`)

`RespuestaRepository(ABC)`:

- `create(*, folio: str, actor_matricula: str, actor_role: str, comentario: str, archivos: list[ArchivoRespuestaRecord]) -> RespuestaDTO` — inserts the batch row and its file rows in one `transaction.atomic()`. Returns the hydrated DTO.
- `list_for_solicitud(folio: str) -> list[RespuestaDTO]` — oldest-first; `select_related("actor")` + `prefetch_related("archivos")`. Bound to ≤2 queries.
- `get_archivo_record(archivo_id: UUID) -> ArchivoRespuestaRecord` — for the download path; includes `stored_path`. Raises `ArchivoRespuestaNotFound` on miss.

`OrmRespuestaRepository` translates `Model.DoesNotExist` → `ArchivoRespuestaNotFound`. The actor's `full_name` is read from `actor.full_name` for the `RespuestaDTO.actor_nombre` field.

### Service surface (`respuesta/services/respuesta_service/`)

`RespuestaService(ABC)`:

- `create_batch(input_dto: CreateRespuestaInput) -> RespuestaDTO`
- `list_for_solicitud(folio: str, *, requester: UserDTO) -> list[RespuestaDTO]` — applies visibility rule (solicitante sees only when `FINALIZADA`)
- `open_for_download(archivo_id: UUID, *, requester: UserDTO) -> tuple[ArchivoRespuestaDTO, BinaryIO]`

`DefaultRespuestaService.__init__` takes: `respuesta_repository: RespuestaRepository`, `file_storage: FileStorage`, `lifecycle_service: LifecycleService`, `logger: Logger`.

#### `create_batch` flow

1. `detail = lifecycle_service.get_detail(input_dto.folio)` — `SolicitudNotFound` propagates.
2. **State guard:** if `detail.estado != Estado.EN_PROCESO` → raise `InvalidStateForRespuesta`.
3. **Authz guard:** the **view layer** is the one enforcing role (admin or personal in `detail.tipo.responsible_role`) via the existing `ReviewerRequiredMixin` + a service-level cross-check on `input_dto.actor_role` against `detail.tipo.responsible_role` (admin bypass). Reuses the same shape as `LifecycleService._authorize`.
4. **Validation:** the `CreateRespuestaInput.@model_validator` already enforced empty-batch and 10-file caps; per-file size/extension are checked here against `ALLOWED_EXTENSIONS` + `GLOBAL_MAX_SIZE_BYTES`. Raises `ResponseFileTooLarge` / `ResponseFileExtensionNotAllowed` with `field_errors={"archivos": [...]}`.
5. **Persist (transactional):**
   - `with transaction.atomic():` open a savepoint.
   - For each file: stream-hash (sha256), compute the storage suggested name as `respuesta-<uuid4().hex[:8]>__<sanitised original>`, call `file_storage.save(folio=folio, suggested_name=..., content=bytes)`. Collect the returned `stored_path` and build an `ArchivoRespuestaRecord`.
   - `repository.create(...)` inserts the batch + child rows. The repo runs inside the same atomic.
   - On any exception inside the block: re-raise → `transaction.on_commit` hooks registered by `LocalFileStorage.save` will NOT fire → orphaned `.partial` files cleaned up by `file_storage.cleanup_pending()` called from the service's `try/finally` (exactly the pattern documented in `archivos/design.md` under "Transactional contract").
6. **Outside the atomic:** none — there are no notifications for upload events.

#### `list_for_solicitud` visibility rule

- `requester.role == Role.ADMIN` → all batches.
- `requester.role == detail.tipo.responsible_role` → all batches.
- `requester.matricula == detail.solicitante.matricula AND detail.estado == Estado.FINALIZADA` → all batches.
- Otherwise → empty list (the view chooses to render the section or hide it; the service does not raise here so the template can ask without throwing).

#### `open_for_download` authz

The service fetches the `ArchivoRespuestaRecord` (which carries `respuesta_id` and `folio`), then `lifecycle_service.get_detail(folio)`, then applies:

| Requester | Estado | Outcome |
|---|---|---|
| ADMIN | any | allowed |
| Personal in `responsible_role` | any | allowed |
| Owner (matrícula match) | `FINALIZADA` | allowed |
| Owner (matrícula match) | other | `Unauthorized` |
| Anyone else | any | `Unauthorized` |

The bytes come back via `file_storage.open(stored_path)`.

### Forms (`respuesta/forms/respuesta_upload_form.py`)

```python
class RespuestaUploadForm(forms.Form):
    comentario = forms.CharField(
        required=False, max_length=MAX_COMENTARIO_CHARS,
        widget=forms.Textarea(attrs={"rows": 4, "maxlength": MAX_COMENTARIO_CHARS}),
        label="Comentario (opcional)",
    )
    archivos = MultipleFileField(  # custom widget: subclass of forms.FileField with allow_empty_file=False, widget=forms.ClearableFileInput(attrs={"multiple": True})
        required=False, label="Archivos de respuesta",
    )

    def clean(self) -> dict:
        cleaned = super().clean()
        files = self.files.getlist("archivos") if self.files else []
        comentario = (cleaned.get("comentario") or "").strip()
        if not files and not comentario:
            raise forms.ValidationError("Adjunta al menos un archivo o escribe un comentario.")
        if len(files) > MAX_FILES_PER_BATCH:
            raise forms.ValidationError(f"Máximo {MAX_FILES_PER_BATCH} archivos por envío.")
        cleaned["archivos_list"] = files
        return cleaned
```

The view converts the cleaned form into a `CreateRespuestaInput` (reading each `UploadedFile.read()` into bytes — bounded by 10 MB per file).

### Views & URLs

`app/solicitudes/respuesta/urls.py`:

```python
app_name = "respuesta"
urlpatterns = [
    path("<str:folio>/respuestas/nueva/",
         CreateRespuestaView.as_view(), name="create"),
    path("<str:folio>/respuestas/<uuid:respuesta_id>/archivos/<uuid:archivo_id>/",
         DownloadArchivoRespuestaView.as_view(), name="download"),
]
```

Mounted by `app/solicitudes/urls.py` so the full names become `solicitudes:respuesta:create` and `solicitudes:respuesta:download`.

`CreateRespuestaView` (POST-only, `ReviewerRequiredMixin`): validates form, builds DTO, calls service, flashes `messages.success("Respuesta adjuntada.")`, redirects to `solicitudes:revision:detail folio=folio`. Catches `AppError` → flashes `messages.error(exc.user_message)`, redirects to the same detail page.

`DownloadArchivoRespuestaView` (GET, `LoginRequiredMixin`): calls `service.open_for_download(archivo_id, requester=actor_from_request(request))`. Returns `FileResponse(file_obj, as_attachment=True, filename=archivo.nombre_original)`. RFC 5987 encoded `Content-Disposition` like `archivos`.

### Cross-feature edits

**`pdf/services/pdf_service/implementation.py`** — `_authorize_render_for_solicitud` drops the `owner AND estado == FINALIZADA → allowed` branch. The function now only allows admin and personal in the responsible role. Update `pdf/tests/test_pdf_service.py`:

- Replace "owner/FINALIZADA → allowed" with "owner/FINALIZADA → Unauthorized" assertion.
- The other rows of the matrix stay as-is.

**`templates/solicitudes/intake/detail.html`** — find the existing "Descargar PDF" button block (gated on `is_owner and detail.estado == FINALIZADA and detail.tipo.plantilla_id`) and remove it. Add, gated on `detail.estado == FINALIZADA` and the `respuestas` context key being non-empty, a "Documentos de respuesta" card listing each batch with: actor name + timestamp · comment (if any, line breaks preserved via `linebreaksbr`) · file list with `Descargar` links targeting `solicitudes:respuesta:download`.

The intake detail view (`solicitudes/intake/views/detail.py`) gains a `respuestas = respuesta_service.list_for_solicitud(folio, requester=actor)` context key. View import path: `from solicitudes.respuesta.dependencies import get_respuesta_service`.

**`templates/solicitudes/revision/detail.html`** — relabel the existing PDF button: `Descargar PDF` → `Descargar borrador`. Add an "Adjuntar respuesta" card containing the `RespuestaUploadForm` (POSTs to `solicitudes:respuesta:create`), gated visible on `detail.estado == EN_PROCESO`. Add a "Respuestas entregadas" card showing every batch (same shape as the alumno-side rendering), visible whenever any batch exists.

The revision detail view (`solicitudes/revision/views/detail.py`) gains:
- a `respuestas` context key built by `respuesta_service.list_for_solicitud(folio, requester=actor)`,
- an `upload_form` context key (`RespuestaUploadForm()`),
- both pulled from `respuesta.dependencies.get_respuesta_service()`.

These two view edits are the only invasive changes outside the new feature package.

### Storage layout on disk

```
MEDIA_ROOT/solicitudes/<folio>/respuestas/<respuesta_uuid>/<archivo_uuid>__<sanitised_name>.<ext>
```

`LocalFileStorage.save(folio, suggested_name, content)` is already in place — we just pass a different `suggested_name`. **Decision:** the `respuestas/<respuesta_uuid>/` segment is achieved by passing `suggested_name=f"respuestas/{respuesta_uuid}/{archivo_uuid}__{sanitise(name)}.{ext}"` since `LocalFileStorage.save` joins it under `solicitudes/<folio>/`. If `LocalFileStorage` rejects subdirectories in `suggested_name`, fall back to flat layout at `MEDIA_ROOT/solicitudes/<folio>/<archivo_uuid>__...` — the structure is cosmetic, not load-bearing.

### Dependency wiring (`respuesta/dependencies.py`)

```python
def get_respuesta_repository() -> RespuestaRepository:
    return OrmRespuestaRepository()

def get_respuesta_service() -> RespuestaService:
    return DefaultRespuestaService(
        respuesta_repository=get_respuesta_repository(),
        file_storage=get_file_storage(),                              # imports from archivos.dependencies
        lifecycle_service=get_lifecycle_service(),
        logger=logging.getLogger("solicitudes.respuesta.service"),
    )
```

`get_file_storage` is reused from `solicitudes.archivos.dependencies` — that's allowed because `FileStorage` is infrastructure (it conceptually belongs to `_shared/storage` and was placed under `archivos/` historically). The respuesta service imports the factory, not the implementation class. **Decision:** do not refactor `FileStorage` out of `archivos` in this initiative; cross-feature factory import is an acceptable temporary seam, documented here for follow-up.

### Settings / migrations / env

- No new settings.
- No new env vars.
- Single new migration (described above). Squash not required.

### Sequencing within the initiative

Recommended order for `/implement`:

1. **Models + migration** (no behavior yet). Run `makemigrations`, commit.
2. **Schemas + exceptions + constants**.
3. **Repository (ABC + ORM impl)** + repository tests.
4. **Service (ABC + impl)** + service tests with in-memory fake repo + recording fake `FileStorage`.
5. **Form** + form tests.
6. **Views + URLs + dependency wiring** + view tests (HTTP layer).
7. **PDF service authz amendment** + PDF test updates.
8. **Template edits** (intake/detail + revision/detail) + the supporting view-context additions.
9. **Tier 1 in-process integration test** covering the cross-feature flow.
10. **Tier 2 Playwright golden path**.

Steps 1–6 are entirely additive (the feature is dark until step 8 wires it into templates), so the new code can ship behind nothing more than "templates not yet updated." This keeps risk low.

## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)

- **Personal uploads two batches and finalizes, alumno downloads only after FINALIZADA.** Spans `lifecycle` (atender + finalizar), `respuesta` (create + list + download), `intake/revision` templates. Lives in `app/solicitudes/respuesta/tests/test_views.py` since respuesta is the highest-level feature in the chain.
- **PDF authz regression: alumno can no longer download the template-rendered PDF.** Spans `pdf` only. Already a single-feature concern; placed in `pdf/tests/test_views.py` as an amendment to the existing matrix tests.

### Browser (Tier 2 — `pytest-playwright`)

- **Personal-as-Control-Escolar adjuntar respuesta + finalizar, alumno-side ve los documentos.** A new `tests-e2e/tests/test_respuesta_flow.py` with new page objects `RevisionDetailPage` (extends existing if any) and `IntakeDetailPage`. Covers: handler opens detail → clicks "Descargar borrador" (download triggers; assert via `expect_download`) → uploads 2 files + comment via the form → clicks "Finalizar" → logs out → logs in as alumno → opens own detail → sees "Documentos de respuesta" card with 2 file links and the comment.

## Open Questions

- **`LocalFileStorage` subdirectory support in `suggested_name`.** If the existing implementation joins `suggested_name` literally (allowing slashes) the nested layout works as written; if it sanitises slashes out, fall back to the flat layout. Either is acceptable functionally; decided at implementation time after a 30-second read of `LocalFileStorage.save`.

## Acceptance Criteria

- [ ] `RespuestaSolicitud` and `ArchivoRespuesta` models exist with the documented columns, indexes, and ordering.
- [ ] A single migration creates both tables; `migrate --plan` shows no drift after running.
- [ ] `RespuestaService.create_batch` rejects empty submissions, >10 files, oversized files, disallowed extensions, and any estado other than `EN_PROCESO` with the matching feature exception.
- [ ] `RespuestaService.create_batch` is transactional: a forced storage failure mid-batch leaves zero rows in the DB and no `.partial` files in `MEDIA_ROOT` after `cleanup_pending()`.
- [ ] `RespuestaService.list_for_solicitud` returns empty for owner-during-EN_PROCESO and populated for owner-after-FINALIZADA, personal-anytime, and admin-anytime.
- [ ] `DownloadArchivoRespuestaView` enforces the same authz; owner gets 403 in EN_PROCESO, 200 in FINALIZADA.
- [ ] `pdf/services/pdf_service` no longer allows owner downloads; the alumno's "Descargar PDF" button is gone from `intake/detail.html`.
- [ ] `revision/detail.html` shows "Descargar borrador" (relabel), "Adjuntar respuesta" (visible only in EN_PROCESO), and "Respuestas entregadas" (visible whenever batches exist).
- [ ] `intake/detail.html` shows "Documentos de respuesta" only when `estado == FINALIZADA` AND at least one batch exists.
- [ ] No new email is sent by an upload batch; the existing FINALIZADA email path is unchanged.
- [ ] All tests in `respuesta/tests/` pass; `pdf/tests/test_pdf_service.py` updated assertions pass.
- [ ] Tier 1 integration test in `respuesta/tests/test_views.py` covering the cross-feature flow passes.
- [ ] Tier 2 Playwright `test_respuesta_flow.py` passes against `live_server`.
- [ ] Roadmap row 016 flipped to `Done` after `/review` closes the initiative.
- [ ] `design.md` for `respuesta` filled in from this plan; `pdf/design.md` authz matrix updated; `revision/design.md` and `intake/design.md` reference the new card/section.
