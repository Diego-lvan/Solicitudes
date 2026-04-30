# mentores · catalog — Design

> Canonical reference for the mentor catalog feature shipped in initiative **008 — Mentors**. Future initiatives that touch this surface should update this file rather than redefining the contract elsewhere.

## Purpose

Maintain the institution's list of student matrículas registered as **mentors**. Mentors are exempt from the comprobante de pago requirement on tipos that set `mentor_exempt=True`. Admins manage the catalog manually (one matrícula at a time) or in bulk (CSV upload). Intake consumes a single boolean (`is_mentor(matricula)`) to drive comprobante visibility and `pago_exento` snapshot stamping.

## Data model

### `Mentor` — `mentores/models/mentor.py`

```python
class Mentor(Model):
    matricula = CharField(max_length=20, primary_key=True)
    activo = BooleanField(default=True)
    fuente = CharField(max_length=16, choices=MentorSource.choices())  # MANUAL | CSV
    nota = CharField(max_length=200, blank=True)
    fecha_alta = DateTimeField(auto_now_add=True)
    fecha_baja = DateTimeField(null=True, blank=True)
    creado_por = ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="+")

    class Meta:
        indexes = [Index(fields=["activo"])]
```

- `matricula` is the natural primary key (no surrogate id).
- `activo=False` is a **soft delete**; `fecha_baja` records when. Reactivating an inactive matrícula resets `fecha_alta = now` and clears `fecha_baja` — i.e., the catalog stores **current state only**, not history. (Initiative 012 supersedes this.)
- `creado_por` uses `PROTECT` to prevent admin user deletion from cascading and orphaning the catalog.
- `MentorSource` is a `StrEnum` in `mentores/constants.py`.

The matrícula format is enforced as a regex (default `^\d{8}$`, configurable via the `MENTOR_MATRICULA_REGEX` Django setting) by `mentores.validators.is_valid_matricula`. Both the form layer and the service layer call this validator; the service layer is authoritative because the CSV importer bypasses Django forms.

## DTOs — `mentores/schemas.py`

| DTO | Direction | Purpose |
|---|---|---|
| `MentorDTO` (frozen) | repo/service → view/template | Output shape; mirrors model fields. |
| `MentorUpsertInput` | view/service → repo | Insert / reactivate boundary. |
| `CsvImportResult` (frozen) | service → view | Counts (`total_rows`, `inserted`, `reactivated`, `skipped_duplicates`, `invalid_rows: list[dict]`). |

`invalid_rows` entries: `{"row": int, "matricula": str, "error": str}`. Row numbers are 1-based and include the header (so the first data row is `row=2`).

## Exceptions — `mentores/exceptions.py`

| Exception | Subclass of `_shared.exceptions.…` | HTTP | Spanish `user_message` |
|---|---|---|---|
| `MentorNotFound` | `NotFound` | 404 | "El mentor no existe." |
| `MentorAlreadyActive` | `Conflict` | 409 | "El alumno ya está registrado como mentor activo." |
| `CsvParseError` | `DomainValidationError` | 422 | "El archivo CSV tiene un formato inválido." |

`Mentor.DoesNotExist` is mapped to `MentorNotFound` inside the repository; Django ORM exceptions never escape that layer.

## Repository — `mentores/repositories/mentor/`

`MentorRepository` ABC + `OrmMentorRepository`:

```python
class MentorRepository(ABC):
    def get_by_matricula(self, matricula) -> MentorDTO: ...
    def exists_active(self, matricula) -> bool: ...           # hot path; primitive return
    def list(self, *, only_active, page) -> Page[MentorDTO]: ...
    def upsert(self, input_dto) -> tuple[MentorDTO, UpsertOutcome]: ...
    def deactivate(self, matricula) -> MentorDTO: ...         # idempotent on already-inactive
```

`UpsertOutcome` is a `StrEnum` with `INSERTED`, `REACTIVATED`, `ALREADY_ACTIVE`. The service uses the outcome to count reactivations vs duplicates and to decide whether to raise `MentorAlreadyActive`.

Writes are wrapped in `transaction.atomic()` with `select_for_update()` on the existing row to make concurrent admin actions safe. `OrmMentorRepository` is the **only** module in the app that touches `Mentor.objects.*`.

## Services — `mentores/services/`

### `mentor_service/`

`MentorService` ABC is the **cross-feature contract** consumed by `solicitudes/intake/`. Methods: `is_mentor`, `list`, `add`, `deactivate`. `add` validates matrícula format, calls `repo.upsert`, and raises `MentorAlreadyActive` on the `ALREADY_ACTIVE` outcome.

### `csv_importer/`

`MentorCsvImporter` ABC + `DefaultMentorCsvImporter`. Format: single column with header `matricula`. Behavior:

- Decode UTF-8 (BOM-tolerant via `utf-8-sig`).
- Reject if header missing/wrong → `CsvParseError`.
- Per row: trim whitespace, validate format. Invalid rows accumulate in `invalid_rows` and **do not abort the batch**.
- Already-active matrícula → `skipped_duplicates += 1`.
- Inactive matrícula → reactivated (counted as `reactivated`).
- New matrícula → inserted.

Wrapped in `transaction.atomic()` so an unexpected DB error rolls back the entire batch; row-level validation errors do not.

## DI wiring — `mentores/dependencies.py`

Factory functions:

- `get_mentor_repository() -> MentorRepository`
- `get_mentor_service() -> MentorService`
- `get_mentor_csv_importer() -> MentorCsvImporter`
- `get_intake_mentor_adapter() -> IntakeMentorService` — adapter satisfying intake's outbound `MentorService` port (see Cross-feature integration below).

## Views & URLs

All views are admin-only (`AdminRequiredMixin` from `usuarios.permissions`).

| URL | View | Methods | Purpose |
|---|---|---|---|
| `/mentores/` | `MentorListView` | GET | List with active/all filter + pagination |
| `/mentores/agregar/` | `AddMentorView` | GET, POST | Manual add; raises `MentorAlreadyActive` (409) on duplicate |
| `/mentores/<str:matricula>/desactivar/` | `DeactivateMentorView` | GET (confirm), POST (apply) | Soft delete |
| `/mentores/importar/` | `ImportCsvView` | GET, POST | Bulk CSV upload; result page shows the `CsvImportResult` |

The list view's filter form uses a hidden `filtered=1` sentinel so an unchecked "Solo activos" checkbox actually disables the filter (Django GET forms drop unchecked checkbox keys; the sentinel lets the view distinguish "fresh load" from "submitted with checkbox off").

## Templates — `templates/mentores/`

Five templates extending `base.html`: `list.html`, `add.html`, `import_csv.html`, `import_result.html`, `confirm_deactivate.html`. All Spanish copy, Bootstrap 5, accessibility per the `frontend-design` skill (skip-link, h1, table-responsive with `d-none d-md-table-cell` on low-priority columns, status badges with text + color, mobile reflow tested at 320px).

The catalog list links each matrícula cell to a future detail view at `/mentores/<matricula>/` (placeholder until 012 ships the timeline).

## Sidebar entry

Admin-only "Mentores" link under **CATÁLOGO** in `templates/components/sidebar.html`, sibling to "Tipos de solicitud".

## Cross-feature integration: intake adapter

Intake declares an outbound port at `solicitudes.intake.mentor_port.MentorService` (consumer-defined ABC with one method, `is_mentor(matricula) -> bool`). Per the cross-feature dependency rule, **the producer (mentores) provides the adapter**.

`mentores/adapters/intake_adapter.py` exposes `MentoresIntakeAdapter`, a thin class implementing the intake port by delegating `is_mentor` to `mentores.services.mentor_service.MentorService.is_mentor`. `mentores/dependencies.py.get_intake_mentor_adapter()` wires it; `solicitudes/intake/dependencies.py` calls **only** that factory — intake's runtime code (services, views, forms, schemas) imports zero from `mentores.*`.

This shape lets each feature evolve its interface independently:
- Mentores can grow `MentorService` (new methods like `get_history`, `was_mentor_at` in 012) without affecting intake.
- Intake can change its port shape only by editing `mentor_port.py`; mentores updates the adapter to match.

`pago_exento` snapshot integrity (OQ-008-2): the boolean is stamped onto `Solicitud` at creation time using whatever `is_mentor` returns then. The catalog can later deactivate the mentor without affecting prior solicitudes — the snapshot lives on the row, not on the catalog.

## Tests

| Layer | File | Pattern |
|---|---|---|
| Repository | `tests/test_mentor_repository.py` | Real DB (`pytest.mark.django_db`); `model_bakery` factories with UUID-derived defaults; asserts on returned DTOs. |
| Service | `tests/test_mentor_service.py` | `InMemoryMentorRepository` fake (in `tests/fakes.py`); no DB. |
| CSV importer | `tests/test_csv_importer.py` | Fake repo + module-level `pytestmark = pytest.mark.django_db` (importer's `transaction.atomic()` needs a real DB connection). |
| Views | `tests/test_views.py` | JWT-cookie `Client` pattern; permission boundaries (anonymous → 302 redirect to login, wrong role → 403). |
| Cross-feature | `tests/test_intake_wiring.py` | End-to-end through real adapter + ORM repo + intake views. Covers Tier 1 E2E + smoke. |
| Browser | `tests-e2e/test_mentores_golden_path.py` | Tier 2 Playwright; admin imports CSV; admin deactivates from list. Screenshots at 1280×900 and 320×800. |

Coverage targets met: services 100%, repository 100%, views 84-97%, total 98%.

## Known limitations (deferred to 012)

- The catalog stores **current state only**: reactivation overwrites `fecha_alta` and clears `fecha_baja`, losing the prior period. There is no answer to "was matrícula M a mentor on 2024-04-15?".
- Deactivation does not record **who deactivated** (only `creado_por` is captured for the current period).
- No detail view yet at `/mentores/<matricula>/` — list view links to it but the page itself is added by 012.

These are addressed by initiative **012 — Mentor Catalog Historicization**, which replaces `Mentor` with a per-period `MentorPeriodo` model.

## Related Specs

- [`specs/apps/mentores/historicization/requirements.md`](../historicization/requirements.md) — initiative 012; full per-period historicization.
- [`specs/planning/008-mentors/plan.md`](../../../planning/008-mentors/plan.md) — implementation blueprint.
- [`specs/planning/008-mentors/changelog.md`](../../../planning/008-mentors/changelog.md) — implementation log.
- [`specs/global/requirements.md`](../../../global/requirements.md) — RF-11.
- [`specs/flows/solicitud-lifecycle.md`](../../../flows/solicitud-lifecycle.md) — the cross-app flow that consumes `is_mentor`.
- [`.claude/rules/django-code-architect.md`](../../../../.claude/rules/django-code-architect.md) — architectural rules this design adheres to.
