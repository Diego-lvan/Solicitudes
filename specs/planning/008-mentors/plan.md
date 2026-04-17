# 008 — Mentors

## Summary

`apps/mentores` exposes the mentor catalog (a small, periodically updated list of student matrículas exempt from comprobante de pago for tipos with `mentor_exempt=True`). Admins manage the catalog via manual entry or CSV bulk upload. The intake flow consumes `MentorService.is_mentor(matricula)` to decide whether to require comprobante (replaces 004's `FalseMentorService` placeholder).

## Depends on

- **001** — `_shared`
- **002** — `Role`, `AdminRequiredMixin`
- **004** — `FalseMentorService` placeholder is replaced here

## Affected Apps / Modules

- `apps/mentores/` — new app
- `apps/solicitudes/intake/dependencies.py` — replace `FalseMentorService` with the real `MentorService`

## References

- [global/requirements.md](../../global/requirements.md) — RF-11
- The whiteboard's "CARGAS" — bulk-load of mentor matrículas; here this is a CSV import view, not a separate microservice.

## Implementation Details

### Layout

```
apps/mentores/
├── __init__.py
├── apps.py
├── urls.py
├── exceptions.py
├── schemas.py
├── permissions.py            # re-export AdminRequiredMixin
├── dependencies.py
├── models/
│   └── mentor.py
├── forms/
│   ├── add_mentor_form.py
│   └── csv_import_form.py
├── repositories/
│   └── mentor/{interface,implementation}.py
├── services/
│   ├── mentor_service/{interface,implementation}.py
│   └── csv_importer/{interface,implementation}.py
├── views/
│   ├── list.py
│   ├── add.py
│   ├── deactivate.py
│   └── import_csv.py
├── templates/                # under templates/mentores/
└── tests/
```

### Model — `models/mentor.py`

```python
class Mentor(Model):
    matricula = CharField(max_length=20, primary_key=True)
    activo = BooleanField(default=True)
    fuente = CharField(max_length=16, choices=MentorSource.choices)   # MANUAL | CSV
    nota = CharField(max_length=200, blank=True)                      # optional admin note
    fecha_alta = DateTimeField(auto_now_add=True)
    fecha_baja = DateTimeField(null=True, blank=True)
    creado_por = ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="+")

    class Meta:
        indexes = [Index(fields=["activo"])]
```

### DTOs (`schemas.py`)

```python
class MentorDTO(BaseModel):
    model_config = {"frozen": True}
    matricula: str
    activo: bool
    fuente: MentorSource
    nota: str
    fecha_alta: datetime
    fecha_baja: datetime | None

class CsvImportResult(BaseModel):
    model_config = {"frozen": True}
    total_rows: int
    inserted: int
    reactivated: int
    skipped_duplicates: int
    invalid_rows: list[dict[str, Any]]   # [{"row": 12, "matricula": "abc", "error": "matricula must be 8 digits"}]
```

### Exceptions (`exceptions.py`)

```python
class MentorNotFound(NotFound):              code = "mentor_not_found";        user_message = "El mentor no existe."
class MentorAlreadyActive(Conflict):         code = "mentor_already_active";   user_message = "El alumno ya está registrado como mentor activo."
class CsvParseError(DomainValidationError):  code = "csv_parse_error";         user_message = "El archivo CSV tiene un formato inválido."
```

### Service — `services/mentor_service/`

```python
class MentorService(ABC):
    @abstractmethod
    def is_mentor(self, matricula: str) -> bool: ...                # the hot path called by intake
    @abstractmethod
    def list(self, *, only_active: bool, page: PageRequest) -> Page[MentorDTO]: ...
    @abstractmethod
    def add(self, *, matricula: str, fuente: MentorSource, nota: str, actor: UserDTO) -> MentorDTO: ...
    @abstractmethod
    def deactivate(self, matricula: str, actor: UserDTO) -> MentorDTO: ...
```

`is_mentor` is the only cross-app entry point consumed by 004's intake. Validation: matricula format (8 digits, configurable). `add` accepts an existing inactive matricula and reactivates it (writes `fecha_alta = now`, `fecha_baja = None`).

### CSV importer (`services/csv_importer/`)

```python
class MentorCsvImporter(ABC):
    @abstractmethod
    def import_csv(self, content: bytes, *, actor: UserDTO) -> CsvImportResult: ...
```

CSV format: single column `matricula` with a header row. Reject if header missing. Per row:
- Trim whitespace, validate format.
- If matricula already active: count as `skipped_duplicates`.
- If matricula inactive: reactivate, count as `reactivated`.
- Else: insert, count as `inserted`.
- Invalid rows accumulate in `invalid_rows` (but the import is **not aborted** — partial success is acceptable).

The import runs in a single `atomic()` so a fatal error rolls back everything; row-level validation errors do not abort.

### Repository

Standard CRUD: `get_by_matricula`, `list(only_active, page)`, `upsert`, `deactivate`. The hot path `is_mentor` calls `repo.exists_active(matricula) -> bool` to skip DTO marshalling.

### Views (admin only)

| URL | View | Method | Purpose |
|---|---|---|---|
| `mentores/` | `MentorListView` | GET | List with filter (active/inactive), pagination |
| `mentores/agregar/` | `AddMentorView` | GET, POST | Manual add by matricula |
| `mentores/<matricula>/desactivar/` | `DeactivateMentorView` | POST | Soft delete |
| `mentores/importar/` | `ImportCsvView` | GET, POST | Upload CSV; success page shows `CsvImportResult` |

### Wire-up

`apps/solicitudes/intake/dependencies.py`:

```python
from apps.mentores import dependencies as mentores_dependencies

def get_intake_service() -> IntakeService:
    return DefaultIntakeService(
        ...,
        mentor_service=mentores_dependencies.get_mentor_service(),  # real impl
    )
```

But: per the cross-feature dependency rule, intake's service must consume the **interface**, not import a concrete implementation. So `IntakeService.__init__` accepts `MentorService` (interface, defined in this initiative). The `dependencies.py` resolves it to the concrete `DefaultMentorService` at boot.

### Sequencing

1. Model + migration.
2. Schemas, exceptions.
3. Repo + tests.
4. `MentorService` + tests.
5. `MentorCsvImporter` + tests (a few CSV fixtures).
6. Forms + admin views + templates.
7. Replace `FalseMentorService` in `intake/dependencies.py`.
8. End-to-end: admin imports CSV with 5 matrículas → list shows 5 active; create solicitud as one of those matrículas with a `mentor_exempt` tipo → no comprobante required; create with a non-mentor matricula → comprobante required.


## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)
- Cross-feature: admin adds matricula `M` as a mentor → alumno `M` submits intake of a `mentor_exempt=True` tipo → form does NOT require comprobante → resulting `Solicitud.pago_exento == True`.
- Cross-feature: alumno not in the mentor list submits the same `mentor_exempt` tipo → form requires comprobante; submitting without it returns `comprobante_required`.
- Cross-feature: admin deactivates mentor `M`; alumno `M` submits a new solicitud → comprobante now required. Existing solicitudes of `M` keep `pago_exento=True` (snapshot integrity).

### Browser (Tier 2 — `pytest-playwright`)
- Golden path: admin imports a CSV of mentor matrículas via the upload form; success page shows the `CsvImportResult` counts; the list view shows the imported entries.
- Golden path: admin deactivates a mentor from the list view (browser).

## Acceptance Criteria

- [ ] Admin can add a mentor manually; duplicate raises `MentorAlreadyActive` (UI shows friendly error).
- [ ] CSV import with a 100-row file: `inserted + skipped_duplicates + reactivated + len(invalid_rows) == 100`.
- [ ] Deactivating sets `activo=False`, `fecha_baja=now`. List with `only_active=True` excludes them.
- [ ] `is_mentor("12345678")` returns `True` for active mentors, `False` otherwise.
- [ ] Intake of a `mentor_exempt` tipo by a mentor: no comprobante in the form; `solicitud.pago_exento = True` in the row.
- [ ] Intake of a `mentor_exempt` tipo by a non-mentor: comprobante required.
- [ ] Coverage: service ≥ 95%, repo ≥ 95%, views ≥ 80%.

## Open Questions

- **OQ-008-1** — Matricula format: assumed 8 digits (configurable via `MENTOR_MATRICULA_REGEX` setting, default `^\d{8}$`). Confirm with the institution.
- **OQ-008-2** — Snapshot vs. live mentor check at intake: we call `is_mentor` at creation time and stamp `pago_exento` onto the solicitud (per 004's plan). Removing a user from the mentor list does not retroactively un-exempt their existing solicitudes. Confirmed by 004's stored `pago_exento`.
- **OQ-008-3** — Re-importing a CSV that contains matrículas already deactivated: should they be reactivated automatically? Default: yes (treated as `reactivated`).
