# 004 — Solicitud Lifecycle

## Summary

The core domain initiative. Implements solicitud creation (intake) by alumnos and docentes, the state machine (`CREADA → EN_PROCESO → FINALIZADA`; `CREADA → CANCELADA`; `EN_PROCESO → CANCELADA`), folio generation (`SOL-YYYY-NNNNN`), the personal review queue (shared, no exclusive ownership), per-actor list/detail/action views, the historical state log, and the snapshot of the form definition into the solicitud at creation time. File handling (005), PDF (006), notifications (007), and mentor exemption integration (008) hook into this initiative through cross-app service interfaces.

This is the largest initiative; expect 2–3 sessions to land it cleanly.

## Depends on

- **001** — `_shared` (exceptions, pagination, middleware)
- **002** — `UserService`, `Role`, permission mixins
- **003** — `TipoService`, `FormSnapshot`, `build_django_form`

## Affected Apps / Modules

- `apps/solicitudes/` — adds three new feature packages: `intake`, `revision`, `lifecycle`
- `apps/solicitudes/models/` — adds `Solicitud`, `HistorialEstado`
- `apps/_shared/audit.py` — generic activity-log writer (created here, used by 005/007/008/009)

## References

- [global/requirements.md](../../global/requirements.md) — RF-04, RF-05, RF-06, RF-08, RF-09
- [global/architecture.md](../../global/architecture.md) — state machine, folio format, snapshot
- [.claude/rules/django-code-architect.md](../../../.claude/rules/django-code-architect.md) — cross-feature dependency rule

## Implementation Details

### Layout

```
apps/solicitudes/
├── models/
│   ├── solicitud.py                # NEW
│   ├── historial_estado.py         # NEW
│   └── (existing tipo_solicitud.py, field_definition.py)
├── lifecycle/                      # FEATURE — state machine + folio
│   ├── __init__.py
│   ├── constants.py                # Estado enum, valid transitions matrix
│   ├── exceptions.py
│   ├── schemas.py
│   ├── repositories/
│   │   ├── solicitud/{interface,implementation}.py
│   │   ├── historial/{interface,implementation}.py
│   │   └── folio/{interface,implementation}.py        # sequence allocator
│   ├── services/
│   │   ├── lifecycle_service/{interface,implementation}.py
│   │   └── folio_service/{interface,implementation}.py
│   ├── dependencies.py
│   └── tests/
├── intake/                         # FEATURE — solicitante creates solicitud
│   ├── __init__.py
│   ├── urls.py
│   ├── exceptions.py
│   ├── schemas.py
│   ├── permissions.py
│   ├── dependencies.py
│   ├── forms/
│   │   └── intake_form.py          # NOT a static Form; thin wrapper around build_django_form + comprobante field
│   ├── services/
│   │   └── intake_service/{interface,implementation}.py
│   ├── views/
│   │   ├── catalog.py              # GET /solicitudes/ list of tipos for current role
│   │   ├── create.py               # GET/POST /solicitudes/crear/<slug>/
│   │   ├── mis_solicitudes.py      # GET /solicitudes/mis/
│   │   ├── detail.py               # GET /solicitudes/<folio>/
│   │   └── cancel.py               # POST /solicitudes/<folio>/cancelar/
│   ├── templates/                  # under templates/solicitudes/intake/
│   └── tests/
├── revision/                       # FEATURE — personal queue and actions
│   ├── __init__.py
│   ├── urls.py
│   ├── schemas.py
│   ├── permissions.py
│   ├── dependencies.py
│   ├── forms/
│   │   └── transition_form.py      # observaciones field
│   ├── services/
│   │   └── review_service/{interface,implementation}.py
│   ├── views/
│   │   ├── queue.py                # GET /revision/  list assigned to my role
│   │   ├── detail.py               # GET /revision/<folio>/
│   │   ├── take.py                 # POST /revision/<folio>/atender/
│   │   ├── finalize.py             # POST /revision/<folio>/finalizar/
│   │   └── cancel.py               # POST /revision/<folio>/cancelar/
│   ├── templates/                  # under templates/solicitudes/revision/
│   └── tests/
└── (existing tipos/, formularios/)
```

### Data models

#### `models/solicitud.py`

```python
class Solicitud(Model):
    folio = CharField(max_length=20, primary_key=True)         # SOL-YYYY-NNNNN
    tipo = ForeignKey(TipoSolicitud, on_delete=PROTECT)        # never delete a tipo with solicitudes
    solicitante = ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="solicitudes")
    estado = CharField(max_length=16, choices=Estado.choices, default=Estado.CREADA)
    form_snapshot = JSONField()                                # FormSnapshot.model_dump()
    valores = JSONField(default=dict)                          # dict[field_id (str), Any]; files referenced by ArchivoSolicitud (005)
    requiere_pago = BooleanField()                             # captured from tipo.requires_payment at creation
    pago_exento = BooleanField(default=False)                  # captured: was the user a mentor at creation time?
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            Index(fields=["solicitante", "-created_at"]),
            Index(fields=["estado", "-created_at"]),
            Index(fields=["tipo", "estado"]),
        ]
```

Why store `requiere_pago` and `pago_exento` on the solicitud (not derive from tipo + mentor lookup at read time):
- The mentor list changes over time. A solicitud created when the user was a mentor must not retroactively become non-exempt if they're removed from the list.
- Audit / reporting queries are stable.

#### `models/historial_estado.py`

```python
class HistorialEstado(Model):
    id = BigAutoField(primary_key=True)
    solicitud = ForeignKey(Solicitud, on_delete=CASCADE, related_name="historial")
    estado_anterior = CharField(max_length=16, choices=Estado.choices, null=True)  # null only for the initial CREADA insert
    estado_nuevo = CharField(max_length=16, choices=Estado.choices)
    actor = ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="+")
    actor_role = CharField(max_length=32, choices=Role.choices)                    # snapshot the role too
    observaciones = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [Index(fields=["solicitud", "-created_at"])]
```

The `actor_role` snapshot lets us answer "which role moved this to FINALIZADA" historically, even if the actor's role changes later.

### `lifecycle/constants.py`

```python
class Estado(str, Enum):
    CREADA = "CREADA"
    EN_PROCESO = "EN_PROCESO"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"

# (estado_actual, accion) -> estado_destino
TRANSITIONS: dict[tuple[Estado, str], Estado] = {
    (Estado.CREADA,     "atender"):   Estado.EN_PROCESO,
    (Estado.EN_PROCESO, "finalizar"): Estado.FINALIZADA,
    (Estado.CREADA,     "cancelar"):  Estado.CANCELADA,
    (Estado.EN_PROCESO, "cancelar"):  Estado.CANCELADA,
}

TERMINAL: set[Estado] = {Estado.FINALIZADA, Estado.CANCELADA}
```

Cancellation **authorization** layered on top:
- Solicitante: only from `CREADA`.
- Personal in `tipo.responsible_role`: from `CREADA` or `EN_PROCESO`.
- Admin: any non-terminal estado.

### Pydantic DTOs (`lifecycle/schemas.py`)

```python
class SolicitudRow(BaseModel):
    model_config = {"frozen": True}
    folio: str
    tipo_id: UUID
    tipo_nombre: str
    solicitante_matricula: str
    solicitante_nombre: str
    estado: Estado
    requiere_pago: bool
    created_at: datetime
    updated_at: datetime

class HistorialEntry(BaseModel):
    model_config = {"frozen": True}
    id: int
    estado_anterior: Estado | None
    estado_nuevo: Estado
    actor_matricula: str
    actor_nombre: str
    actor_role: Role
    observaciones: str
    created_at: datetime

class SolicitudDetail(BaseModel):
    model_config = {"frozen": True}
    folio: str
    tipo: TipoSolicitudRow
    solicitante: UserDTO
    estado: Estado
    form_snapshot: FormSnapshot
    valores: dict[str, Any]                    # field_id (str) -> primitive
    requiere_pago: bool
    pago_exento: bool
    created_at: datetime
    updated_at: datetime
    historial: list[HistorialEntry]

class CreateSolicitudInput(BaseModel):
    tipo_id: UUID
    solicitante_matricula: str
    valores: dict[str, Any]                    # already validated by build_django_form
    is_mentor_at_creation: bool                # resolved by intake_service via mentor service
    # files are managed by 005 separately (uploaded after the solicitud row exists)

class TransitionInput(BaseModel):
    folio: str
    actor_matricula: str
    observaciones: str = Field(default="", max_length=2000)
```

### Exceptions

#### `lifecycle/exceptions.py`

```python
class SolicitudNotFound(NotFound):                code = "solicitud_not_found";       user_message = "La solicitud no existe."
class InvalidStateTransition(Conflict):
    code = "invalid_state_transition"
    def __init__(self, current: Estado, action: str):
        super().__init__(f"cannot {action} from {current.value}")
        self.user_message = f"No se puede aplicar '{action}' a una solicitud en estado {current.value}."
class FolioCollision(Conflict):                   code = "folio_collision";           user_message = "Conflicto generando folio. Reintenta."
```

#### `intake/exceptions.py`

```python
class CreatorRoleNotAllowed(Unauthorized):       code = "creator_role_not_allowed";   user_message = "Tu rol no puede crear este tipo de solicitud."
class ComprobanteRequired(DomainValidationError):code = "comprobante_required";      user_message = "Este tipo requiere comprobante de pago."
```

### Folio service (`lifecycle/services/folio_service`)

```python
class FolioService(ABC):
    @abstractmethod
    def next_folio(self, *, year: int) -> str: ...                     # returns "SOL-YYYY-NNNNN"
```

`DefaultFolioService` delegates to `FolioRepository.allocate(year) -> int`. Implementation strategies (choose at impl time, not now):

- **A. Postgres sequence per year** — `nextval('folio_seq_2026')`. Pros: scales, no contention. Cons: requires DDL on year rollover.
- **B. Counter row + `SELECT … FOR UPDATE`** — `FolioCounter(year, last)` table; `atomic` block locks the row, increments. Pros: portable to SQLite for dev (we accept lower throughput). Cons: contention at scale, not a concern here.

We pick **B**: simpler, works with SQLite. `FolioRepository.allocate(year)`:

```python
with atomic():
    counter, _ = FolioCounter.objects.select_for_update().get_or_create(year=year, defaults={"last": 0})
    counter.last += 1
    counter.save(update_fields=["last"])
    return counter.last
```

Format: `f"SOL-{year}-{n:05d}"`.

### Lifecycle service (`lifecycle/services/lifecycle_service`)

```python
class LifecycleService(ABC):
    @abstractmethod
    def get_detail(self, folio: str) -> SolicitudDetail: ...
    @abstractmethod
    def list_for_solicitante(self, matricula: str, *, page: PageRequest, filters: SolicitudFilter) -> Page[SolicitudRow]: ...
    @abstractmethod
    def list_for_personal(self, role: Role, *, page: PageRequest, filters: SolicitudFilter) -> Page[SolicitudRow]: ...
    @abstractmethod
    def transition(self, *, action: str, input_dto: TransitionInput, actor: UserDTO) -> SolicitudDetail: ...
```

`transition` is the heart of the state machine:

```
1. solicitud = repo.get_by_folio(folio)         # raises SolicitudNotFound
2. authorize_transition(solicitud, action, actor)
       # rules per action:
       # - atender: actor.role == solicitud.tipo.responsible_role OR Role.ADMIN
       # - finalizar: same
       # - cancelar: solicitante (only CREADA), responsible role (CREADA|EN_PROCESO), admin (any non-terminal)
3. estado_destino = TRANSITIONS[(solicitud.estado, action)]   # KeyError -> InvalidStateTransition
4. with atomic():
       repo.update_estado(folio, new=estado_destino, updated_at=now)
       historial_repo.append(folio, prev=solicitud.estado, next=estado_destino, actor=actor, observaciones=...)
5. notification_service.notify_state_change(folio, estado_destino, observaciones)
       # 007 plugs in here; for now the call uses an injected NotificationService that is a no-op until 007 lands
6. activity_log.write("solicitud.estado_cambiado", folio=folio, from=..., to=..., actor=...)   # _shared/audit.py
7. return get_detail(folio)
```

### Intake service (`intake/services/intake_service`)

```python
class IntakeService(ABC):
    @abstractmethod
    def list_creatable_tipos(self, role: Role) -> list[TipoSolicitudRow]: ...
    @abstractmethod
    def get_intake_form(self, slug: str, role: Role) -> tuple[TipoSolicitudDTO, type[forms.Form]]: ...
    @abstractmethod
    def create(self, input_dto: CreateSolicitudInput, actor: UserDTO) -> SolicitudDetail: ...
    @abstractmethod
    def cancel_own(self, folio: str, actor: UserDTO, observaciones: str) -> SolicitudDetail: ...
```

`create` flow:

```
1. tipo = tipo_service.get_for_creator(slug, role=actor.role)
       # raises Unauthorized if creator_roles ∉ actor.role
2. snapshot = tipo_service.snapshot(tipo.id)
3. comprobante_required = tipo.requires_payment AND not (tipo.mentor_exempt AND input_dto.is_mentor_at_creation)
   # the boolean is_mentor_at_creation is resolved by the VIEW via mentor_service.is_mentor(actor.matricula) BEFORE calling create
   # the service trusts the boolean (it's part of the input DTO and tested) — keeping the cross-feature call OUT of intake_service
4. validate values against snapshot via build_django_form(snapshot)(data=input_dto.valores)
       # if invalid -> DomainValidationError with field_errors
5. with atomic():
     folio = folio_service.next_folio(year=now().year)
     row = solicitud_repo.create(
        folio=folio,
        tipo_id=tipo.id,
        solicitante_matricula=actor.matricula,
        estado=CREADA,
        form_snapshot=snapshot.model_dump(),
        valores=normalized_values,
        requiere_pago=tipo.requires_payment,
        pago_exento=(tipo.mentor_exempt AND input_dto.is_mentor_at_creation),
     )
     historial_repo.append(folio, prev=None, next=CREADA, actor=actor, observaciones="")
6. notification_service.notify_creation(folio, tipo.responsible_role)
7. return lifecycle_service.get_detail(folio)
```

Files (RF-10) are uploaded as part of the same form submission but persisted by 005's service — see Cross-app dependencies.

`cancel_own` is a thin wrapper that calls `lifecycle_service.transition(action="cancelar", ...)` after asserting `actor.matricula == solicitud.solicitante`. Lives in intake (not lifecycle) because it's the solicitante's verb, not personal's.

### Review service (`revision/services/review_service`)

```python
class ReviewService(ABC):
    @abstractmethod
    def list_assigned(self, role: Role, *, page: PageRequest, filters: SolicitudFilter) -> Page[SolicitudRow]: ...
    @abstractmethod
    def get_detail_for_personal(self, folio: str, role: Role) -> SolicitudDetail: ...
    @abstractmethod
    def take(self, folio: str, actor: UserDTO, observaciones: str) -> SolicitudDetail: ...
    @abstractmethod
    def finalize(self, folio: str, actor: UserDTO, observaciones: str) -> SolicitudDetail: ...
    @abstractmethod
    def cancel(self, folio: str, actor: UserDTO, observaciones: str) -> SolicitudDetail: ...
```

Each method authorizes (`actor.role == tipo.responsible_role` OR `actor.role == Role.ADMIN`) then delegates to `lifecycle_service.transition`. Shared queue: any user with the responsible role sees the row in `list_assigned`. There is no `assigned_to` field; first-write-wins on contention (acceptable per spec D).

### Filters DTO

```python
class SolicitudFilter(BaseModel):
    estado: Estado | None = None
    tipo_id: UUID | None = None
    folio_contains: str | None = None
    solicitante_contains: str | None = None       # matches matricula or full_name
    created_from: date | None = None
    created_to: date | None = None
```

`OrmSolicitudRepository.list(...)` builds a queryset from these. Pagination uses `Page[SolicitudRow]` from `_shared/pagination.py`.

### Views

#### Solicitante (intake)

| URL | View | Method | Mixin |
|---|---|---|---|
| `solicitudes/` | `CatalogView` | GET | `LoginRequiredMixin` |
| `solicitudes/crear/<slug>/` | `CreateSolicitudView` | GET, POST | `LoginRequiredMixin` |
| `solicitudes/mis/` | `MisSolicitudesView` | GET | `LoginRequiredMixin` |
| `solicitudes/<folio>/` | `SolicitudDetailView` | GET | `LoginRequiredMixin` (owner OR responsible-role personal OR admin) |
| `solicitudes/<folio>/cancelar/` | `CancelOwnView` | POST | `LoginRequiredMixin` (owner only, only when estado=CREADA) |

`CreateSolicitudView.post` flow (concrete):
1. Resolve `tipo` via slug; reject if `actor.role ∉ tipo.creator_roles` (re-checked in service).
2. Build form: `FormCls = build_django_form(snapshot); form = FormCls(request.POST, request.FILES)`.
3. If `tipo.requires_payment` and not (mentor and `tipo.mentor_exempt`): inject a `comprobante` `FileField` (required) into the form via a thin wrapper. Mentor lookup: `mentor_service.is_mentor(actor.matricula)` — this is the only place intake touches mentors; the result feeds `is_mentor_at_creation`.
4. `form.is_valid()` → build `CreateSolicitudInput(...)` → `intake_service.create(...)`.
5. On `DomainValidationError.field_errors`: re-render with errors attached.
6. On success: 302 → `solicitudes:intake:detail` with `messages.success("Solicitud creada con folio FOLIO")`.
7. Files (per-field `FileField`s) are saved through 005's storage service inside the same `atomic()` block.

#### Personal (revision)

| URL | View | Method | Mixin |
|---|---|---|---|
| `revision/` | `QueueView` | GET | `PersonalRequiredMixin` (filters by user's role) |
| `revision/<folio>/` | `RevisionDetailView` | GET | `PersonalRequiredMixin` (and `tipo.responsible_role == actor.role` OR admin) |
| `revision/<folio>/atender/` | `TakeView` | POST | same |
| `revision/<folio>/finalizar/` | `FinalizeView` | POST | same |
| `revision/<folio>/cancelar/` | `CancelByPersonalView` | POST | same |

### URLs (final shape after 004)

```python
# config/urls.py
urlpatterns = [
    path("auth/", include(("apps.usuarios.urls", "usuarios"))),
    path("solicitudes/admin/tipos/", include(("apps.solicitudes.tipos.urls", "tipos"))),
    path("solicitudes/", include(("apps.solicitudes.intake.urls", "intake"))),
    path("revision/", include(("apps.solicitudes.revision.urls", "revision"))),
    path("health/", health_view),
]
```

Reverse: `solicitudes:intake:detail`, `solicitudes:intake:create`, `solicitudes:revision:queue`, etc.

### Templates

```
templates/solicitudes/
├── intake/
│   ├── catalog.html              # cards of available tipos for the role
│   ├── create.html               # dynamic form + comprobante + files
│   ├── mis_solicitudes.html      # list with filters + pagination
│   ├── detail.html               # form values, archivos, historial
│   └── confirm_cancel.html
└── revision/
    ├── queue.html                # filtered list + pagination
    ├── detail.html               # same as intake/detail.html plus action buttons
    ├── confirm_take.html
    ├── confirm_finalize.html
    └── confirm_cancel.html
```

Common partials in `templates/solicitudes/_partials/`:
- `_estado_badge.html` (color-coded Bootstrap badge per Estado)
- `_solicitud_row.html` (used by both list views)
- `_historial.html` (renders the timeline)
- `_valores_render.html` (renders snapshot fields with their values)

### Cross-app dependencies (this initiative consumes)

- `apps.usuarios.services.UserService` — to enrich `SolicitudRow` with solicitante name (intake/lifecycle inject `UserService`, never `UserRepository`).
- `apps.notificaciones.NotificationService` — to dispatch on creation and transitions; **plugged in 007**. Until then, `dependencies.py` injects a `NoOpNotificationService` so 004 ships standalone. The interface is defined in 007's plan; we agree on the signature here (see Open Questions).
- `apps.mentores.MentorService` — to resolve `is_mentor(matricula)`; **plugged in 008**. Until then, inject a `FalseMentorService` (always returns False). Mentor exemption testing is therefore deferred to 008's E2E pass.
- `apps.solicitudes.archivos.ArchivoService` — for storing files at intake; **plugged in 005**. Until then, intake form's per-field `FileField`s are validated but uploaded files are discarded with a warning. Files are not testable end-to-end until 005 lands.

### `apps/_shared/audit.py`

```python
def write(event: str, **fields: Any) -> None:
    """Emit a structured log line at INFO with event=event and the rest of the kwargs.
       Adds request_id from the contextvar set by RequestIDMiddleware."""
```

Used by lifecycle, intake, revision, and later 005/007/008. No DB persistence in v1 — writes go to the JSON log stream where they can be tailed/grep'd. If compliance asks for a DB audit later, swap the impl without touching call sites.

### Sequencing

1. `models/solicitud.py`, `models/historial_estado.py`, `FolioCounter` model, migration.
2. `lifecycle/constants.py`, `lifecycle/exceptions.py`, `lifecycle/schemas.py`.
3. Folio repo + service + tests.
4. Solicitud repo + tests (real DB, with `select_related("tipo")` and historial counting).
5. Historial repo + tests.
6. Lifecycle service + tests (in-memory fakes for repos).
7. `_shared/audit.py`.
8. `intake/exceptions.py`, `intake/schemas.py`, intake form wrapper.
9. Intake service + tests (in-memory fakes; `FalseMentorService`, `NoOpNotificationService`).
10. Intake views + templates + tests.
11. Revision service + tests.
12. Revision views + templates + tests.
13. Wire URLs, dependencies.py for both features.
14. Manual end-to-end across roles: alumno creates → personal sees in queue → atender → finalizar; alumno cancels in CREADA; personal cancels in EN_PROCESO; admin cancels finalized → 409.


## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)
- Cross-feature: alumno submits intake form → solicitud lands in `CREADA` with the correct folio and historial entry → personal in `tipo.responsible_role` atiende (`CREADA → EN_PROCESO`) → personal finaliza (`EN_PROCESO → FINALIZADA`). Asserts estado transitions, `HistorialEstado` rows, and (after 007 lands) the email outbox.
- Cross-feature: alumno cancels their own solicitud while `CREADA` → estado=`CANCELADA`. Cancellation attempt while `EN_PROCESO` → 409 with friendly error.

### Browser (Tier 2 — `pytest-playwright`)
- Golden path: alumno creates and submits a solicitud through the dynamic form (browser).
- Golden path: personal in the responsible role takes a `CREADA` solicitud and finalizes it from the revision detail page (browser).

## Acceptance Criteria

### Functional
- [ ] Alumno sees `/solicitudes/` and only the tipos with `Role.ALUMNO ∈ creator_roles AND activo=True`.
- [ ] Docente sees their subset; CONTROL_ESCOLAR / RESPONSABLE_PROGRAMA see no catalog (empty list, friendly empty state).
- [ ] Submitting `/solicitudes/crear/<slug>/` creates a `Solicitud` with estado `CREADA`, a folio `SOL-2026-NNNNN`, the form snapshot, and exactly one `HistorialEstado` row (`prev=None, next=CREADA`).
- [ ] Two parallel POSTs to the same `crear/<slug>/` endpoint produce two distinct folios (folio service is atomic).
- [ ] Alumno's `mis/` view lists their solicitudes with filters (estado, tipo, fecha, folio); pagination works.
- [ ] Alumno can cancel their own solicitud only while estado=CREADA. Attempt at EN_PROCESO returns 409 with friendly message.
- [ ] Personal in `tipo.responsible_role` sees the row in `/revision/`. Personal in a different role does not.
- [ ] Atender, finalizar, cancelar actions write `HistorialEstado` rows and update `Solicitud.estado`, `updated_at`. Each emits an audit log line.
- [ ] Admin sees and acts on all solicitudes regardless of `responsible_role`.
- [ ] Detail page shows the snapshot fields with their values, the historial timeline (chronological), and (if files exist after 005) attachments.
- [ ] Field labels rendered on a finalized solicitud match the snapshot, even after the live tipo's labels change.

### Non-functional
- [ ] List queries are at most 3 SQL queries (`select_related` on `tipo`, `solicitante`; `prefetch_related` only for detail historial).
- [ ] `pytest` green; coverage: lifecycle service ≥ 95%, intake service ≥ 95%, review service ≥ 95%, repositories ≥ 95%, views ≥ 80%.
- [ ] State machine: a property-based test (`hypothesis`) generates random sequences of (estado, action) and verifies that allowed transitions succeed and disallowed raise `InvalidStateTransition`.
- [ ] No `HttpRequest` reaches services; verified by grep audit.

## Open Questions

- **OQ-004-1** — `NotificationService` interface signature. Proposed:
  ```
  notify_creation(folio: str, responsible_role: Role) -> None
  notify_state_change(folio: str, estado_destino: Estado, observaciones: str) -> None
  ```
  Confirm in 007's plan.
- **OQ-004-2** — `MentorService.is_mentor(matricula: str) -> bool`. Confirm in 008's plan.
- **OQ-004-3** — Deleting a solicitud: not allowed. Cancellation is the only "soft delete". Confirm we do not need a hard-delete admin path.
- **OQ-004-4** — Editing a solicitud after creation: NOT supported in v1 (the spec doesn't ask for it; cancel + create new is the workaround). Confirm.
- **OQ-004-5** — File attachments live separately (005), but the intake form must accept them in the same POST. The intake view temporarily holds them on disk inside the `atomic()` block; 005 owns the storage path. Plan defers concrete handling to 005, but 004 must agree on the contract: `archivo_service.store_for_solicitud(folio, field_id, uploaded_file) -> ArchivoDTO` called from the intake view inside the same transaction. Confirm in 005's plan.
