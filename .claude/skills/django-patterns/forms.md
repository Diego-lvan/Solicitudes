# Forms — Boundary Parsing → Pydantic DTO

Django Forms (and ModelForms) are the **boundary parser**: they take untyped HTTP input (POST data, query strings, file uploads) and produce validated `cleaned_data`. The view then converts that `cleaned_data` into a typed Pydantic DTO **before** crossing into the service layer.

`cleaned_data` (a `dict[str, Any]`) is **not** allowed to cross into a service. Services accept Pydantic DTOs only.

---

## The boundary pattern

```python
# View
form = CreateSolicitudForm(request.POST, request.FILES)
if not form.is_valid():
    return render(request, "solicitudes/intake/create.html", {"form": form}, status=400)

# Convert to typed DTO
input_dto = CreateSolicitudInput(
    user_id=request.user.id,
    tipo_solicitud_id=form.cleaned_data["tipo_solicitud_id"].id,
    titulo=form.cleaned_data["titulo"],
    descripcion=form.cleaned_data["descripcion"],
)

# Hand off
service = get_solicitud_service()
detail = service.create(input_dto)
```

The service signature is `create(self, data: CreateSolicitudInput) -> SolicitudDetail`. It never sees `request`, `cleaned_data`, or any Django Form object.

---

## Forms live in `forms/` (one per file)

```
solicitudes/intake/forms/
├── __init__.py
├── create_solicitud_form.py
├── update_solicitud_form.py
└── transition_solicitud_form.py
```

When a feature has only one form, a flat `forms.py` is acceptable. Two or more → `forms/` folder, one class per file.

---

## Standard `Form` example

```python
"""Form for creating a new solicitud."""
from __future__ import annotations

from django import forms

from solicitudes.models import TipoSolicitud


class CreateSolicitudForm(forms.Form):
    tipo_solicitud_id = forms.ModelChoiceField(
        queryset=TipoSolicitud.objects.filter(activo=True),
        label="Tipo de solicitud",
        empty_label="Selecciona un tipo",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    titulo = forms.CharField(
        label="Título",
        min_length=3,
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    descripcion = forms.CharField(
        label="Descripción",
        min_length=10,
        max_length=5000,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 6}),
    )

    def clean_titulo(self) -> str:
        return self.cleaned_data["titulo"].strip()

    def clean_descripcion(self) -> str:
        return self.cleaned_data["descripcion"].strip()
```

**Rules:**
- All `label`s in Spanish (user-facing copy)
- Widgets carry Bootstrap 5 classes (`form-control`, `form-select`, etc.) — see the `frontend-design` skill
- Per-field cleanup in `clean_<field>()`; cross-field validation in `clean()`
- The form does NOT call services or repositories. Pure parsing + validation.

---

## When to use `ModelForm`

`ModelForm` is for **simple CRUD** where the form fields map 1:1 to model fields and you want Django's automatic field generation. The boundary rule still applies: convert to a Pydantic DTO before crossing into the service.

```python
class UpdateSolicitudModelForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ["titulo", "descripcion"]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
        }
```

**Important:** never call `form.save()` from the view. `form.save()` writes through the ORM, which violates the layering. Instead:

```python
# View
if form.is_valid():
    input_dto = UpdateSolicitudInput(
        folio=folio,
        actor_user_id=request.user.id,
        titulo=form.cleaned_data["titulo"],
        descripcion=form.cleaned_data["descripcion"],
    )
    service.update(input_dto)
```

If you find yourself wanting `form.save()`, you're skipping the service. That's a violation.

---

## Pydantic ↔ Form: writing the DTO from `cleaned_data`

Three idioms, in order of preference:

**1. Explicit construction (preferred — most readable):**

```python
input_dto = CreateSolicitudInput(
    user_id=request.user.id,
    tipo_solicitud_id=form.cleaned_data["tipo_solicitud_id"].id,
    titulo=form.cleaned_data["titulo"],
    descripcion=form.cleaned_data["descripcion"],
)
```

**2. `model_validate` with selected keys:**

```python
input_dto = CreateSolicitudInput.model_validate({
    "user_id": request.user.id,
    "tipo_solicitud_id": form.cleaned_data["tipo_solicitud_id"].id,
    **{k: v for k, v in form.cleaned_data.items() if k in {"titulo", "descripcion"}},
})
```

**3. Helper method on the form (for forms with many fields):**

```python
class CreateSolicitudForm(forms.Form):
    # ... field declarations ...

    def to_input_dto(self, *, user_id: UUID) -> CreateSolicitudInput:
        return CreateSolicitudInput(
            user_id=user_id,
            tipo_solicitud_id=self.cleaned_data["tipo_solicitud_id"].id,
            titulo=self.cleaned_data["titulo"],
            descripcion=self.cleaned_data["descripcion"],
        )

# View
input_dto = form.to_input_dto(user_id=request.user.id)
```

Use the helper-method pattern when the conversion has any logic (FK → id, model → uuid, file → path).

---

## File uploads

```python
class UploadEvidenceForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo",
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "png", "jpg"])],
    )

    def clean_archivo(self):
        f = self.cleaned_data["archivo"]
        if f.size > 5 * 1024 * 1024:  # 5 MB
            raise forms.ValidationError("El archivo no puede pesar más de 5 MB.")
        return f
```

Convert to a DTO that carries the path or bytes — not the `UploadedFile` object — so the service stays Django-agnostic:

```python
input_dto = UploadEvidenceInput(
    folio=folio,
    actor_user_id=request.user.id,
    filename=form.cleaned_data["archivo"].name,
    content_type=form.cleaned_data["archivo"].content_type,
    size_bytes=form.cleaned_data["archivo"].size,
    bytes=form.cleaned_data["archivo"].read(),
)
```

The service writes through a storage abstraction, not directly through Django's storage system.

---

## Surfacing service-layer errors back to the form

When the service raises `DomainValidationError` with `field_errors`, the view re-attaches them to the form:

```python
try:
    detail = service.create(input_dto)
except DomainValidationError as e:
    for field, errors in e.field_errors.items():
        for err in errors:
            form.add_error(field, err)
    return render(request, "solicitudes/intake/create.html", {"form": form}, status=e.http_status)
```

The user sees a re-rendered form with error messages next to the offending fields, identical to what they see for HTML-form validation. This is the bridge between the form layer and the domain layer.

---

## Multi-step forms

Use Django's `SessionWizardView` (from `formtools`) OR roll your own with a hidden `step` field. In either case:

- Each step is its own `Form` class (one per file under `forms/`).
- Final submit converts the merged `cleaned_data` from all steps into a single Pydantic DTO.
- Service receives the full DTO, not a partial step.
- Persisting partial state between steps: Django session. Don't write to the DB until the final step succeeds.

---

## Anti-patterns

- ❌ Calling a service from inside `clean()` — form is pure validation, no I/O
- ❌ Calling `form.save()` from the view — services own writes
- ❌ Passing `cleaned_data` as a `dict` into a service — convert to a typed DTO
- ❌ Putting `**form.cleaned_data` into a Pydantic constructor without selecting fields — leaks ModelChoiceField objects (which are model instances, not ids) into the DTO
- ❌ Sharing forms across features — each feature owns its forms
- ❌ Form labels in English — users read these; they must be in Spanish
- ❌ Field-level errors as plain strings without `add_error` — pre-rendered HTML with error markup defeats Django's form rendering
