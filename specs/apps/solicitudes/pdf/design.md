# pdf — Design

> Canonical reference for the PDF Generation feature. Promoted from initiative 006's `plan.md` after `/review` cleared.

## Scope

The `pdf` feature owns:

- The `PlantillaSolicitud` ORM model (plantilla = "PDF template": Django-template HTML + CSS, admin-managed).
- The admin CRUD surface for plantillas (list, create, detail with sample preview, edit, deactivate).
- On-demand rendering of a solicitud as a PDF, composing `LifecycleService` (read), `PlantillaRepository` (template body), `UserService` (hydrate solicitante), and the WeasyPrint wrapper (`_shared/pdf.py`).
- The variable-resolution layer that converts a `SolicitudDetail` into the context dict the plantilla renders against.
- A synthetic-context preview endpoint so admins can iterate on a plantilla without a real solicitud.

The feature does **not** persist generated PDF bytes — every download re-renders from the source data so the output is always consistent with the current solicitud. Determinism is enforced via WeasyPrint's `pdf_identifier` hook so two renders of the same input under a frozen clock produce byte-identical bytes.

## Layer wiring

```
admin views (list/create/detail/edit/delete/preview)
        │
        ▼
PlantillaService (services/plantilla_service/interface.py)
        │
        ▼
PlantillaRepository (repositories/plantilla/) ─── ORM (PlantillaSolicitud)


download view (RenderSolicitudPdfView) — public, login required
        │
        ▼
PdfService (services/pdf_service/interface.py)
        │
        ├── LifecycleService           ← cross-feature, via interface
        ├── PlantillaRepository        ← intra-feature
        ├── UserService                ← cross-feature, via interface
        └── render_pdf(_shared/pdf.py) ← WeasyPrint wrapper
```

`pdf/dependencies.py` wires `OrmPlantillaRepository → DefaultPlantillaService` and `DefaultPdfService` (which composes `get_lifecycle_service()` and `get_user_service()`). `STATIC_ROOT` is passed as WeasyPrint's `base_url` so plantillas may reference `/static/...` paths if they want, but plantillas requiring byte-stability across deployments should embed assets as `data:` URIs.

## Data shapes

### Model (`solicitudes/models/plantilla_solicitud.py`)

`PlantillaSolicitud`:

- `id` UUID4 primary key.
- `nombre` CharField(120).
- `descripcion` TextField(blank=True).
- `html` TextField — Django-template body using `{{ var }}` placeholders. Rendered via `engines["django"].from_string(...)` at PDF time; validated at save time by parsing once.
- `css` TextField(blank=True) — wrapped in `<style>` and prepended to the body before WeasyPrint sees it.
- `activo` BooleanField(default=True).
- `created_at` / `updated_at`.
- Index: `(activo, nombre)`.
- Default ordering: `nombre`.
- `db_table = "solicitudes_plantillasolicitud"`.

`TipoSolicitud.plantilla` is a nullable FK to `PlantillaSolicitud`, `on_delete=SET_NULL`, `related_name="tipos"`. Migration `0003` converted the `plantilla_id` UUIDField placeholder (introduced in 003) into this real FK.

### DTOs (`pdf/schemas.py`)

All frozen Pydantic v2 models.

- **`PlantillaDTO`** — full plantilla, returned by repo `get_by_id`. Holds `html` + `css` blobs.
- **`PlantillaRow`** — trimmed for list views (omits `html`/`css`).
- **`CreatePlantillaInput`** — admin-create payload. Validates `nombre` 3..120, `html` non-empty.
- **`UpdatePlantillaInput`** — extends `CreatePlantillaInput` with `id`.
- **`PdfRenderResult`** — `{ folio: str, bytes_: bytes, suggested_filename: str }`. The trailing underscore on `bytes_` avoids shadowing the builtin; never JSON-serialised — the bytes go straight into `HttpResponse`.

`TipoSolicitudRow` was extended with `plantilla_id: UUID | None = None` (default keeps existing constructors valid) so `SolicitudDetail.tipo.plantilla_id` is reachable in templates and the PDF service without a second cross-feature lookup.

### Render context

`pdf/context.py::build_render_context(solicitud, solicitante, now)` returns:

- `solicitante`: `{ matricula, nombre, email, programa, semestre, genero }` (from `UserDTO`; `nombre` maps from `full_name`). `genero` (added by initiative 011) is the cached single-letter SIGA code (`"H"` / `"M"` / `""`); plantillas branch on it for gendered Spanish, e.g. `{% if solicitante.genero == "H" %}el{% elif solicitante.genero == "M" %}la{% else %}el/la{% endif %}`.
- `solicitud`: `{ folio, estado, tipo_nombre, created_at, updated_at }`.
- `valores`: `{ <slug>: rendered_value }` — the slug is `slug_for_label(field.label)` (Django `slugify` then `-` → `_`), zipped with `solicitud.valores` by `field_id`. FILE-typed values render as the original filename only.
- `now`: timezone-aware datetime in `America/Mexico_City`.
- `firma_lugar_fecha`: localized "Zacatecas, Zac., a {day} de {mes} de {year}".

`build_synthetic_context(now)` returns a parallel mapping with placeholder values (`matricula="99999"`, etc.) for the admin preview surface — keys mirror `build_render_context` so a plantilla that works for a real solicitud also renders for the preview without conditional logic.

`assemble_html(body, css)` wraps the rendered body with `<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>`. `<style>` is omitted when CSS is empty.

## Services

### `PlantillaService` (admin CRUD)

- `list(only_active=False) -> list[PlantillaRow]`
- `get(plantilla_id) -> PlantillaDTO`
- `create(input_dto) -> PlantillaDTO` — validates `html` parses as a Django template; raises `PlantillaTemplateError(field_errors={"html": [str(exc)]})` on `TemplateSyntaxError`.
- `update(input_dto) -> PlantillaDTO` — same validation.
- `deactivate(plantilla_id) -> None` — idempotent; raises `PlantillaNotFound` if missing.

### `PdfService` (rendering)

- `render_for_solicitud(folio, requester) -> PdfRenderResult` — full flow:
    1. `lifecycle_service.get_detail(folio)` (raises `SolicitudNotFound`).
    2. Authorise (see matrix below). Raises `Unauthorized`.
    3. If `detail.tipo.plantilla_id is None`: raise `TipoHasNoPlantilla`.
    4. `plantilla = plantilla_repo.get_by_id(detail.tipo.plantilla_id)`.
    5. `solicitante = user_service.get_by_matricula(detail.solicitante.matricula)` so SIGA-derived fields (programa, semestre) are present even if the cached row missed them.
    6. Build context, render body via `engines["django"].from_string(plantilla.html).render(ctx)` (catches `TemplateSyntaxError` → `PlantillaTemplateError`), `assemble_html`, `render_pdf(html, base_url=STATIC_ROOT, pdf_identifier=folio.encode("utf-8"))`.
    7. `suggested_filename = f"{slugify(detail.tipo.nombre)}-{folio}.pdf"`.
- `render_sample(plantilla_id) -> PdfRenderResult` — renders against `build_synthetic_context`, with `pdf_identifier=str(plantilla_id).encode("ascii")` so two consecutive previews under a frozen clock are byte-identical. Used by the admin detail page's iframe.

### Authorisation matrix (`render_for_solicitud`)

| Requester role                          | Same matrícula as solicitante? | Estado | Outcome |
| ---                                     | ---                            | ---    | ---     |
| ADMIN                                   | any                            | any    | allowed |
| CONTROL_ESCOLAR / RESPONSABLE_PROGRAMA  | any                            | any    | allowed |
| ALUMNO / DOCENTE / MENTOR (non-personal)| yes (owner)                    | FINALIZADA | allowed |
| ALUMNO / DOCENTE / MENTOR (non-personal)| yes (owner)                    | not FINALIZADA | `Unauthorized` |
| ALUMNO / DOCENTE / MENTOR (non-personal)| no                             | any    | `Unauthorized` |

Pinned by the test suite: owner/finalizada (allowed), owner/CREADA (denied), other-alumno/finalizada (denied), DOCENTE non-owner/finalizada (denied), personal/CREADA (allowed), admin/EN_PROCESO (allowed). A future refactor that broadens the personal set must update those tests.

## Repository (`pdf/repositories/plantilla/`)

`OrmPlantillaRepository` exposes `get_by_id`, `list(only_active=...)`, `create(input)`, `update(input)`, `deactivate(id)`. Returns frozen DTOs only; never models or querysets. `Model.DoesNotExist` is wrapped to `PlantillaNotFound` at every read/write site.

## Determinism

- `_shared/pdf.render_pdf(html, *, base_url=None, pdf_identifier: bytes | None = None) -> bytes` — the only WeasyPrint surface in the codebase. `pdf_identifier` is forwarded as WeasyPrint's `/ID` array seed; combined with a frozen clock (which fixes `/CreationDate` and `/ModDate`) this produces byte-identical bytes for the same input.
- Determinism holds **within** an environment. `base_url` resolves to a local filesystem path; a plantilla that references `/static/foo.png` may diverge across machines if the resolved file differs. Plantillas requiring cross-deployment byte-stability should embed images as `data:` URIs.

## Exceptions (`pdf/exceptions.py`)

All inherit from `_shared.exceptions` so the global error middleware maps them to HTTP statuses:

- **`PlantillaNotFound`** (NotFound, 404) — plantilla id does not exist.
- **`PlantillaTemplateError`** (DomainValidationError, 422) — Django template syntax error at save *or* render. Carries `field_errors={"html": [...]}` so the admin form can surface the message under the HTML textarea.
- **`TipoHasNoPlantilla`** (Conflict, 409) — `tipo.plantilla_id is None` at PDF render time.

## Views

| URL                                              | View                       | Mixin                  | Purpose |
| ---                                              | ---                        | ---                    | --- |
| `solicitudes/admin/plantillas/`                  | `PlantillaListView`        | `AdminRequiredMixin`   | List rows |
| `solicitudes/admin/plantillas/nueva/`            | `PlantillaCreateView`      | same                   | Create form |
| `solicitudes/admin/plantillas/<uuid>/`           | `PlantillaDetailView`      | same                   | Read-only + iframe preview |
| `solicitudes/admin/plantillas/<uuid>/preview.pdf`| `PlantillaPreviewView`     | same + `xframe_options_sameorigin` | Inline PDF for the iframe |
| `solicitudes/admin/plantillas/<uuid>/editar/`    | `PlantillaEditView`        | same                   | Edit form |
| `solicitudes/admin/plantillas/<uuid>/desactivar/`| `PlantillaDeactivateView`  | same                   | Soft-delete |
| `solicitudes/<folio>/pdf/`                       | `RenderSolicitudPdfView`   | `LoginRequiredMixin` (authz inside service) | Download PDF |

The download URL is constrained with `re_path(r"^(?P<folio>[A-Z]+-\d{4}-\d{4,})/pdf/$", ...)` so the literal segment `pdf` cannot collide with the intake catch-all.

`PlantillaPreviewView` returns `Content-Disposition: inline; filename="..."` so the iframe in the detail page renders the bytes in-browser rather than downloading. `RenderSolicitudPdfView` uses `attachment` for the real download flow.

## Forms (`pdf/forms/plantilla_form.py`)

`PlantillaForm` is a plain Django `Form` (not a `ModelForm`) with monospace textareas for `html` and `css`. The view is responsible for converting `cleaned_data` into a `CreatePlantillaInput` / `UpdatePlantillaInput` Pydantic DTO before calling the service.

`TipoForm` (in `solicitudes/tipos/forms/tipo_form.py`) gained a `plantilla_id` `forms.ChoiceField` populated by the view via the `plantilla_choices=[(uuid_str, nombre), ...]` constructor kwarg — the form stays free of cross-feature service references. The `_helpers.build_create_input` / `build_update_input` thread `plantilla_id` into `CreateTipoInput` / `UpdateTipoInput`.

## Templates (`templates/solicitudes/admin/plantillas/`)

`list.html` (table with empty state), `form.html` (used by both create and edit; required indicators, `role="alert"` errors, primary right of cancel; bottom card listing available variables for plantilla authors), `detail.html` (h1 + status badge + action cluster, embedded `<iframe>` of `preview.pdf` with explanatory `form-text` and "Abrir en pestaña nueva" link, raw HTML/CSS shown in `<pre>` blocks below the preview), `confirm_deactivate.html`.

The sidebar (`templates/components/sidebar.html`) shows "Plantillas de PDF" under **Catálogo** for `request.user.role == 'ADMIN'`, between "Tipos de solicitud" and "Mentores".

`templates/solicitudes/revision/detail.html` and `templates/solicitudes/intake/detail.html` show contextual "Generar PDF" / "Descargar PDF" buttons, gated on `detail.tipo.plantilla_id` (and `is_owner and detail.estado == FINALIZADA` on the alumno's intake view).

## Tests

- `pdf/tests/test_schemas.py` — Pydantic validation (frozen DTOs, min/max lengths, required fields).
- `pdf/tests/test_exceptions.py` — sentinel HTTP statuses + `field_errors` payload shape.
- `pdf/tests/test_plantilla_repository.py` — real-DB CRUD with DTO assertions.
- `pdf/tests/test_plantilla_service.py` — template syntax validation; uses a hand-rolled fake repo, no DB.
- `pdf/tests/test_context.py` — slug normalization, label→value mapping, file-value rendering, `firma_lugar_fecha` formatting.
- `pdf/tests/test_pdf_service.py` — authz matrix (owner/personal/admin/other-alumno/DOCENTE non-owner), no-plantilla → `TipoHasNoPlantilla`, byte-identical re-render under `freeze_time("2026-04-25T12:00:00+00:00")`.
- `pdf/tests/test_views.py` — admin CRUD via `Client`, alumno 403, admin preview returns inline PDF with `X-Frame-Options: SAMEORIGIN` (regression-pinned), download authz matrix end-to-end.

`pdf/tests/factories.py` exposes `make_plantilla(...)`.

## Cross-feature consumers

- `solicitudes.tipos` — `TipoForm.plantilla_id` ChoiceField is populated from `PlantillaService.list(only_active=True)`. Listed plantillas are **frozen at the moment of the form GET** — if the admin opens an edit form and the plantilla is deactivated before they POST, the FK still resolves (or remains None) without error because `on_delete=SET_NULL` is in place. Listed plantillas are also exposed on `TipoSolicitudRow.plantilla_id`.
- `solicitudes.lifecycle` — `OrmSolicitudRepository._to_detail` populates `SolicitudDetail.tipo.plantilla_id` so consumers (intake/revision templates, `PdfService`) can decide whether a PDF is renderable without re-fetching the tipo.
- `usuarios` — `PdfService` calls `UserService.get_by_matricula(...)` to hydrate solicitante fields for the render context.

## Related Specs

- [Initiative 006 plan](../../../planning/006-pdf-generation/plan.md) — the implementation blueprint this design promotes from.
- [tipos/design.md](../tipos/design.md) — the catalog feature; owns the `plantilla_id` selector on the tipo form.
- [lifecycle/design.md](../lifecycle/design.md) — provides `LifecycleService.get_detail` and the `SolicitudDetail` shape.
- [flows/pdf-generation.md](../../../flows/pdf-generation.md) — end-to-end sequence: alumno opens detail page after FINALIZADA → clicks "Descargar PDF" → service composes lifecycle + plantilla + user → WeasyPrint → response.
- [shared/infrastructure](../../../shared/infrastructure/) — `_shared/pdf.py` lives here.
