# 012 — Mentor Catalog Historicization

## Summary

Replace the single-row-per-matrícula `Mentor` model with a **per-period model** (`MentorPeriodo`), so the mentor catalog records every `(alta, baja)` range as a distinct row. Reactivation opens a new period instead of overwriting; the catalog can answer point-in-time membership queries and produce per-matrícula timelines. Downstream contracts (`is_mentor`, `pago_exento` snapshot, CSV importer outcomes) keep their external semantics.

## Depends on

- **008 — Mentors** — must land on `main` before this initiative starts. 012 rewrites the same module.

## Affected Apps / Modules

- `mentores/models/` — drop `Mentor`, add `MentorPeriodo`.
- `mentores/repositories/mentor/{interface,implementation}.py` — rewrite around the period model; new methods `get_history`, `was_mentor_at`. Rename `upsert` → `add_or_reactivate`.
- `mentores/services/mentor_service/{interface,implementation}.py` — add `get_history`, `was_mentor_at`. `is_mentor`, `add`, `deactivate` keep their signatures and outcomes.
- `mentores/services/csv_importer/implementation.py` — unchanged externally; internal call switches to `add_or_reactivate`.
- `mentores/schemas.py` — `MentorPeriodoDTO` (replaces `MentorDTO`); `MentorUpsertInput` retained but ownership shifted (now describes "open a new period"); `CsvImportResult` unchanged.
- `mentores/views/list.py` — unchanged URL/template; internal switch to `list_active`.
- `mentores/views/detail.py` — **NEW**: timeline view at `/mentores/<matricula>/`.
- `mentores/views/deactivate.py` — captures `desactivado_por = actor`.
- `mentores/urls.py` — add `path("<str:matricula>/", DetailView.as_view(), name="detail")`.
- `mentores/migrations/000N_*.py` — three migrations (schema add, data backfill, drop old table).
- `templates/mentores/list.html` — link each row's matrícula to the new detail view.
- `templates/mentores/detail.html` — **NEW**.
- `templates/mentores/import_result.html` — unchanged.
- `templates/components/sidebar.html` — unchanged (still one entry pointing at list).
- `mentores/tests/*` — repository tests rewritten; new tests for history/point-in-time/partial-index; importer + service test fixtures updated for the new outcomes.
- `mentores/tests/test_intake_wiring.py` — re-run unmodified to verify cross-feature regression.

## References

- [`specs/apps/mentores/historicization/requirements.md`](../../apps/mentores/historicization/requirements.md) — WHAT/WHY for this initiative.
- [`specs/planning/008-mentors/plan.md`](../008-mentors/plan.md) — the catalog that 012 replaces; sets contract expectations (`is_mentor`, CSV import outcomes, snapshot integrity).
- [`specs/planning/004-solicitud-lifecycle/plan.md`](../004-solicitud-lifecycle/plan.md) — owns `pago_exento` snapshot. This initiative must preserve OQ-008-2 (snapshot at creation, never re-evaluated on read).
- [`specs/global/requirements.md`](../../global/requirements.md) — RF-11 (admin manages mentor catalog).
- [`.claude/rules/django-code-architect.md`](../../../.claude/rules/django-code-architect.md) — architectural law (read before implementing).

## Implementation Details

### Model — `mentores/models/mentor_periodo.py`

```python
class MentorPeriodo(Model):
    id = BigAutoField(primary_key=True)
    matricula = CharField(max_length=20, db_index=True)
    fuente = CharField(max_length=16, choices=MentorSource.choices())
    nota = CharField(max_length=200, blank=True)
    # NOTE: no `auto_now_add=True` — Django's pre_save fires unconditionally
    # on insert and would overwrite explicit values during bulk_create in the
    # data migration (silently destroying historical alta dates). The
    # repository stamps `fecha_alta = timezone.now()` explicitly in
    # `add_or_reactivate`; the data migration carries forward the original
    # `Mentor.fecha_alta` values verbatim.
    fecha_alta = DateTimeField()
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
        indexes = [
            Index(fields=["matricula", "fecha_baja"]),
        ]
        ordering = ["-fecha_alta"]
```

**Postgres-only assumption:** the partial unique index (`UniqueConstraint(condition=Q(...))`) and the `DISTINCT ON` query used by `list(only_active=False)` are Postgres-specific. The project's dev compose stack and `config.settings.test_postgres` both target Postgres; the SQLite fallback in `config.settings.dev` (when `DB_HOST` is unset) is only safe for `manage.py check`-style smoke runs and **will not run mentores migrations correctly**. Status task: confirm this is documented in the dev README/CLAUDE.md if it isn't already.

The `(matricula, fecha_baja)` index serves the hot path (`exists_active`).

`Mentor` is removed. The existing `mentores.models.__init__` re-exports `MentorPeriodo` instead.

### DTOs — `mentores/schemas.py`

```python
class MentorPeriodoDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    matricula: str
    fuente: MentorSource
    nota: str
    fecha_alta: datetime
    fecha_baja: datetime | None
    creado_por_matricula: str
    desactivado_por_matricula: str | None

class MentorUpsertInput(BaseModel):
    """Input to ``MentorRepository.add_or_reactivate``."""
    matricula: str = Field(min_length=1, max_length=20)
    fuente: MentorSource
    nota: str = Field(default="", max_length=200)
    creado_por_matricula: str = Field(min_length=1, max_length=20)

# CsvImportResult retained as-is from 008.
```

`MentorDTO` is removed. Templates that read `dto.matricula`, `dto.activo`, `dto.fuente`, `dto.nota`, `dto.fecha_alta`, `dto.fecha_baja` continue to read those names from `MentorPeriodoDTO`; `activo` is replaced by an explicit predicate `dto.fecha_baja is None` (rendered as a status badge in the template).

### Repository — `mentores/repositories/mentor/`

```python
class MentorRepository(ABC):
    @abstractmethod
    def exists_active(self, matricula: str) -> bool: ...
    @abstractmethod
    def get_active_period(self, matricula: str) -> MentorPeriodoDTO: ...
    @abstractmethod
    def list(self, *, only_active: bool, page: PageRequest) -> Page[MentorPeriodoDTO]: ...
    @abstractmethod
    def get_history(self, matricula: str) -> list[MentorPeriodoDTO]: ...
    @abstractmethod
    def was_mentor_at(self, matricula: str, when: datetime) -> bool: ...
    @abstractmethod
    def add_or_reactivate(
        self, input_dto: MentorUpsertInput
    ) -> tuple[MentorPeriodoDTO, UpsertOutcome]: ...
    @abstractmethod
    def deactivate(self, matricula: str, *, actor_matricula: str) -> MentorPeriodoDTO: ...
```

`UpsertOutcome` semantics (unchanged enum values, slightly refined behavior):

| Outcome | When |
|---|---|
| `INSERTED` | First period for this matrícula. |
| `REACTIVATED` | Prior periods exist; all are closed. New period inserted. |
| `ALREADY_ACTIVE` | An active period exists. No write. |

`add_or_reactivate` is the only write path. Implementation pseudocode:

```python
def add_or_reactivate(input_dto):
    # Two reads + one write. The `exists active?` check covers the common
    # case; the partial unique index is the safety net under concurrent
    # admin actions. Without IntegrityError recovery, a TOCTOU race between
    # two reactivation requests would surface as a 500.
    with transaction.atomic():
        active = MentorPeriodo.objects.filter(
            matricula=input_dto.matricula, fecha_baja__isnull=True,
        ).first()
        if active is not None:
            return _to_dto(active), UpsertOutcome.ALREADY_ACTIVE
        had_history = MentorPeriodo.objects.filter(
            matricula=input_dto.matricula,
        ).exists()
        try:
            new_period = MentorPeriodo.objects.create(
                matricula=input_dto.matricula,
                fuente=input_dto.fuente.value,
                nota=input_dto.nota,
                fecha_alta=timezone.now(),
                creado_por_id=input_dto.creado_por_matricula,
            )
        except IntegrityError:
            # Concurrent reactivator won the race against the partial unique
            # index. Re-read the active row and treat it as ALREADY_ACTIVE.
            active = MentorPeriodo.objects.get(
                matricula=input_dto.matricula, fecha_baja__isnull=True,
            )
            return _to_dto(active), UpsertOutcome.ALREADY_ACTIVE
        return (
            _to_dto(new_period),
            UpsertOutcome.REACTIVATED if had_history else UpsertOutcome.INSERTED,
        )
```

`deactivate` updates only the active period:

```python
def deactivate(matricula, *, actor_matricula):
    with transaction.atomic():
        try:
            period = (MentorPeriodo.objects
                      .select_for_update()
                      .get(matricula=matricula, fecha_baja__isnull=True))
        except MentorPeriodo.DoesNotExist as exc:
            raise MentorNotFound(...) from exc
        period.fecha_baja = timezone.now()
        period.desactivado_por_id = actor_matricula
        period.save(update_fields=["fecha_baja", "desactivado_por"])
        return _to_dto(period)
```

`was_mentor_at` is a single indexed read. **Boundary semantics: half-open interval `[fecha_alta, fecha_baja)`** — `fecha_alta` is inclusive, `fecha_baja` is exclusive. So for a period `[2024-01-01 09:00 → 2024-06-01 09:00]`:
- `was_mentor_at(M, 2024-01-01 09:00) == True` (inclusive on alta)
- `was_mentor_at(M, 2024-06-01 08:59:59) == True`
- `was_mentor_at(M, 2024-06-01 09:00) == False` (exclusive on baja)

```python
def was_mentor_at(matricula, when):
    return MentorPeriodo.objects.filter(
        matricula=matricula,
        fecha_alta__lte=when,
    ).filter(
        Q(fecha_baja__isnull=True) | Q(fecha_baja__gt=when),
    ).exists()
```

### Service — `mentores/services/mentor_service/`

```python
class MentorService(ABC):
    @abstractmethod
    def is_mentor(self, matricula: str) -> bool: ...
    @abstractmethod
    def list(self, *, only_active: bool, page: PageRequest) -> Page[MentorPeriodoDTO]: ...
    @abstractmethod
    def add(self, *, matricula, fuente, nota, actor) -> MentorPeriodoDTO: ...
    @abstractmethod
    def deactivate(self, matricula: str, actor: UserDTO) -> MentorPeriodoDTO: ...
    @abstractmethod
    def get_history(self, matricula: str) -> list[MentorPeriodoDTO]: ...
    @abstractmethod
    def was_mentor_at(self, matricula: str, when: datetime) -> bool: ...
```

- `add` keeps the `MentorAlreadyActive` exception on `ALREADY_ACTIVE`.
- `list` is a pure passthrough to `repo.list(only_active, page)`. The repo's `list` returns:
  - `only_active=True` → rows where `fecha_baja IS NULL`, ordered by `matricula`. One row per currently-active mentor.
  - `only_active=False` → one row per matrícula (the most recent period via Postgres `DISTINCT ON("matricula") ORDER BY matricula, fecha_alta DESC`). Admins see one row per person regardless of how many periods they have; the row's `fecha_baja` tells whether they're currently active.
- `is_mentor` and `was_mentor_at` are pure passthroughs to the repo.

### Migrations — `mentores/migrations/`

Three sequential migrations:

1. **`0002_mentor_periodo.py`** — schema migration: create `MentorPeriodo` table with all columns, partial unique index, regular index. `Mentor` is left in place.
2. **`0003_backfill_mentor_periodos.py`** — data migration:
   ```python
   def forwards(apps, schema_editor):
       Mentor = apps.get_model("mentores", "Mentor")
       MentorPeriodo = apps.get_model("mentores", "MentorPeriodo")
       to_create = []
       for m in Mentor.objects.all():
           to_create.append(MentorPeriodo(
               matricula=m.matricula,
               fuente=m.fuente,
               nota=m.nota,
               fecha_alta=m.fecha_alta,
               fecha_baja=m.fecha_baja,  # may be None (active) or set (inactive)
               creado_por_id=m.creado_por_id,
               desactivado_por_id=None,
           ))
       MentorPeriodo.objects.bulk_create(to_create)
   ```
   `reverse` is `noop` (data restoration would lose the post-cutover periods).
3. **`0004_drop_mentor.py`** — schema migration: drop the `Mentor` model. **Forward-only.** The reverse path re-creates an empty `Mentor` table for migration-graph completeness, but the row data is gone — rolling all the way back past `0002` destroys history. The migration's docstring must declare this explicitly so a future operator running `manage.py migrate mentores 0001` is not surprised. Use the same forward-only discipline that 003+ has elsewhere in the codebase.

Because `MentorPeriodo.fecha_alta` does **not** have `auto_now_add=True` (see Model section above), the `bulk_create` in `0003` can pass `fecha_alta=m.fecha_alta` directly and Django will not overwrite it on insert. This is the deliberate fix for the "auto_now_add silently overwrites the migration value" footgun.

### Views

- **`mentores/views/list.py`** — `MentorListView` returns `Page[MentorPeriodoDTO]` instead of `Page[MentorDTO]`. Existing `filtered=1` sentinel pattern preserved. The list shows one row per currently-active period when `only_active=True`, and one row per matrícula (latest period) when `only_active=False`.
- **`mentores/views/detail.py`** — **NEW**:
  ```python
  class MentorDetailView(AdminRequiredMixin, View):
      template_name = "mentores/detail.html"

      def get(self, request, matricula):
          history = get_mentor_service().get_history(matricula)
          if not history:
              raise MentorNotFound(f"matricula={matricula}")
          return render(request, self.template_name,
                        {"matricula": matricula, "history": history})
  ```
- **`mentores/views/deactivate.py`** — service.deactivate now passes `actor` through; the actor's matrícula is what the repo records as `desactivado_por`.
- **`mentores/views/add.py`** and **`mentores/views/import_csv.py`** — no changes (their service calls keep the same signatures and outcomes).

### Templates

- **`templates/mentores/list.html`** — link the matrícula cell to `mentores:detail`. Replace `dto.activo` reads with `dto.fecha_baja is None`. Keep all other markup, accessibility, mobile reflow rules.
- **`templates/mentores/detail.html`** — **NEW**. Layout:
  - `<h1 class="h3">Historial del mentor {{ matricula }}</h1>`
  - Status pill at top: "Actualmente activo" (green badge) if any period has `fecha_baja IS NULL`, otherwise "Inactivo" (secondary).
  - Timeline list: `<ol>` of `<li>` rows, each with `fecha_alta` → `fecha_baja or "Activo"`, fuente badge, nota, "Iniciado por", "Desactivado por" (if applicable). Newest-first.
  - "Volver al catálogo" link back to `mentores:list`.
- All other templates: unchanged.

### Cross-feature impact (intake)

**Behavior preserved; some test setup helpers must be updated.** `MentoresIntakeAdapter` keeps calling `MentorService.is_mentor(matricula)`. The repo's hot path is rewritten but the externally-visible boolean is identical: "is there any active period for this matrícula?".

The 008 cross-feature regression suite at `mentores/tests/test_intake_wiring.py` currently imports `from mentores.models import Mentor` and uses `Mentor.objects.create(...)` / `Mentor.objects.filter(pk=...).update(activo=False)` / `Mentor.objects.filter(creado_por=...).count()` for setup and assertions. After 012's migration `0004` drops `Mentor`, those references break at import time. The test must be updated:
- `_seed_mentor` helper switches to `MentorPeriodo.objects.create(...)`.
- `Mentor.objects.filter(pk="ALU1").update(activo=False)` becomes
  `MentorPeriodo.objects.filter(matricula="ALU1", fecha_baja__isnull=True).update(fecha_baja=timezone.now())`.
- `Mentor.objects.filter(creado_por=admin_user).count() == 80` becomes
  `MentorPeriodo.objects.filter(creado_por=admin_user, fecha_baja__isnull=True).count() == 80`.

The **behavioral** assertions (`pago_exento==True`, `comprobante` required when not a mentor, snapshot integrity across deactivation) stay identical. Same applies to `mentores/tests/test_csv_importer.py` and any other test that touches `Mentor` directly.

`pago_exento` snapshot integrity is preserved because the snapshot lives on `Solicitud`, not on the catalog. Deactivating a mentor closes the period without touching any solicitud row.

### Sequencing

1. 008 lands on `main`.
2. Add `MentorPeriodo` model + migration `0002`.
3. Data backfill migration `0003`.
4. Drop `Mentor` migration `0004`.
5. Repository rewrite + tests.
6. Service updates + tests (existing test_mentor_service.py extended; new test_history.py for `get_history` / `was_mentor_at`).
7. CSV importer test fixture updates (no code changes — confirm outcomes still produce the expected counts).
8. Detail view + template + tests.
9. List view + template touch-ups.
10. Run full pytest including `mentores/tests/test_intake_wiring.py` and `tests-e2e/test_mentores_golden_path.py` to verify no regression.
11. Quality gates (`ruff`, `mypy`, full pytest).

## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)

- **Reactivation creates a new period (not overwrite)**: admin adds matrícula M (period 1) → admin deactivates M (period 1 closed) → admin re-adds M via manual form (period 2 opened). `MentorPeriodo.objects.filter(matricula=M).count() == 2`. Both periods visible in `service.get_history(M)`, ordered newest-first.
- **CSV reactivation creates a new period**: same flow but reactivation comes through the CSV import path. Result counts (`reactivated == 1`) unchanged from 008's contract.
- **Cross-feature snapshot integrity (regression carry-forward from 008)**: `mentores/tests/test_intake_wiring.py::test_mentor_deactivation_preserves_existing_solicitud_snapshot` passes after its setup helpers are updated to `MentorPeriodo`. Behavioral assertions (`pago_exento` stays `True` for prior solicitudes, comprobante required for new ones) unchanged.
- **Point-in-time membership boundaries**: matrícula M with period `[2024-01-01 09:00 → 2024-06-01 09:00]`. `was_mentor_at(M, 2024-01-01 09:00) == True` (inclusive alta); `was_mentor_at(M, 2024-06-01 08:59:59) == True`; `was_mentor_at(M, 2024-06-01 09:00) == False` (exclusive baja). With a second period `[2024-09-01 → null]`, `was_mentor_at(M, 2024-08-15) == False` and `was_mentor_at(M, 2024-12-15) == True`.
- **Partial unique index enforcement**: attempting to insert two open periods for the same matrícula via the ORM raises `IntegrityError` (test pinned to confirm DB-level safety, not just service-level checks).
- **Concurrent reactivation race**: simulate two simultaneous reactivation requests for the same inactive matrícula; the partial unique index makes one fail with `IntegrityError`; the service's recovery branch returns `(dto, ALREADY_ACTIVE)` instead of surfacing a 500. (May be exercised at the service-test level by mocking the repo's `create` to raise `IntegrityError` once and confirming the recovery path runs.)

### Browser (Tier 2 — `pytest-playwright`)

- **Admin views a mentor's history**: seed two periods for matrícula M; admin navigates to `/mentores/M/`; sees the timeline with two entries, status pill says "Inactivo" if the latest period is closed and "Actualmente activo" if open. Screenshots at 1280×900 desktop and 320×800 mobile to `/tmp/screenshots-012/`.
- **Admin reactivates a deactivated mentor and the history reflects it**: seed one closed period for M; admin imports a CSV containing M; admin opens `/mentores/M/`; sees two timeline entries, status "Actualmente activo".

## Acceptance Criteria

- [ ] `MentorPeriodo` model exists; `Mentor` model is removed after migration.
- [ ] Partial unique index `unique_active_period_per_matricula` is enforced at the DB level (verified by an `IntegrityError`-asserting test).
- [ ] Data migration `0003` faithfully copies all pre-existing `Mentor` rows into `MentorPeriodo` (one period per row), preserving `fecha_alta`, `fecha_baja`, `fuente`, `nota`, `creado_por`. Verified against an empty DB and a populated DB (test fixture).
- [ ] Repository contract: 7 methods (`exists_active`, `get_active_period`, `list(only_active, page)`, `get_history`, `was_mentor_at`, `add_or_reactivate`, `deactivate`). All covered by `test_mentor_repository.py`. Coverage ≥ 95%.
- [ ] Service contract: `is_mentor`, `list`, `add`, `deactivate`, `get_history`, `was_mentor_at`. Outcomes for `add` (`INSERTED`/`REACTIVATED`/`ALREADY_ACTIVE`) match 008's external semantics. Coverage ≥ 95%.
- [ ] CSV importer: outcomes (`inserted`, `reactivated`, `skipped_duplicates`, `invalid_rows`) keep the same external semantics. Existing `test_csv_importer.py` 100-row test passes unmodified except for repository fixture updates.
- [ ] Detail view at `/mentores/<matricula>/` renders the timeline (read-only). 404 (mapped from `MentorNotFound`) for unknown matrículas. Admin-only.
- [ ] List view: behavior unchanged for end-users. Each matrícula in the list links to its detail page. Mobile reflow at 320px preserved.
- [ ] Cross-feature regression: `mentores/tests/test_intake_wiring.py` setup helpers updated to `MentorPeriodo`; **behavioral assertions stay identical**; suite stays green; `Solicitud.pago_exento` snapshot pattern is unaffected.
- [ ] Tier 2 e2e (`tests-e2e/test_mentores_golden_path.py`) re-runs without modification AND a new file `tests-e2e/test_mentor_history_browser.py` exercises the two new flows.
- [ ] Quality gates: `ruff`, `mypy`, full `pytest` all green at the end.

## Open Questions

- **OQ-012-1** — `desactivado_por` for legacy rows (migrated from `Mentor`): we set `NULL` because the prior schema did not capture the deactivator. Acceptable as long as the audit story is "from migration date forward". If the institution requires retroactive attribution, that's not solvable without external data and is out of scope.
- **OQ-012-2** — When an admin edits the `nota` of a currently-active period (no UI today, but easy to add later), do we **mutate the period** or **close it and open a new one**? Plan: mutate. Notes are metadata; period boundaries should only move on `activo` flips. A future "audit log" initiative could capture nota edits separately.
- **OQ-012-3** — `list(only_active=False)` returns one summary per matrícula (latest period), not all periods. If a future report wants "all periods, all matrículas, paged", that's a new repo method (`list_all_periods`) — adding it later is non-breaking.
