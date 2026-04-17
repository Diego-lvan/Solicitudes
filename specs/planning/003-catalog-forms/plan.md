# 003 — Catalog & Dynamic Forms

## Summary

Build the dynamic catalog: `TipoSolicitud` and `FieldDefinition` data, admin CRUD, and the runtime form-builder that turns a `TipoSolicitud` into a Django form for the intake flow (used by 004). Each tipo carries `creator_roles`, `responsible_role`, `requires_payment`, `mentor_exempt`, optional template reference (resolved in 006), and an ordered list of typed fields.

This initiative does **not** create solicitudes — it produces the catalog and the form schema. 004 consumes this to build the intake page.

## Depends on

- **001** — `_shared` infra
- **002** — `Role` enum, `AdminRequiredMixin`

## Affected Apps / Modules

- `apps/solicitudes/` — new app, with `tipos` and `formularios` features
- `templates/solicitudes/admin/` — catalog management UI

## References

- [global/requirements.md](../../global/requirements.md) — RF-01, RF-02
- [global/architecture.md](../../global/architecture.md) — `tipos` and `formularios` features under `solicitudes`
- [.claude/skills/django-patterns/features.md](../../../.claude/skills/django-patterns/features.md) — feature package layout

## Implementation Details

### Layout

```
apps/solicitudes/
├── __init__.py
├── apps.py
├── urls.py                      # includes tipos/urls.py + (later) intake/urls.py + revision/urls.py
├── models/
│   ├── __init__.py
│   ├── tipo_solicitud.py
│   └── field_definition.py
├── tipos/                       # FEATURE — admin CRUD over the catalog
│   ├── __init__.py
│   ├── urls.py
│   ├── constants.py             # FieldType enum, max field counts
│   ├── exceptions.py
│   ├── schemas.py
│   ├── permissions.py           # AdminRequiredMixin re-export
│   ├── dependencies.py
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── tipo_form.py
│   │   └── field_form.py
│   ├── repositories/
│   │   └── tipo/
│   │       ├── __init__.py
│   │       ├── interface.py
│   │       └── implementation.py
│   ├── services/
│   │   └── tipo_service/
│   │       ├── __init__.py
│   │       ├── interface.py
│   │       └── implementation.py
│   ├── views/
│   │   ├── __init__.py
│   │   ├── list.py
│   │   ├── create.py
│   │   ├── edit.py
│   │   ├── detail.py
│   │   └── delete.py
│   └── tests/
│       ├── factories.py
│       ├── fakes.py
│       ├── test_tipo_repository.py
│       ├── test_tipo_service.py
│       ├── test_tipo_views.py
│       └── test_forms.py
├── formularios/                 # FEATURE — runtime form builder consumed by 004
│   ├── __init__.py
│   ├── schemas.py               # FieldSnapshot, FormSnapshot
│   ├── builder.py               # build_django_form(snapshot) -> type[forms.Form]
│   ├── validators.py            # per FieldType validation helpers
│   └── tests/
│       └── test_builder.py
└── tests/                       # app-level integration tests, if any
```

### Data models

#### `models/tipo_solicitud.py`

```python
class TipoSolicitud(Model):
    id = UUIDField(primary_key=True, default=uuid4)
    slug = SlugField(max_length=80, unique=True)              # used in URLs (e.g., /solicitudes/crear/constancia-estudios/)
    nombre = CharField(max_length=120)
    descripcion = TextField(blank=True)
    responsible_role = CharField(max_length=32, choices=Role.choices)
    creator_roles = JSONField(default=list)                   # list[str] of Role values; validated by service
    requires_payment = BooleanField(default=False)
    mentor_exempt = BooleanField(default=False)               # only meaningful when requires_payment=True
    plantilla_id = UUIDField(null=True, blank=True)           # FK target lives in 006; nullable until then
    activo = BooleanField(default=True)                       # tombstone — never hard-delete tipos with solicitudes
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        indexes = [Index(fields=["activo", "responsible_role"])]
```

`creator_roles` is JSON for simplicity (a small set, edited rarely). The service guards against invalid values.

#### `models/field_definition.py`

```python
class FieldDefinition(Model):
    id = UUIDField(primary_key=True, default=uuid4)
    tipo = ForeignKey(TipoSolicitud, on_delete=CASCADE, related_name="fields")
    label = CharField(max_length=120)
    field_type = CharField(max_length=16, choices=FieldType.choices)
    required = BooleanField(default=True)
    order = PositiveSmallIntegerField()
    options = JSONField(default=list, blank=True)             # list[str] for SELECT; ignored otherwise
    accepted_extensions = JSONField(default=list, blank=True) # list[str] for FILE; ignored otherwise (e.g., [".pdf",".zip"])
    max_size_mb = PositiveIntegerField(default=10)            # for FILE
    placeholder = CharField(max_length=200, blank=True)
    help_text = CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["order"]
        constraints = [UniqueConstraint(fields=["tipo", "order"], name="unique_field_order_per_tipo")]
```

#### `tipos/constants.py`

```python
class FieldType(str, Enum):
    TEXT = "TEXT"
    TEXTAREA = "TEXTAREA"
    NUMBER = "NUMBER"
    DATE = "DATE"
    SELECT = "SELECT"
    FILE = "FILE"
```

### Pydantic DTOs

#### `tipos/schemas.py`

```python
class FieldDefinitionDTO(BaseModel):
    model_config = {"frozen": True}
    id: UUID
    label: str
    field_type: FieldType
    required: bool
    order: int
    options: list[str] = []
    accepted_extensions: list[str] = []
    max_size_mb: int = 10
    placeholder: str = ""
    help_text: str = ""

class TipoSolicitudDTO(BaseModel):
    model_config = {"frozen": True}
    id: UUID
    slug: str
    nombre: str
    descripcion: str
    responsible_role: Role
    creator_roles: set[Role]
    requires_payment: bool
    mentor_exempt: bool
    plantilla_id: UUID | None
    activo: bool
    fields: list[FieldDefinitionDTO]

class TipoSolicitudRow(BaseModel):
    """Trim DTO for list views (no fields, no plantilla)."""
    id: UUID
    slug: str
    nombre: str
    responsible_role: Role
    creator_roles: set[Role]
    requires_payment: bool
    activo: bool

class CreateTipoInput(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    descripcion: str = ""
    responsible_role: Role
    creator_roles: set[Role] = Field(min_length=1)
    requires_payment: bool = False
    mentor_exempt: bool = False
    plantilla_id: UUID | None = None
    fields: list[CreateFieldInput] = []

    @model_validator(mode="after")
    def _check_creator_roles(self):
        allowed = {Role.ALUMNO, Role.DOCENTE}
        if not self.creator_roles.issubset(allowed):
            raise ValueError("creator_roles only supports ALUMNO and DOCENTE")
        return self

    @model_validator(mode="after")
    def _check_mentor_exempt(self):
        if self.mentor_exempt and not self.requires_payment:
            raise ValueError("mentor_exempt is only meaningful when requires_payment is true")
        return self

class CreateFieldInput(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    field_type: FieldType
    required: bool = True
    order: int = Field(ge=0)
    options: list[str] = []
    accepted_extensions: list[str] = []
    max_size_mb: int = Field(default=10, ge=1, le=50)

    @model_validator(mode="after")
    def _check_options(self):
        if self.field_type is FieldType.SELECT and not self.options:
            raise ValueError("SELECT fields must define options")
        if self.field_type is not FieldType.SELECT and self.options:
            raise ValueError("only SELECT fields use options")
        return self

    @model_validator(mode="after")
    def _check_extensions(self):
        if self.field_type is FieldType.FILE and not self.accepted_extensions:
            raise ValueError("FILE fields must declare accepted_extensions")
        return self

class UpdateTipoInput(CreateTipoInput):
    id: UUID
```

#### `formularios/schemas.py`

```python
class FieldSnapshot(BaseModel):
    """Frozen copy of a FieldDefinition stored inside Solicitud at creation time."""
    model_config = {"frozen": True}
    field_id: UUID
    label: str
    field_type: FieldType
    required: bool
    order: int
    options: list[str] = []
    accepted_extensions: list[str] = []
    max_size_mb: int = 10
    placeholder: str = ""
    help_text: str = ""

class FormSnapshot(BaseModel):
    model_config = {"frozen": True}
    tipo_id: UUID
    tipo_slug: str
    tipo_nombre: str
    captured_at: datetime
    fields: list[FieldSnapshot]
```

`FormSnapshot` is what the intake service writes into the solicitud (`Solicitud.form_snapshot` JSON column, defined in 004). 003 produces and tests the snapshot builder; 004 consumes it.

### Exceptions (`tipos/exceptions.py`)

```python
class TipoNotFound(NotFound):                    code = "tipo_not_found";              user_message = "El tipo de solicitud no existe."
class TipoSlugConflict(Conflict):                code = "tipo_slug_conflict";          user_message = "Ya existe un tipo con ese identificador."
class TipoInUse(Conflict):                       code = "tipo_in_use";                 user_message = "El tipo no se puede eliminar porque tiene solicitudes asociadas."
class InvalidFieldDefinition(DomainValidationError):
                                                 code = "invalid_field_definition";    user_message = "La definición del campo no es válida."
```

### Repository — `tipos/repositories/tipo/`

```python
class TipoRepository(ABC):
    @abstractmethod
    def get_by_id(self, tipo_id: UUID) -> TipoSolicitudDTO: ...        # raises TipoNotFound
    @abstractmethod
    def get_by_slug(self, slug: str) -> TipoSolicitudDTO: ...
    @abstractmethod
    def list(self, *, only_active: bool, creator_role: Role | None, responsible_role: Role | None) -> list[TipoSolicitudRow]: ...
    @abstractmethod
    def create(self, input_dto: CreateTipoInput) -> TipoSolicitudDTO: ...
    @abstractmethod
    def update(self, input_dto: UpdateTipoInput) -> TipoSolicitudDTO: ...
    @abstractmethod
    def deactivate(self, tipo_id: UUID) -> None: ...
    @abstractmethod
    def has_solicitudes(self, tipo_id: UUID) -> bool: ...              # used to gate hard-delete
```

`OrmTipoRepository` uses `prefetch_related("fields")` for `get_*` and the full DTO. `list()` skips `fields` and returns `TipoSolicitudRow`. `slug` is auto-derived from `nombre` on create (`slugify` + uniqueness suffix). `update` replaces the field set transactionally (`atomic`): delete fields not in the new set, upsert the rest.

### Service — `tipos/services/tipo_service/`

```python
class TipoService(ABC):
    @abstractmethod
    def list_for_admin(self, *, only_active: bool) -> list[TipoSolicitudRow]: ...
    @abstractmethod
    def list_for_creator(self, role: Role) -> list[TipoSolicitudRow]: ...     # filters by creator_roles
    @abstractmethod
    def get_for_admin(self, tipo_id: UUID) -> TipoSolicitudDTO: ...
    @abstractmethod
    def get_for_creator(self, slug: str, role: Role) -> TipoSolicitudDTO: ...
        # raises Unauthorized if role ∉ creator_roles or tipo inactive
    @abstractmethod
    def create(self, input_dto: CreateTipoInput) -> TipoSolicitudDTO: ...
    @abstractmethod
    def update(self, input_dto: UpdateTipoInput) -> TipoSolicitudDTO: ...
    @abstractmethod
    def deactivate(self, tipo_id: UUID) -> None: ...
    @abstractmethod
    def snapshot(self, tipo_id: UUID) -> FormSnapshot: ...                   # consumed by 004's intake service
```

Business rules enforced here (not in views, not in repos):
- `creator_roles` must be a subset of `{ALUMNO, DOCENTE}`.
- `responsible_role` must be in `{CONTROL_ESCOLAR, RESPONSABLE_PROGRAMA, DOCENTE}` (admin is never a responsible).
- `mentor_exempt` requires `requires_payment`.
- Deactivate instead of delete when `has_solicitudes()` is true (raise `TipoInUse` if a hard delete is requested).
- `get_for_creator` re-checks `creator_roles ⊇ {role}` and `activo` (defense in depth — UI already filtered).
- `snapshot()` reads the active tipo and returns `FormSnapshot` with `captured_at = timezone.now()`.

### Form builder — `formularios/builder.py`

```python
def build_django_form(snapshot: FormSnapshot) -> type[forms.Form]:
    """Return a dynamically constructed Django Form class whose fields match snapshot.fields."""
```

Implementation: a metaclass-free factory that builds a class with `field_<id>` attributes. Mapping:

| `FieldType` | Django field | Widget |
|---|---|---|
| `TEXT` | `CharField(max_length=200)` | `TextInput` |
| `TEXTAREA` | `CharField(widget=Textarea(attrs={"rows":4}))` | `Textarea` |
| `NUMBER` | `DecimalField` | `NumberInput` |
| `DATE` | `DateField` | `DateInput(attrs={"type":"date"})` |
| `SELECT` | `ChoiceField(choices=[(o,o) for o in field.options])` | `Select` |
| `FILE` | `FileField(validators=[ext_validator(field.accepted_extensions), size_validator(field.max_size_mb)])` | `ClearableFileInput` |

`required` flows directly. `label`, `help_text`, and `widget.attrs["placeholder"]` come from the snapshot. The constructed class also exposes `to_values_dict(cleaned_data) -> dict[str, Any]` that serializes to JSON-safe primitives (`Decimal` → `str`, `date` → `iso`), used by the intake service in 004.

### Views (`tipos/views/`)

Admin-only (`AdminRequiredMixin`). Server-rendered with Bootstrap forms.

| URL | View | Method | Purpose |
|---|---|---|---|
| `tipos/` | `TipoListView` | GET | List with filter (active/inactive, responsible_role) |
| `tipos/nuevo/` | `TipoCreateView` | GET, POST | Create tipo + initial fields |
| `tipos/<uuid:tipo_id>/` | `TipoDetailView` | GET | Read-only detail (preview of dynamic form) |
| `tipos/<uuid:tipo_id>/editar/` | `TipoEditView` | GET, POST | Edit metadata + fields |
| `tipos/<uuid:tipo_id>/desactivar/` | `TipoDeactivateView` | POST | Soft delete |

Form ergonomics: the create/edit page uses a `TipoForm` (metadata) + a Django formset of `FieldForm` for the field rows. JavaScript adds/removes rows; backend validates the whole shape. On submit:
1. Validate `TipoForm` and `FieldFormSet` independently.
2. Build `CreateTipoInput` / `UpdateTipoInput` from `cleaned_data`. Pydantic validators surface as form errors via a service-layer adapter.
3. Call `tipo_service.create` / `update`.
4. On `TipoSlugConflict` / `InvalidFieldDefinition`: re-render with field errors.

`TipoDetailView` instantiates `build_django_form(service.snapshot(tipo_id))` and renders the form (unbound) so the admin can preview what creators will see.

### URLs

`apps/solicitudes/urls.py`:

```python
app_name = "solicitudes"
urlpatterns = [
    path("admin/tipos/", include(("apps.solicitudes.tipos.urls", "tipos"))),
    # intake/, revision/, archivos/, pdf/ added by later initiatives
]
```

`tipos/urls.py` defines the table above with `app_name = "tipos"`. Reverse: `{% url 'solicitudes:tipos:list' %}`.

### Templates

```
templates/solicitudes/admin/tipos/
├── list.html
├── form.html              # shared by create/edit
├── detail.html            # preview of dynamic form
└── confirm_deactivate.html
```

All extend `templates/base.html`. `form.html` includes a `_field_row.html` partial reused by JS-cloned rows.

### Cross-app dependencies

- Consumes `apps.usuarios.permissions.AdminRequiredMixin` and `apps.usuarios.constants.Role`.
- Produces `TipoService` and `formularios.build_django_form` consumed by 004.

### Sequencing

1. Create `apps/solicitudes/` skeleton, register in `INSTALLED_APPS`.
2. `models/tipo_solicitud.py`, `models/field_definition.py`, migration.
3. `tipos/constants.py`, `tipos/exceptions.py`, `tipos/schemas.py`.
4. Repository + tests.
5. Service + tests (in-memory fake repo).
6. `dependencies.py`.
7. Forms + view tests + view impls.
8. Templates.
9. `formularios/schemas.py`, `formularios/builder.py`, `formularios/validators.py` + tests.
10. End-to-end: admin creates "Constancia de Estudios" with 3 fields → preview renders → snapshot returns the same fields.


## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)
- _None — admin CRUD only; covered by per-feature view tests._

### Browser (Tier 2 — `pytest-playwright`)
- Golden path: admin creates a new TipoSolicitud with two FieldDefinitions; lists it; edits it.

## Acceptance Criteria

- [ ] Admin can create a tipo, set `creator_roles`, fields, payment flags; visible at `/admin/tipos/`.
- [ ] Editing a tipo updates fields atomically; existing solicitudes (when 004 is in place) remain unaffected because they hold a snapshot.
- [ ] Non-admin GET on `/admin/tipos/...` returns 403 via `_shared/error.html`.
- [ ] `tipo_service.list_for_creator(Role.ALUMNO)` returns only tipos where `Role.ALUMNO ∈ creator_roles AND activo=True`.
- [ ] `tipo_service.snapshot(tipo_id)` returns a `FormSnapshot` with all fields, ordered by `order`.
- [ ] `build_django_form(snapshot).is_valid()` accepts valid input and rejects invalid (per FieldType).
- [ ] `mentor_exempt=True` with `requires_payment=False` rejected at form/service boundary.
- [ ] `creator_roles` outside `{ALUMNO, DOCENTE}` rejected.
- [ ] Deleting a tipo with solicitudes raises `TipoInUse` (returns 409). Deactivating works.
- [ ] Tests: services ≥ 95%, repository ≥ 95%, views ≥ 80%, forms 100%, builder ≥ 95%.

## Open Questions

- **OQ-003-1** — Should field labels be edited freely after creation, or locked once a solicitud has been filed against the tipo? Locking is safer for legacy solicitudes, but the snapshot already protects them; the live form can drift visually. Default: editable, snapshot is the source of truth for old solicitudes.
- **OQ-003-2** — Field deletion / reordering UX: when an admin removes a field that historical solicitudes used, the historical solicitud still has the value (under the field's snapshot id). The list view of the historical solicitud must render the snapshot, not the live tipo. (Reinforced in 004 plan.)
- **OQ-003-3** — Maximum number of fields per tipo. Suggest 25; revisit if a real tipo needs more.
- **OQ-003-4** — Plantilla cross-reference: the `plantilla_id` column is added now but no FK constraint until 006 introduces the table. Use `JSONField` to store as raw UUID until then? Decision: keep `UUIDField` nullable now, add the FK in 006's migration.
