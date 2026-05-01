# mentores · historicization — Design

> Canonical reference for the per-period mentor catalog shipped in initiative **012 — Mentor Catalog Historicization**. Supersedes the single-row-per-matrícula model documented in `specs/apps/mentores/catalog/design.md` (the catalog's `Mentor` table was dropped by migration `0004_drop_mentor`). Future initiatives that touch this surface should update this file rather than redefining the contract elsewhere.

## Purpose

Maintain the institution's mentor catalog with **full history**: every `(alta, baja)` range a matrícula has held is preserved as its own row, so the catalog can answer point-in-time membership questions and produce per-mentor timelines. Reactivation opens a new period rather than overwriting the old one. Bulk admin actions (multi-select deactivation) operate atomically at the DB level.

## Data model

### `MentorPeriodo` — `mentores/models/mentor_periodo.py`

```python
class MentorPeriodo(Model):
    id = BigAutoField(primary_key=True)
    matricula = CharField(max_length=20, db_index=True)
    fuente = CharField(max_length=16, choices=MentorSource.choices())
    nota = CharField(max_length=200, blank=True)
    fecha_alta = DateTimeField()              # NO auto_now_add — see note
    fecha_baja = DateTimeField(null=True, blank=True)
    creado_por = ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="+")
    desactivado_por = ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT,
                                 null=True, blank=True, related_name="+")

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["matricula"],
                condition=Q(fecha_baja__isnull=True),
                name="unique_active_period_per_matricula",
            ),
        ]
        indexes = [Index(fields=["matricula", "fecha_baja"])]
        ordering = ["-fecha_alta"]
```

- One row per `(alta, baja)` period. `fecha_baja IS NULL` denotes the currently-open period.
- Surrogate `BigAutoField` PK (matrícula is no longer unique — many periods per matrícula are expected).
- **No `auto_now_add` on `fecha_alta`.** Django's `pre_save` for `auto_now_add` fires unconditionally on insert (including via `bulk_create`), which would silently overwrite explicit values during the data migration that backfills history. The repository stamps `fecha_alta = timezone.now()` explicitly in `add_or_reactivate`; the data migration carries forward original `Mentor.fecha_alta` values verbatim.
- **Postgres-only.** The partial unique index (`UniqueConstraint(condition=Q(...))`) and the `DISTINCT ON` query used by `list(only_active=False)` are Postgres-specific. Dev/test stacks both target Postgres; SQLite is not supported for migrations.
- `desactivado_por` is set by `deactivate` / `deactivate_many` / `deactivate_all_active`. Legacy rows backfilled by `0003_backfill_mentor_periodos` carry `NULL` because the prior schema did not capture the deactivator (acceptable: audit story is "from migration date forward").

The matrícula format is enforced via `mentores.validators.is_valid_matricula` (default regex `^\d{8}$`, configurable via `MENTOR_MATRICULA_REGEX`). Both the form layer and the service layer call this validator; the service is authoritative because the CSV importer bypasses Django forms.

## DTOs — `mentores/schemas.py`

| DTO | Direction | Purpose |
|---|---|---|
| `MentorPeriodoDTO` (frozen) | repo/service → view/template | Output shape per period: `id`, `matricula`, `fuente`, `nota`, `fecha_alta`, `fecha_baja`, `creado_por_matricula`, `desactivado_por_matricula`. |
| `MentorUpsertInput` | view/service → repo | Insert / reactivate boundary. Carries the fields needed to open a new period; the repo stamps `fecha_alta = timezone.now()` itself. |
| `CsvImportResult` (frozen) | service → view | Counts (`total_rows`, `inserted`, `reactivated`, `skipped_duplicates`, `invalid_rows: list[dict]`). External semantics unchanged from 008. |
| `BulkDeactivateResult` (frozen) | service → view | Counts (`total_attempted`, `closed`, `already_inactive`). `total_attempted` reflects **unique** matrículas (service de-duplicates the input). `already_inactive` lumps "closed before this call" with "unknown to the catalog" — the catalog cannot distinguish them post-hoc. |

`MentorDTO` is removed. Templates that read `dto.matricula`, `dto.fuente`, `dto.nota`, `dto.fecha_alta`, `dto.fecha_baja` continue to read those names from `MentorPeriodoDTO`; the legacy `dto.activo` boolean is replaced by the explicit predicate `dto.fecha_baja is None`.

## Exceptions — `mentores/exceptions.py`

Unchanged from 008:

| Exception | Subclass of `_shared.exceptions.…` | HTTP | Spanish `user_message` |
|---|---|---|---|
| `MentorNotFound` | `NotFound` | 404 | "El mentor no existe." |
| `MentorAlreadyActive` | `Conflict` | 409 | "El alumno ya está registrado como mentor activo." |
| `CsvParseError` | `DomainValidationError` | 422 | "El archivo CSV tiene un formato inválido." |

`MentorPeriodo.DoesNotExist` is mapped to `MentorNotFound` inside the repository; Django ORM exceptions never escape that layer.

## Repository — `mentores/repositories/mentor/`

`MentorRepository` ABC + `OrmMentorRepository`. Seven methods:

```python
class MentorRepository(ABC):
    # Hot path consumed by intake — returns bool, no DTO marshalling.
    def exists_active(self, matricula: str) -> bool: ...

    def get_active_period(self, matricula: str) -> MentorPeriodoDTO: ...   # raises MentorNotFound
    def get_history(self, matricula: str) -> Sequence[MentorPeriodoDTO]: ...  # newest-first; empty list for unknown
    def was_mentor_at(self, matricula: str, when: datetime) -> bool: ...   # half-open [alta, baja)

    def list(self, *, only_active: bool, page: PageRequest) -> Page[MentorPeriodoDTO]: ...

    def add_or_reactivate(self, input_dto: MentorUpsertInput) -> tuple[MentorPeriodoDTO, UpsertOutcome]: ...
    def deactivate(self, matricula: str, *, actor_matricula: str) -> MentorPeriodoDTO: ...

    # Bulk variants — single Postgres UPDATE each, return count of rows closed.
    def deactivate_many(self, matriculas: Sequence[str], *, actor_matricula: str) -> int: ...
    def deactivate_all_active(self, *, actor_matricula: str) -> int: ...
```

### Key behaviors

- **`list(only_active=True)`** → `MentorPeriodo.objects.filter(fecha_baja__isnull=True).order_by("matricula")`. One row per currently-active mentor.
- **`list(only_active=False)`** → Postgres `DISTINCT ON("matricula")` ordered by `(matricula, -fecha_alta)`. One row per matrícula (the most recent period). Admins see one summary entry per person regardless of how many historical periods they have.
- **`was_mentor_at(matricula, when)`** uses the half-open interval `[fecha_alta, fecha_baja)`: `fecha_alta` inclusive, `fecha_baja` exclusive. Open periods (`fecha_baja IS NULL`) extend to infinity.
- **`add_or_reactivate`** is the only single-row write path. Outcomes:
  | Outcome | When |
  |---|---|
  | `INSERTED` | First period for this matrícula. |
  | `REACTIVATED` | Prior periods exist; all are closed; new period inserted. |
  | `ALREADY_ACTIVE` | An open period exists; nothing changed. |

  The implementation wraps the read+write in `transaction.atomic()` and **recovers from `IntegrityError`**: under concurrent reactivation, the partial unique index rejects the second insert; the recovery branch re-reads the active row and returns `ALREADY_ACTIVE` rather than surfacing a 500.
- **`deactivate`** uses `select_for_update` on the open period; raises `MentorNotFound` if no open period exists.
- **`deactivate_many` / `deactivate_all_active`** are single bulk `UPDATE`s filtered by `fecha_baja IS NULL`. No `transaction.atomic()` wrap is needed — Postgres handles the row-set update atomically and the partial unique index cannot fire on open→closed transitions. Best-effort: matrículas without an open period are skipped silently. Empty input on `deactivate_many` short-circuits to `0` with no DB round trip.

## Service — `mentores/services/mentor_service/`

`MentorService` ABC + `DefaultMentorService`. Eight methods:

```python
class MentorService(ABC):
    def is_mentor(self, matricula: str) -> bool: ...
    def list(self, *, only_active: bool, page: PageRequest) -> Page[MentorPeriodoDTO]: ...
    def add(self, *, matricula, fuente, nota, actor) -> MentorPeriodoDTO: ...
    def deactivate(self, matricula: str, actor: UserDTO) -> MentorPeriodoDTO: ...
    def get_history(self, matricula: str) -> Sequence[MentorPeriodoDTO]: ...
    def was_mentor_at(self, matricula: str, when: datetime) -> bool: ...
    def bulk_deactivate(self, matriculas: Sequence[str], actor: UserDTO) -> BulkDeactivateResult: ...
    def deactivate_all_active(self, actor: UserDTO) -> BulkDeactivateResult: ...
```

- `add` keeps the `MentorAlreadyActive` exception on `ALREADY_ACTIVE` outcomes.
- `bulk_deactivate` **de-duplicates** input via `set(...)` before passing to the repo, so duplicates do not inflate `already_inactive`. `total_attempted` is the count of unique matrículas. `already_inactive = total_attempted - closed`.
- `deactivate_all_active` returns `total_attempted == closed` and `already_inactive == 0` because the underlying query targets only open periods by definition.

`is_mentor` is a pure passthrough to `repo.exists_active`. Intake's `MentoresIntakeAdapter` keeps calling it and the boolean contract is identical to 008's.

## Migrations — `mentores/migrations/`

Three sequential, **forward-only** migrations:

1. **`0002_mentor_periodo`** — schema add. Both `Mentor` and `MentorPeriodo` coexist briefly.
2. **`0003_backfill_mentor_periodos`** — data migration via `bulk_create`. Each `Mentor` row produces one `MentorPeriodo` carrying `fecha_alta` (verbatim — no `auto_now_add` overwrite), `fecha_baja`, `fuente`, `nota`, `creado_por`. `desactivado_por` is `NULL` for legacy rows. Reverse path is a `noop` (cannot restore data lost after the cutover).
3. **`0004_drop_mentor`** — schema drop of `Mentor`. **Forward-only by intent.** The reverse path re-creates an empty table for migration-graph completeness only — rolling back past `0002` destroys history. Recovery path: restore from a backup taken before `0002` ran.

## Views — `mentores/views/`

| View | URL | Method | Notes |
|---|---|---|---|
| `MentorListView` | `/mentores/` | GET | Admin-only. Default `only_active=True`. `filtered=1` sentinel pattern preserved. Wraps the table in a POST form for bulk deactivation. |
| `MentorDetailView` | `/mentores/<matricula>/` | GET | Admin-only. Renders the per-period timeline read-only. Empty history → `MentorNotFound` (404). |
| `AddMentorView` | `/mentores/agregar/` | GET, POST | Admin-only. Manual add flow; raises `MentorAlreadyActive` (409) on duplicate. |
| `DeactivateMentorView` | `/mentores/<matricula>/desactivar/` | GET, POST | Admin-only. Single-row deactivate. Retained at the URL level; **no UI link to it today** (bulk flow superseded the per-row link). |
| `BulkDeactivateMentorsView` | `/mentores/desactivar-bulk/` | POST | Admin-only. Two-step server-side confirm. |
| `ImportCsvView` | `/mentores/importar/` | GET, POST | Admin-only. CSV upload + result summary. |

### `BulkDeactivateMentorsView` two-step flow

Single endpoint, POST-only.

1. **Step 1 — render confirm.** No `token` in POST → view validates `action ∈ {selected, all}`, dedupes + sorts the matrículas, mints a signed token via `django.core.signing.dumps({"action", "matriculas"}, salt="mentores.bulk_deactivate")`, and renders `confirm_bulk_deactivate.html`. **No DB writes.**
2. **Step 2 — apply.** `token` present in POST → view verifies via `signing.loads(token, salt=..., max_age=300)`. On `BadSignature` (tampered) or `SignatureExpired` (older than 5 minutes), redirect with an error flash; no DB writes. On success, dispatch `service.bulk_deactivate(...)` (selected) or `service.deactivate_all_active(...)` (all), set a Django messages summary, redirect to the list.

Why a signed token instead of `confirmed=1`: a same-origin script could otherwise POST `confirmed=1&action=all` directly and bypass the confirmation page (CSRF only stops cross-site abuse). The signed token carries action + matriculas, so a tampered second POST cannot expand the target set after step 1 rendered.

`ACTION_ALL` is reachable today only via direct POST — the list-page UI only emits `action=selected`. The branch is retained for a possible future "advanced admin" panel and is fully tested.

## Templates — `app/templates/mentores/`

| Template | Notes |
|---|---|
| `list.html` | Wraps the table in a single POST form (`#bulk-deactivate-form`). Per-row checkbox on currently-open periods; toolbar above the table with **"Seleccionar todos"** (master toggle, `type="button"`, small inline IIFE script — the page's only JS) + single **"Desactivar"** submit (`btn-outline-danger`, posts `action=selected`). The `Acciones` column is removed. The matrícula cell links to the detail view. Mobile reflow at 320px shows only `Matrícula` + `Estado`. |
| `detail.html` | NEW. Breadcrumb + status pill ("Actualmente activo" / "Inactivo") + chronological timeline (`<ol class="list-group">`) of every period with attribution ("Iniciado por" / "Desactivado por"). |
| `confirm_bulk_deactivate.html` | NEW. Carries one signed `token` hidden field (no per-matrícula inputs to tamper with). Different copy for `action=all` (stronger warning) vs `action=selected` (lists targets). Confirm button `btn-danger`; Cancel `btn-outline-secondary`. |
| `confirm_deactivate.html` | Unchanged from 008. Reachable only via direct URL today. |
| `add.html`, `import_csv.html`, `import_result.html` | Unchanged from 008. |

## URL routing — `mentores/urls.py`

```python
urlpatterns = [
    path("", MentorListView.as_view(), name="list"),
    path("agregar/", AddMentorView.as_view(), name="add"),
    path("importar/", ImportCsvView.as_view(), name="import_csv"),
    path("desactivar-bulk/", BulkDeactivateMentorsView.as_view(), name="deactivate_bulk"),
    path("<str:matricula>/desactivar/", DeactivateMentorView.as_view(), name="deactivate"),
    path("<str:matricula>/", MentorDetailView.as_view(), name="detail"),
]
```

The literal route `desactivar-bulk/` is registered **before** the `<str:matricula>/` catch-all, so it cannot be shadowed. The matrícula validator regex (`^\d{6,10}$` by default) makes a real collision with literal segment names impossible today.

## Cross-feature contract preserved

- `MentoresIntakeAdapter` (in `mentores/adapters/intake_adapter.py`) keeps calling `MentorService.is_mentor(matricula)`. The boolean contract is identical to 008.
- `Solicitud.pago_exento` snapshot integrity is preserved: the boolean is stamped at intake creation and never re-evaluated on read. Deactivating a mentor closes the period without touching any `Solicitud` row.
- The 008 cross-feature regression suite (`mentores/tests/test_intake_wiring.py`) re-runs green after its setup helpers were updated to `MentorPeriodo`. Behavioral assertions are byte-identical.

## Related Specs

- [`requirements.md`](requirements.md) — WHAT + WHY for this feature.
- [`specs/apps/mentores/catalog/design.md`](../catalog/design.md) — the legacy single-row catalog this feature supersedes (kept for historical reference and 008 context).
- [`specs/planning/008-mentors/plan.md`](../../../planning/008-mentors/plan.md) — the catalog this design replaces.
- [`specs/planning/012-mentor-historicization/plan.md`](../../../planning/012-mentor-historicization/plan.md) — implementation blueprint for this design.
- [`specs/planning/004-solicitud-lifecycle/plan.md`](../../../planning/004-solicitud-lifecycle/plan.md) — owner of the `pago_exento` snapshot contract this feature must not break.
