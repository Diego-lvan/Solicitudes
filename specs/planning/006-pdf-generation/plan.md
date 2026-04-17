# 006 — PDF Generation

## Summary

Per-tipo HTML templates with `{{ variable }}` substitution, rendered to PDF on demand by personal (and downloadable thereafter by personal and the solicitante). No PDF blob is persisted — the source data lives in the solicitud (`form_snapshot`, `valores`, plus user/SIGA fields), so the PDF can be re-generated identically at any time. Templates are admin-managed alongside the tipo catalog.

## Depends on

- **001** — `_shared/pdf.py` (WeasyPrint wrapper). 001 also bakes the WeasyPrint OS deps (Cairo, Pango, GDK-PixBuf, fonts) into the `Dockerfile`, so this initiative needs no extra system-level work.
- **003** — `TipoSolicitud.plantilla_id` (currently nullable UUID; 006 adds the FK)
- **004** — `Solicitud`, `SolicitudDetail`

## Affected Apps / Modules

- `solicitudes/pdf/` — new feature package
- `solicitudes/models/plantilla.py` — new model (replacing the placeholder UUID column)

## References

- [global/requirements.md](../../global/requirements.md) — RF-03, RF-09 (responsable genera PDF)
- [global/architecture.md](../../global/architecture.md) — `pdf` feature
- 003 plan, OQ-003-4 — FK resolution

## Implementation Details

### Model — `models/plantilla.py`

```python
class PlantillaSolicitud(Model):
    id = UUIDField(primary_key=True, default=uuid4)
    nombre = CharField(max_length=120)
    descripcion = TextField(blank=True)
    html = TextField()                              # Jinja-style placeholders ({{ var }}); rendered with Django template engine
    css = TextField(blank=True)                     # @page, fonts, layout
    activo = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

Migration also converts `TipoSolicitud.plantilla_id` (nullable `UUIDField`, introduced in 003) into `ForeignKey(PlantillaSolicitud, null=True, on_delete=SET_NULL)`.

### Variable resolution

The render context combines:
- `solicitante`: `{matricula, nombre, email, programa, semestre}` (from `UserDTO`).
- `solicitud`: `{folio, estado, created_at, updated_at, tipo_nombre}`.
- `valores`: dict of `{label_slug: rendered_value}` derived from `form_snapshot.fields` zipped with `valores`. The slug is derived deterministically (`slugify(label)`) so templates can reference `{{ valores.programa_actual }}`.
- `now`: timestamp of rendering, formatted in `America/Mexico_City`.
- `firma_lugar_fecha`: localized "Zacatecas, Zac., a 25 de abril de 2026".

Files (FILE-type fields) are not embedded in the PDF (they're separate downloads). The variable resolves to `<filename>` for human-readable reference.

### DTOs (`pdf/schemas.py`)

```python
class PlantillaDTO(BaseModel):
    model_config = {"frozen": True}
    id: UUID
    nombre: str
    descripcion: str
    html: str
    css: str
    activo: bool

class CreatePlantillaInput(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    descripcion: str = ""
    html: str = Field(min_length=1)
    css: str = ""

class UpdatePlantillaInput(CreatePlantillaInput):
    id: UUID

class PdfRenderResult(BaseModel):
    model_config = {"frozen": True, "arbitrary_types_allowed": True}
    folio: str
    bytes_: bytes
    suggested_filename: str        # e.g., "constancia-estudios-SOL-2026-00042.pdf"
```

### Exceptions (`pdf/exceptions.py`)

```python
class PlantillaNotFound(NotFound):                 code = "plantilla_not_found";       user_message = "La plantilla no existe."
class PlantillaTemplateError(DomainValidationError):
                                                   code = "plantilla_template_error";   user_message = "La plantilla tiene un error de sintaxis."
class TipoHasNoPlantilla(Conflict):                code = "tipo_has_no_plantilla";      user_message = "Este tipo de solicitud no tiene plantilla configurada."
```

### Repository (`pdf/repositories/plantilla/`)

Standard CRUD, returns `PlantillaDTO`.

### Service (`pdf/services/pdf_service/`)

```python
class PdfService(ABC):
    @abstractmethod
    def render_for_solicitud(self, folio: str, requester: UserDTO) -> PdfRenderResult: ...
        # raises TipoHasNoPlantilla, SolicitudNotFound, Unauthorized
```

Flow:
1. `solicitud = lifecycle_service.get_detail(folio)` — through `LifecycleService` interface.
2. Authorize: `requester` is solicitante, responsible-role personal, or admin. Raise `Unauthorized` otherwise.
3. `tipo = solicitud.tipo`. If `tipo.plantilla_id is None`: raise `TipoHasNoPlantilla`.
4. `plantilla = plantilla_repo.get_by_id(tipo.plantilla_id)`.
5. Build context (see "Variable resolution").
6. `html_rendered = django.template.engines["django"].from_string(plantilla.html).render(context)`.
7. `pdf_bytes = render_pdf(html=full_html_with_css(html_rendered, plantilla.css))` — using `_shared/pdf.py`.
8. `suggested_filename = f"{slugify(tipo.nombre)}-{folio}.pdf"`.
9. Return `PdfRenderResult`.

Catch `TemplateSyntaxError` → `PlantillaTemplateError(field_errors={"html": [str(exc)]})`.

### Service for plantilla CRUD (`pdf/services/plantilla_service/`)

Standard admin CRUD service. Validates that `html` is a parseable Django template at save time (catches errors before they bite during render).

### Views

#### Admin — plantilla CRUD

| URL | View | Mixin |
|---|---|---|
| `solicitudes/admin/plantillas/` | `PlantillaListView` | `AdminRequiredMixin` |
| `solicitudes/admin/plantillas/nueva/` | `PlantillaCreateView` | same |
| `solicitudes/admin/plantillas/<uuid:id>/` | `PlantillaDetailView` (with preview) | same |
| `solicitudes/admin/plantillas/<uuid:id>/editar/` | `PlantillaEditView` | same |

The detail page renders a sample PDF using a synthetic context (matricula `99999`, lorem-ipsum values), so the admin can iterate on layout without creating a real solicitud.

The tipo edit page (003) gets a `plantilla_id` `<select>` populated from active `PlantillaSolicitud`s.

#### Download — `pdf/views/download.py`

| URL | View | Method | Mixin |
|---|---|---|---|
| `solicitudes/<folio>/pdf/` | `RenderSolicitudPdfView` | GET | `LoginRequiredMixin` (authz inside service) |

Returns `HttpResponse(pdf_bytes, content_type="application/pdf")` with `Content-Disposition: attachment; filename="<suggested>"`.

Solicitante can download once `estado == FINALIZADA` (per RF-09 phrasing); personal and admin can render at any estado for preview / verification. Enforced in service.

### Templates

```
templates/solicitudes/admin/plantillas/
├── list.html
├── form.html
└── detail.html             # editor + sample preview iframe (data: URL)
```

No template for the rendered PDF itself — it's literal HTML stored in the DB.

### Cross-app dependencies

- `solicitudes.lifecycle.LifecycleService` (consumed for `get_detail`).
- `usuarios.UserService` (consumed for solicitante hydration if `solicitud.solicitante` lacks SIGA fields).

### Sequencing

1. Model + migration (introduce `PlantillaSolicitud`, convert `tipo.plantilla_id` to FK).
2. Schemas, exceptions.
3. Plantilla repo + service + tests (template parse validation).
4. Plantilla admin views + templates.
5. PdfService + tests (render WeasyPrint to bytes; assert bytes start with `%PDF`).
6. Download view + tests (authz matrix, no-plantilla → 409).
7. Hook plantilla `<select>` into `tipos/forms/tipo_form.py`.
8. End-to-end: create plantilla, attach to tipo, create solicitud, finalize, download PDF.


## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)
- Cross-feature: solicitud reaches `FINALIZADA` for a tipo with a plantilla → personal triggers PDF generation → solicitante downloads the PDF (`Content-Type: application/pdf`, bytes start with `%PDF`, non-zero length).
- Negative: tipo with `plantilla_id is None` → 409 `tipo_has_no_plantilla`.

### Browser (Tier 2 — `pytest-playwright`)
- Golden path: personal generates the PDF from the detail page; solicitante downloads it from their list.

## Acceptance Criteria

- [ ] Plantilla CRUD works admin-only; invalid Django template syntax rejected at save.
- [ ] Tipo edit form lists active plantillas; selection persists; `plantilla_id` nullable allowed.
- [ ] `GET /solicitudes/<folio>/pdf/` returns `application/pdf` bytes starting with `%PDF` for authorized users.
- [ ] No-plantilla tipo → 409 `tipo_has_no_plantilla`.
- [ ] Solicitante can download only when `estado == FINALIZADA`; personal/admin any estado.
- [ ] Variables substitute correctly: `{{ solicitante.nombre }}`, `{{ solicitud.folio }}`, `{{ valores.<slug> }}`, `{{ now }}`.
- [ ] Re-generating the PDF for the same folio produces byte-identical output (same context → same bytes; tested with `freezegun`).
- [ ] Tests: service ≥ 95%, repo ≥ 95%, views ≥ 80%.

## Open Questions

- **OQ-006-1** — Letterhead / logo: do we vendor `static/img/escudo.png` and reference it via `file://` in the template? WeasyPrint supports `base_url` so relative paths resolve. Plan: yes, expose `STATIC_ROOT` as `base_url` on render.
- **OQ-006-2** — Signatures (digital): out of scope for v1. The PDF is a print-and-sign artifact.
- **OQ-006-3** — Multiple plantillas per tipo (e.g., one for "kardex parcial" and one for "kardex completo"): not in v1. The plantilla `<select>` is single-valued.
