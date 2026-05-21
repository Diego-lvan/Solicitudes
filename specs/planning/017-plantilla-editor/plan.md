# 017 — Plantilla Editor & Asset Library

## Summary

Rediseño del editor admin de plantillas PDF (`solicitudes/pdf/`) más biblioteca nueva de imágenes (`solicitudes/plantilla_assets/`). El editor pasa de form plano a layout de 3 columnas: panel lateral con tabs (Variables / Campos / Imágenes) cuyos chips insertan snippets en la posición del cursor del textarea HTML; preview HTML en vivo en iframe con debounce; botón "Ver PDF real" que renderiza con WeasyPrint en pestaña nueva. La biblioteca de imágenes permite uploads scoped global (institucionales) o por-plantilla, embebidos como `data:` URI en el PDF para preservar el contrato de determinismo (RF-PDF determinismo).

## Depends on

- **006** — PDF Generation. Esta iniciativa **extiende** el feature `pdf` (vistas admin, render context, preview endpoint) y agrega el contexto `assets.*` al `build_render_context`.
- **003** — Catalog & Dynamic Forms. El tab "Campos" del panel necesita `TipoService.get_for_admin(tipo_id)` para listar los `FieldDefinition` y derivar los slugs `valores.<slug>` que el render context usa.
- **015** — Tailwind v4 Frontend Migration. El layout de 3 columnas se construye sobre el stack Tailwind v4 + Alpine.js v3 + Lucide.

## Affected Modules

- `app/solicitudes/pdf/views/edit.py` — rediseño del flujo edit (pasa `tipo_id` opcional al template; redirige al editor nuevo).
- `app/solicitudes/pdf/views/create.py` — análogo (versión create del editor).
- `app/solicitudes/pdf/views/preview_draft.py` (nuevo) — endpoint POST que renderiza HTML+CSS+context sintético sin guardar; opcionalmente persiste el draft en `request.session`.
- `app/solicitudes/pdf/views/preview_draft_pdf.py` (nuevo) — lee el draft de session y devuelve PDF inline.
- `app/solicitudes/pdf/context.py` — `build_render_context` y `build_synthetic_context` reciben `assets: dict[str, str]` (slug → data URI).
- `app/solicitudes/pdf/services/pdf_service/implementation.py` — resuelve assets al render: inyecta `assets` al contexto leyendo `AssetService.list_for_render(plantilla_id)`.
- `app/solicitudes/pdf/dependencies.py` — `DefaultPdfService` recibe `AssetService` (cross-feature service interface).
- `app/solicitudes/pdf/forms/plantilla_form.py` — sin cambios funcionales; el form sigue parseando nombre/descripcion/html/css/activo.
- `app/solicitudes/pdf/urls.py` — agregar `path("preview/", ...)` y `path("preview/pdf/", ...)`.
- `app/solicitudes/plantilla_assets/` (nuevo feature folder completo).
- `app/solicitudes/models/plantilla_asset.py` (nuevo).
- `app/solicitudes/migrations/0007_plantilla_asset.py` (nuevo).
- `app/solicitudes/urls.py` — incluir `path("admin/plantilla-assets/", include("solicitudes.plantilla_assets.urls"))`.
- `app/templates/solicitudes/admin/plantillas/form.html` — rediseño completo.
- `app/templates/solicitudes/admin/_partials/_assets_panel.html` (nuevo).
- `app/templates/solicitudes/admin/_partials/_asset_upload_modal.html` (nuevo).
- `app/templates/solicitudes/admin/plantilla_assets/list.html` (nuevo).
- `app/templates/solicitudes/admin/plantilla_assets/confirm_delete.html` (nuevo).
- `app/templates/components/sidebar.html` — agregar enlace "Imágenes de plantillas" bajo Catálogo (admin).
- `app/static/js/plantilla_editor.js` (nuevo) — componente Alpine para inserción en cursor, debounce del preview, modal de upload. Cargado vía `<script>` directo (sin bundler).

## References

- [requirements.md](../../apps/solicitudes/plantilla_editor/requirements.md) — WHAT/WHY de esta iniciativa.
- [solicitudes/pdf/design.md](../../apps/solicitudes/pdf/design.md) — diseño actual del feature `pdf` que se está extendiendo.
- [solicitudes/tipos/design.md](../../apps/solicitudes/tipos/design.md) — `TipoService.get_for_admin` y `FieldDefinition` slug derivation.
- [global/architecture.md](../../global/architecture.md) — stack y reglas globales.
- [global/requirements.md](../../global/requirements.md) — RF-03 (plantillas con variables), RT-07 (max 10MB por archivo — aquí se aplica un límite más estricto de 2MB para assets).
- [planning/006-pdf-generation/plan.md](../006-pdf-generation/plan.md) — contexto del feature original.
- [django-code-architect.md](../../../.claude/rules/django-code-architect.md) — ley arquitectónica.
- [django-patterns/features.md](../../../.claude/skills/django-patterns/features.md) — patrones de feature.
- [django-patterns/frontend-design](../../../.claude/skills/frontend-design/) — convenciones UI.

## Implementation Details

### 1. Modelo nuevo: `PlantillaAsset`

Archivo: `app/solicitudes/models/plantilla_asset.py`.

```python
from __future__ import annotations
import uuid
from django.db import models
from django.conf import settings

class PlantillaAsset(models.Model):
    SCOPE_GLOBAL = "global"
    SCOPE_PLANTILLA = "plantilla"
    SCOPE_CHOICES = [(SCOPE_GLOBAL, "Global"), (SCOPE_PLANTILLA, "Por plantilla")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=64)
    nombre = models.CharField(max_length=120)
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    plantilla = models.ForeignKey(
        "solicitudes.PlantillaSolicitud",
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="assets",
    )
    imagen = models.FileField(upload_to="plantilla_assets/%Y/%m/")
    mime_type = models.CharField(max_length=50)
    size_bytes = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        db_table = "solicitudes_plantillaasset"
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(scope="global"),
                name="unique_global_asset_slug",
            ),
            models.UniqueConstraint(
                fields=["plantilla", "slug"],
                condition=models.Q(scope="plantilla"),
                name="unique_plantilla_asset_slug",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(scope="global", plantilla__isnull=True)
                    | models.Q(scope="plantilla", plantilla__isnull=False)
                ),
                name="plantilla_asset_scope_consistency",
            ),
        ]
        ordering = ["scope", "nombre"]
```

Migración: `0007_plantilla_asset.py` — solo `CreateModel`. Sin data migration.

### 2. Feature nuevo: `solicitudes/plantilla_assets/`

Layout (sigue `.claude/rules/django-code-architect.md`):

```
solicitudes/plantilla_assets/
├── __init__.py
├── apps.py            # opcional: si necesitamos AppConfig propio (no — sigue bajo solicitudes app)
├── constants.py       # MAX_ASSET_BYTES = 2 * 1024 * 1024; ALLOWED_MIME = {...}; ALLOWED_EXT = {...}
├── schemas.py         # PlantillaAssetDTO, PlantillaAssetRow, CreateAssetInput, AssetScope
├── exceptions.py      # AssetNotFound, InvalidImageType, ImageTooLarge, DuplicateAssetSlug
├── permissions.py     # (re-exporta AdminRequiredMixin para no acoplar)
├── dependencies.py    # get_asset_repository, get_asset_service
├── urls.py            # app_name = "plantilla_assets"
├── repositories/
│   └── asset_repository/
│       ├── __init__.py
│       ├── interface.py
│       └── implementation.py
├── services/
│   └── asset_service/
│       ├── __init__.py
│       ├── interface.py
│       └── implementation.py
├── forms/
│   ├── __init__.py
│   └── asset_form.py   # AssetUploadForm
├── views/
│   ├── __init__.py
│   └── admin.py        # ListView, UploadView, DeleteView, UploadForPlantillaView, ListJsonView
└── tests/
    ├── __init__.py
    ├── factories.py
    ├── test_repositories.py
    ├── test_services.py
    ├── test_forms.py
    └── test_views.py
```

**`schemas.py`**:

```python
from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class AssetScope(StrEnum):
    GLOBAL = "global"
    PLANTILLA = "plantilla"

class PlantillaAssetDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: UUID
    slug: str
    nombre: str
    scope: AssetScope
    plantilla_id: UUID | None
    file_path: str          # storage-relative path; service resolves to absolute when needed
    mime_type: str
    size_bytes: int
    created_at: datetime
    created_by_id: int      # or UUID depending on user model PK

class PlantillaAssetRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: UUID
    slug: str
    nombre: str
    scope: AssetScope
    plantilla_id: UUID | None
    thumb_url: str          # served from /media/...
    mime_type: str
    size_bytes: int

class CreateAssetInput(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    scope: AssetScope
    plantilla_id: UUID | None = None
    file_bytes: bytes
    original_filename: str
    mime_type: str
    created_by_id: int
```

**`exceptions.py`**:

```python
from _shared.exceptions import NotFound, DomainValidationError, Conflict

class AssetNotFound(NotFound):
    code = "asset_not_found"
    user_message = "La imagen no existe o fue eliminada."

class InvalidImageType(DomainValidationError):
    code = "invalid_image_type"
    user_message = "El archivo no es una imagen válida (solo PNG/JPG/WEBP/SVG)."

class ImageTooLarge(DomainValidationError):
    code = "image_too_large"
    user_message = "La imagen excede el tamaño máximo de 2 MB."

class DuplicateAssetSlug(Conflict):
    code = "duplicate_asset_slug"
    user_message = "Ya existe una imagen con ese nombre en este alcance."
```

**`AssetService` interface**:

```python
class AssetService(ABC):
    @abstractmethod
    def list_global(self) -> list[PlantillaAssetRow]: ...
    @abstractmethod
    def list_for_plantilla(self, plantilla_id: UUID) -> list[PlantillaAssetRow]: ...
    @abstractmethod
    def list_for_render(self, plantilla_id: UUID | None) -> list[PlantillaAssetDTO]:
        """Returns globales + (si plantilla_id) las de esa plantilla. Usado por PdfService."""
    @abstractmethod
    def create(self, input_dto: CreateAssetInput) -> PlantillaAssetRow: ...
    @abstractmethod
    def delete(self, asset_id: UUID) -> None: ...
    @abstractmethod
    def get(self, asset_id: UUID) -> PlantillaAssetDTO: ...
```

**Slug derivation** en el service: `slugify(nombre).replace("-", "_")`. Si choca con un slug ya existente dentro del mismo scope, el service raise `DuplicateAssetSlug` (no auto-sufijo — el admin elige nombre único explícito).

**Validación al `create`**:
1. `len(file_bytes) <= MAX_ASSET_BYTES` o raise `ImageTooLarge`.
2. Sniff con `Pillow.Image.open(BytesIO(file_bytes)).verify()` (bitmap) o (SVG) parse con `xml.etree.ElementTree.fromstring` y reject si contiene `<script>` o `on*=` attrs — ver OQ-2 abajo, decisión final: **rechazar SVG en MVP** (cerrar OQ-2).
3. MIME en `ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}`.
4. Extensión en `ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp"}`.

**Repository**: `OrmAssetRepository` con `get`, `list_global`, `list_for_plantilla`, `list_for_render`, `create`, `delete`. Captura `IntegrityError` con `unique_*_asset_slug` violation → `DuplicateAssetSlug`.

### 3. Resolver de assets al render context

`pdf/context.py::build_render_context(...)` recibe nuevo parámetro `assets: dict[str, str]` y lo agrega al dict bajo la key `"assets"`. Mismo con `build_synthetic_context`.

`pdf/services/pdf_service/implementation.py::DefaultPdfService`:
- Constructor recibe `asset_service: AssetService` (cross-feature service interface — no toca `AssetRepository`).
- En `render_for_solicitud`: tras leer plantilla, llama `asset_service.list_for_render(plantilla.id)`, materializa a `dict[slug] = data_uri` (helper `_dto_to_data_uri(dto)` que lee `dto.file_path` desde `MEDIA_ROOT`, base64-encodea, devuelve `f"data:{dto.mime_type};base64,{b64}"`).
- En `render_sample(plantilla_id)`: mismo procedimiento.

`_dto_to_data_uri` vive en `pdf/services/pdf_service/implementation.py` como función privada del módulo. NO usa `Pillow` ni re-encoda — solo lee bytes y base64.

**Determinismo preservado**: los `data:` URI son función pura de `(file_bytes, mime_type)`. Bajo `freeze_time` y mismo asset, el PDF generado es byte-idéntico.

### 4. Endpoint `preview_draft` (HTML render para iframe)

Ruta: `POST /admin/plantillas/preview/` (sin `<uuid>` — el draft puede ser de plantilla nueva o existente).

Vista: `PlantillaPreviewDraftView(AdminRequiredMixin, View)`:

```python
def post(self, request):
    payload = json.loads(request.body)
    html_body = payload.get("html", "")
    css_body = payload.get("css", "")
    plantilla_id = payload.get("plantilla_id")  # UUID str | None
    persist = request.GET.get("persist") == "1"

    try:
        tpl = engines["django"].from_string(html_body)
    except TemplateSyntaxError as exc:
        return self._error_html(str(exc))

    asset_service = get_asset_service()
    plantilla_uuid = UUID(plantilla_id) if plantilla_id else None
    assets_dtos = asset_service.list_for_render(plantilla_uuid)
    assets_map = {dto.slug: _dto_to_data_uri(dto) for dto in assets_dtos}

    ctx_dict = build_synthetic_context(timezone.now(), assets=assets_map)
    try:
        rendered_body = tpl.render(Context(ctx_dict))
    except TemplateSyntaxError as exc:
        return self._error_html(str(exc))
    except Exception as exc:  # render-time variable lookup, filter errors
        return self._error_html(f"Error de render: {exc}")

    full_html = assemble_html(rendered_body, css_body)
    if persist:
        request.session["plantilla_draft"] = {"html": html_body, "css": css_body,
                                              "plantilla_id": plantilla_id}
    resp = HttpResponse(full_html, content_type="text/html; charset=utf-8")
    resp["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
        "font-src data:"
    )
    resp["X-Frame-Options"] = "SAMEORIGIN"
    return resp

def _error_html(self, message: str) -> HttpResponse:
    safe = escape(message)
    body = f"""<!doctype html><html><body style="font-family:sans-serif;padding:1rem">
      <div style="border:1px solid #dc2626;background:#fef2f2;color:#991b1b;
                  padding:0.75rem;border-radius:6px" role="alert">
        <strong>Error de plantilla:</strong> <pre style="margin:0.5rem 0 0">{safe}</pre>
      </div></body></html>"""
    resp = HttpResponse(body, content_type="text/html; charset=utf-8", status=200)
    resp["X-Frame-Options"] = "SAMEORIGIN"
    return resp
```

El status es **200 incluso en error** porque el iframe necesita poder leer el body — los errores son contenido del preview, no fallas HTTP.

### 5. Endpoint `preview_draft_pdf`

Ruta: `GET /admin/plantillas/preview/pdf/`.

```python
class PlantillaPreviewDraftPdfView(AdminRequiredMixin, View):
    def get(self, request):
        draft = request.session.get("plantilla_draft")
        if not draft:
            raise DomainValidationError("Abre primero el preview HTML antes de generar el PDF.")
        # render via WeasyPrint con synthetic context, assets resueltos
        ...
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = 'inline; filename="preview.pdf"'
        return resp
```

Key de session **última-en-escribir-gana** (cerrando OQ-1) — simple y suficiente para admin con una pestaña activa. Si hay dos pestañas, la última que dispare preview con `persist=1` gana; documentado en plan, no UX bug.

### 6. Endpoint `list.json` del panel del editor

Ruta: `GET /admin/plantilla-assets/list.json?plantilla_id=<uuid>`.

Vista en `plantilla_assets/views/admin.py::AssetListJsonView`. Devuelve:

```json
{
  "global": [
    {"slug": "logo_uaz", "nombre": "Logo UAZ", "thumb_url": "/media/...",
     "snippet": "<img src=\"{{ assets.logo_uaz }}\">"}
  ],
  "plantilla": [
    {"slug": "firma_director", "nombre": "Firma Director", "thumb_url": "/media/...",
     "snippet": "<img src=\"{{ assets.firma_director }}\">"}
  ]
}
```

### 7. Vistas CRUD de la galería de assets

| URL | Vista | Método | Propósito |
|---|---|---|---|
| `/admin/plantilla-assets/` | `AssetListView(AdminRequiredMixin, View)` | GET | Galería global, paginada/scroll |
| `/admin/plantilla-assets/upload/` | `AssetUploadView` | POST | Upload global. `Accept: application/json` → 201 + JSON; HTML → redirect |
| `/admin/plantilla-assets/<uuid:asset_id>/delete/` | `AssetDeleteView` | POST | Borra. Confirm en GET. |
| `/admin/plantillas/<uuid:plantilla_id>/assets/upload/` | `AssetUploadForPlantillaView` | POST | Upload scope=plantilla. Mismo JSON/HTML negotiation. |
| `/admin/plantilla-assets/list.json` | `AssetListJsonView` | GET | JSON consumido por el editor (con `?plantilla_id=`). |

Todas requieren `AdminRequiredMixin` (de `usuarios.permissions`). El endpoint `list.json` también — admin-only.

### 8. Rediseño de `form.html`

`app/templates/solicitudes/admin/plantillas/form.html` se rescribe completamente (no se preserva el layout actual).

Estructura general:

```html
{% extends "base.html" %}
{% block content %}
<div x-data="plantillaEditor({
       previewUrl: '{% url "solicitudes:plantillas:preview_draft" %}',
       previewPdfUrl: '{% url "solicitudes:plantillas:preview_draft_pdf" %}',
       assetsJsonUrl: '{% url "solicitudes:plantilla_assets:list_json" %}',
       plantillaId: '{{ plantilla.id|default:"" }}',
       tipoId: '{{ tipo_id|default:"" }}'
     })" x-init="init()" class="grid grid-cols-12 gap-4">

  <aside class="col-span-12 lg:col-span-3">
    {% include "solicitudes/admin/_partials/_assets_panel.html" %}
  </aside>

  <section class="col-span-12 lg:col-span-5">
    <form method="post" id="plantilla-form">{% csrf_token %}
      <!-- nombre, descripcion, activo (sticky header) -->
      <textarea name="html" x-ref="htmlTextarea" x-model="html"
                @input.debounce.500ms="refreshPreview"
                class="font-mono ..."></textarea>
      <details>
        <summary>CSS</summary>
        <textarea name="css" x-model="css" @input.debounce.500ms="refreshPreview"
                  class="font-mono ..."></textarea>
      </details>
      <button type="submit">Guardar</button>
    </form>
  </section>

  <aside class="col-span-12 lg:col-span-4 sticky top-4">
    <iframe x-ref="previewFrame" sandbox="allow-same-origin"
            class="w-full h-[70vh] border" srcdoc=""></iframe>
    <button type="button" @click="openPdfPreview">Ver PDF real</button>
  </aside>

  {% include "solicitudes/admin/_partials/_asset_upload_modal.html" %}
</div>
<script src="{% static 'js/plantilla_editor.js' %}"></script>
{% endblock %}
```

### 9. `plantilla_editor.js` (Alpine component)

Pseudocódigo (vive en `static/js/plantilla_editor.js`, sin bundler — IIFE registrando el componente en `alpine:init`):

```js
document.addEventListener("alpine:init", () => {
  Alpine.data("plantillaEditor", (config) => ({
    html: "",
    css: "",
    activeTab: "variables",  // 'variables' | 'campos' | 'imagenes'
    assets: { global: [], plantilla: [] },
    variables: STATIC_VARIABLES,  // injected as JSON in panel partial
    campos: [],
    previewLoading: false,
    previewError: null,
    uploadModalOpen: false,

    async init() {
      this.html = this.$refs.htmlTextarea.value;
      this.css = document.querySelector('[name="css"]').value;
      await this.loadAssets();
      if (config.tipoId) await this.loadCampos();
      this.refreshPreview();
    },

    insert(snippet) {
      const ta = this.$refs.htmlTextarea;
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      ta.value = ta.value.slice(0, start) + snippet + ta.value.slice(end);
      ta.focus();
      ta.selectionStart = ta.selectionEnd = start + snippet.length;
      this.html = ta.value;
      this.refreshPreview();
    },

    async refreshPreview() {
      this.previewLoading = true;
      try {
        const r = await fetch(config.previewUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json",
                     "X-CSRFToken": getCsrf() },
          body: JSON.stringify({ html: this.html, css: this.css,
                                 plantilla_id: config.plantillaId || null }),
        });
        const text = await r.text();
        this.$refs.previewFrame.srcdoc = text;
        this.previewError = null;
      } catch (e) { this.previewError = e.message; }
      finally { this.previewLoading = false; }
    },

    async openPdfPreview() {
      // first persist draft, then open new tab
      await fetch(config.previewUrl + "?persist=1", { /* same body */ });
      window.open(config.previewPdfUrl, "_blank");
    },

    async uploadAsset(formData, insertAfter) {
      const r = await fetch(formData.get("scope") === "global"
        ? "/admin/plantilla-assets/upload/"
        : `/admin/plantillas/${config.plantillaId}/assets/upload/`,
        { method: "POST", body: formData,
          headers: { "Accept": "application/json", "X-CSRFToken": getCsrf() } });
      if (!r.ok) { /* show form errors */ return; }
      const asset = await r.json();
      this.assets[asset.scope].push(asset);
      this.uploadModalOpen = false;
      if (insertAfter) this.insert(asset.snippet);
    },

    async loadAssets() {
      const url = `${config.assetsJsonUrl}${config.plantillaId ? `?plantilla_id=${config.plantillaId}` : ""}`;
      const r = await fetch(url);
      this.assets = await r.json();
    },

    async loadCampos() {
      const r = await fetch(`/admin/tipos/${config.tipoId}/fields.json`);
      this.campos = await r.json();
    },
  }));
});
```

**Decisión cerrando OQ-3**: el tab "Campos" se pobla **solo cuando `?tipo_id=N` está en el querystring** (también persistir como `default_tipo_id` agrega scope sin caso de uso urgente). Documentar en design.md al cierre.

`fields.json` ya no existe en `tipos/`; **se agrega** una vista `TipoFieldsJsonView` en `app/solicitudes/tipos/views/list.py` (o nuevo `_helpers.py`) que devuelve `[{slug, label, type}, ...]` derivado de los `FieldDefinition` del tipo. Admin-only. Esto es un endpoint nuevo pero pequeño y solo para el editor.

### 10. Partial `_assets_panel.html`

```html
<div role="tablist" class="flex gap-2 border-b">
  <button role="tab" :aria-selected="activeTab==='variables'"
          @click="activeTab='variables'">Variables</button>
  <button role="tab" :aria-selected="activeTab==='campos'"
          @click="activeTab='campos'">Campos</button>
  <button role="tab" :aria-selected="activeTab==='imagenes'"
          @click="activeTab='imagenes'">Imágenes</button>
</div>

<div x-show="activeTab==='variables'">
  {# Static catalog rendered server-side, click chips invoke `insert(snippet)` #}
  <h4>Solicitante</h4>
  <button type="button" @click="insert('{{ '{{ solicitante.nombre }}' }}')"
          class="chip">Nombre</button>
  {# ... rest of static vars ... #}
</div>

<div x-show="activeTab==='campos'">
  <template x-if="!campos.length">
    <p>Asocia la plantilla a un tipo con <code>?tipo_id=...</code> para ver campos.</p>
  </template>
  <template x-for="c in campos" :key="c.slug">
    <button type="button" @click="insert(`{{ '{{ valores.' }}${c.slug}{{ ' }}' }}`)"
            class="chip" x-text="c.label"></button>
  </template>
</div>

<div x-show="activeTab==='imagenes'">
  <h4>Globales</h4>
  <div class="grid grid-cols-2 gap-1">
    <template x-for="a in assets.global" :key="a.slug">
      <button type="button" @click="insert(a.snippet)"
              class="thumb"><img :src="a.thumb_url" :alt="a.nombre"></button>
    </template>
  </div>
  <h4>De esta plantilla</h4>
  <div class="grid grid-cols-2 gap-1">
    <template x-for="a in assets.plantilla" :key="a.slug">
      <button type="button" @click="insert(a.snippet)" class="thumb"><img :src="a.thumb_url"></button>
    </template>
  </div>
  <button type="button" @click="uploadModalOpen=true">+ Subir imagen</button>
</div>
```

### 11. Partial `_asset_upload_modal.html`

Modal Tailwind + Alpine con form (`nombre`, `scope` radio global/plantilla, `imagen` file input, checkbox "insertar al subir"). On submit construye `FormData` y llama `uploadAsset(...)`.

### 12. URL routing updates

`app/solicitudes/urls.py`:

```python
urlpatterns = [
    ...,
    path("admin/plantilla-assets/",
         include("solicitudes.plantilla_assets.urls",
                 namespace="plantilla_assets")),
]
```

`app/solicitudes/pdf/urls.py` — agregar:

```python
from solicitudes.pdf.views.preview_draft import PlantillaPreviewDraftView
from solicitudes.pdf.views.preview_draft_pdf import PlantillaPreviewDraftPdfView

urlpatterns += [
    path("preview/", PlantillaPreviewDraftView.as_view(), name="preview_draft"),
    path("preview/pdf/", PlantillaPreviewDraftPdfView.as_view(), name="preview_draft_pdf"),
]
```

`app/solicitudes/plantilla_assets/urls.py`:

```python
app_name = "plantilla_assets"
urlpatterns = [
    path("", AssetListView.as_view(), name="list"),
    path("upload/", AssetUploadView.as_view(), name="upload_global"),
    path("<uuid:asset_id>/delete/", AssetDeleteView.as_view(), name="delete"),
    path("list.json", AssetListJsonView.as_view(), name="list_json"),
]
```

Y dentro de `pdf/urls.py` también:

```python
path("<uuid:plantilla_id>/assets/upload/",
     AssetUploadForPlantillaView.as_view(),  # imported from plantilla_assets
     name="upload_asset_for_plantilla"),
```

(O bien colocar este path bajo `plantilla_assets/urls.py` con un prefix distinto. Decidir: lo mantenemos en `plantilla_assets/urls.py` con path `plantilla/<uuid>/upload/` para coherencia de namespace.)

### 13. Cross-feature wiring

`solicitudes/pdf/dependencies.py` (ya existe; modificar):

```python
from solicitudes.plantilla_assets.dependencies import get_asset_service

def get_pdf_service() -> PdfService:
    return DefaultPdfService(
        plantilla_repository=get_plantilla_repository(),
        lifecycle_service=lifecycle_dependencies.get_lifecycle_service(),
        user_service=usuarios_dependencies.get_user_service(),
        asset_service=get_asset_service(),  # NEW
        logger=logging.getLogger("solicitudes.pdf.pdf_service"),
    )
```

Sigue la regla cross-feature: `PdfService` consume `AssetService` (interface), no `AssetRepository`.

### 14. Sidebar

`app/templates/components/sidebar.html` — agregar bajo Catálogo, después de "Plantillas de PDF":

```django
{% if request.user.role == 'ADMIN' %}
  <a href="{% url 'solicitudes:plantilla_assets:list' %}">Imágenes de plantillas</a>
{% endif %}
```

### 15. Decisiones cerradas (eran open questions en requirements.md)

- **OQ-1 (draft session key)**: una key fija `request.session["plantilla_draft"]`, last-write-wins. Documentar en design.
- **OQ-2 (SVG)**: **rechazar SVG en MVP**. Solo PNG/JPG/WEBP. Reabrir como iniciativa futura si emerge necesidad.
- **OQ-3 (tab Campos)**: solo querystring `?tipo_id=`, sin persistir default. Si vienen del detail del tipo, el botón "Editar plantilla" del tipo agrega el param.
- **OQ-4 (metadata auditoría)**: mostrar `created_by` y `created_at` en la galería global como columna sutil al final.
- **OQ-5 (límite global)**: sin límite duro; UI scrollable. Si crece >30 agregamos búsqueda en iniciativa futura.

## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)

- Admin POST a `preview_draft` con HTML válido → 200 + iframe-friendly HTML con context sintético interpolado.
- Admin POST a `preview_draft` con `{% if x %}` sin cerrar → 200 + banner de error inline.
- Admin POST upload de imagen válida (scope=global) → 201 JSON con `{slug, snippet, thumb_url}`; aparece en `list.json`.
- Admin POST upload de imagen >2MB → 422 con `field_errors`.
- Admin GET `preview_draft_pdf` sin draft en session → 400 (vía `DomainValidationError` middleware).
- Admin POST `preview_draft?persist=1` + GET `preview_draft_pdf` → 200 application/pdf.
- Render `/solicitudes/<folio>/pdf/` para una plantilla que referencia `{{ assets.logo_uaz }}` → PDF embebe data URI; bajo `freeze_time` byte-idéntico entre dos requests.
- Render `/solicitudes/<folio>/pdf/` para una plantilla que referencia un slug inexistente → PDF se genera con `<img src="">` (no crash).
- Borrar asset global referenciado en plantilla → render subsecuente NO crashea.
- Non-admin GET `/admin/plantilla-assets/` → 403.
- Non-admin POST `preview_draft` → 403.

### Browser (Tier 2 — `pytest-playwright`)

- Golden path admin: abrir editor de plantilla existente → click chip "Nombre" del panel Variables → ver `{{ solicitante.nombre }}` insertado en textarea HTML en posición correcta del cursor → iframe preview refresca y muestra el valor sintético.
- Subir imagen desde modal in-place: abrir editor → tab Imágenes → click "+ Subir" → completar form en modal → submit → modal cierra → thumbnail aparece en grid → click thumbnail inserta `<img>` snippet → preview refresca con la imagen renderizada.
- Botón "Ver PDF real": editar HTML → click "Ver PDF" → nueva pestaña abre con `application/pdf`.

## Acceptance Criteria

- [ ] Modelo `PlantillaAsset` y migración `0007` creados; constraints de unicidad y scope-consistency aplicados.
- [ ] Feature `solicitudes/plantilla_assets/` completo (schemas, exceptions, repository, service, forms, views, urls, dependencies, tests).
- [ ] `PdfService` consume `AssetService` (interface) y resuelve assets a `data:` URI; determinismo del PDF preservado.
- [ ] `build_render_context` y `build_synthetic_context` aceptan e inyectan `assets` en el context.
- [ ] Endpoint `POST /admin/plantillas/preview/` renderiza HTML+CSS+context sintético en respuesta iframe-segura; errores de sintaxis no producen 500.
- [ ] Endpoint `GET /admin/plantillas/preview/pdf/` lee draft de session y devuelve PDF inline.
- [ ] CRUD de assets globales en `/admin/plantilla-assets/` (list, upload, delete) — admin-only.
- [ ] Upload de assets scope=plantilla disponible desde el editor sin abandonar la página (modal + JSON response).
- [ ] Rediseño completo de `templates/solicitudes/admin/plantillas/form.html` a layout 3 columnas con tabs Variables/Campos/Imágenes.
- [ ] Click en chips del panel inserta snippet en posición exacta del cursor del textarea HTML.
- [ ] Preview iframe se refresca con debounce 500ms tras cambios en HTML/CSS.
- [ ] Botón "Ver PDF real" abre WeasyPrint render en pestaña nueva.
- [ ] Tab "Campos" del panel se pobla con campos del tipo cuando `?tipo_id=N` está en la URL.
- [ ] Sidebar admin lista "Imágenes de plantillas" bajo Catálogo.
- [ ] Borrado de asset con confirmación; render de plantillas que lo referenciaban no crashea (renderiza `<img src="">`).
- [ ] Plantillas existentes (sin `assets.*`) siguen renderizando byte-idénticas bajo `freeze_time`.
- [ ] Non-admin recibe 403 en toda la superficie nueva.
- [ ] Cobertura de tests: repositories (DB real), services (fake repos), forms (validación de imagen), views (HTTP + authz), e2e Playwright para los 3 golden paths.

## Open Questions

Ninguna abierta — OQ-1..OQ-5 del `requirements.md` cerradas en la sección 15 de Implementation Details. Si durante `/implement` aparece ambigüedad nueva, se documenta acá antes de continuar.
