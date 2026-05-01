# lifecycle — Design

> Canonical reference for the solicitud lifecycle feature. Updated after initiative 004 closed.

## Scope

The lifecycle feature owns:

- The `Solicitud`, `HistorialEstado`, and `FolioCounter` ORM models (app-level, in `solicitudes/models/`).
- The state machine — what estados exist, what transitions are legal, who is allowed to invoke each transition.
- Folio allocation (`SOL-YYYY-NNNNN`).
- Read-side queries (detail, role-scoped lists).
- The append-only state-transition history.
- Two outbound ports the consumer owns: `NotificationService` (007 will adapt) and the audit log (`_shared/audit.py`).

## Layer wiring

```
intake / revision views
        │
        ▼
LifecycleService (services/lifecycle_service/interface.py)
        │
        ├── SolicitudRepository (repositories/solicitud/)
        ├── HistorialRepository (repositories/historial/)
        └── NotificationService (notification_port.py)  ← 007 plugs in here
        │
        ▼
              ORM (Solicitud, HistorialEstado, FolioCounter, TipoSolicitud)

FolioService → FolioRepository → ORM (FolioCounter)
```

`lifecycle/dependencies.py` wires `Orm*Repository → Default*Service` and binds `NoOpNotificationService` until 007 lands. Repositories are constructed once per service factory call; the historial repo is shared between `OrmSolicitudRepository` (so `get_by_folio` returns a hydrated detail) and `DefaultLifecycleService` (so `transition` writes new entries).

## Data shapes

### Models (`solicitudes/models/`)

- **`Solicitud`** — `folio` (CharField pk, ≤20, format `SOL-YYYY-NNNNN`), `tipo` (FK PROTECT), `solicitante` (FK PROTECT, related_name `solicitudes`), `estado` (CharField with `Estado.choices()`, default `CREADA`), `form_snapshot` (JSONField, frozen `FormSnapshot.model_dump(mode="json")`), `valores` (JSONField, dict[field_id_str, primitive]), `requiere_pago` (Bool), `pago_exento` (Bool, default False), `created_at` / `updated_at`. Indexes: `(solicitante, -created_at)`, `(estado, -created_at)`, `(tipo, estado)`. Default ordering: `-created_at`.
- **`HistorialEstado`** — `id` (BigAutoField), `solicitud` (FK CASCADE, related_name `historial`), `estado_anterior` (nullable, only for the initial CREADA insert), `estado_nuevo`, `actor` (FK PROTECT, `related_name="+"`), `actor_role` (CharField with `Role.choices()` — snapshotted alongside the actor so historical answers to "who finalized?" survive role changes), `observaciones` (text, blank ok), `created_at`. Default ordering `-created_at`. Index `(solicitud, -created_at)`.
- **`FolioCounter`** — `year` (PositiveInt pk), `last` (PositiveInt, default 0). One row per year; `select_for_update` serializes allocation.

`Solicitud.form_snapshot` is **frozen at create-time** and never mutated. `Solicitud.requiere_pago` and `Solicitud.pago_exento` are also captured at create-time (not derived at read-time) so audit/reporting answers are stable even if the tipo's flags or the mentor list change later.

### Constants (`lifecycle/constants.py`)

```python
class Estado(StrEnum):
    CREADA = "CREADA"
    EN_PROCESO = "EN_PROCESO"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"

ACTION_ATENDER = "atender"
ACTION_FINALIZAR = "finalizar"
ACTION_CANCELAR = "cancelar"

TRANSITIONS: dict[tuple[Estado, str], Estado] = {
    (Estado.CREADA,     ACTION_ATENDER):   Estado.EN_PROCESO,
    (Estado.EN_PROCESO, ACTION_FINALIZAR): Estado.FINALIZADA,
    (Estado.CREADA,     ACTION_CANCELAR):  Estado.CANCELADA,
    (Estado.EN_PROCESO, ACTION_CANCELAR):  Estado.CANCELADA,
}
TERMINAL = frozenset({Estado.FINALIZADA, Estado.CANCELADA})
```

`Estado.display_name` returns the user-facing Spanish label (`"Creada"`, `"En proceso"`, `"Finalizada"`, `"Cancelada"`); templates render this rather than `value|title`. The `_ESTADO_DISPLAY` map is the single source of truth.

### DTOs (`lifecycle/schemas.py`)

- **`SolicitudRow`** — frozen list-view DTO: `folio, tipo_id, tipo_nombre, solicitante_matricula, solicitante_nombre, estado, requiere_pago, created_at, updated_at`.
- **`SolicitudDetail`** — frozen hydrated DTO: `folio, tipo: TipoSolicitudRow, solicitante: UserDTO, estado, form_snapshot: FormSnapshot, valores: dict[str, Any], requiere_pago, pago_exento, created_at, updated_at, historial: list[HistorialEntry]`. `tipo.plantilla_id` is populated by `OrmSolicitudRepository._to_detail` from 006 onward so consumers (intake/revision detail templates, `PdfService`) can gate the "Generar PDF" affordance without a second tipo lookup.
- **`HistorialEntry`** — frozen: `id, estado_anterior, estado_nuevo, actor_matricula, actor_nombre, actor_role, observaciones, created_at`.
- **`SolicitudFilter`** — input DTO: `estado, tipo_id, folio_contains, solicitante_contains, created_from, created_to`.
- **`TransitionInput`** — service input: `folio, actor_matricula, observaciones (≤2000)`.

## State machine — authority + authorization

`LifecycleService.transition(action, input_dto, actor)` runs in this exact order:

1. `solicitud = repo.get_by_folio(folio)` → `SolicitudNotFound` if missing.
2. `_authorize(action, detail, actor)` — see rules below.
3. `estado_destino = TRANSITIONS[(detail.estado, action)]` → raises `InvalidStateTransition` on `KeyError`.
4. **Inside `transaction.atomic()`**: `repo.update_estado(folio, new_estado=estado_destino)` and `historial.append(...)`. `update_estado` uses `save(update_fields=["estado", "updated_at"])` so `auto_now` fires.
5. **Outside the atomic block**: `notification_service.notify_state_change(folio, estado_destino, observaciones)` then `audit.write("solicitud.estado_cambiado", ...)`. Notifications and audit are intentionally outside the transaction so a notify hiccup does not roll back a committed state change. The trade-off is "we may commit an estado without an audit line if audit blows up"; that's acceptable because audit is best-effort observability.
6. Return `repo.get_by_folio(folio)` — fresh detail with the new historial included.

### Authorization rules (`_authorize`)

Layered on top of the `TRANSITIONS` map:

- **Admin** (`Role.ADMIN`) — bypasses all role checks.
- **`atender`, `finalizar`** — actor must be in `tipo.responsible_role`.
- **`cancelar`** — three legal callers:
  - solicitante (owner) — only when estado is `CREADA`
  - personal in `tipo.responsible_role` — when estado is `CREADA` or `EN_PROCESO`
  - admin — any non-terminal estado
- **Unknown action** — raises `ValueError`. Branch is unreachable from views (URL pattern restricts to the three documented actions); this catches programming bugs from direct service callers.

The "shared queue" rule (any user with the responsible role sees the row in `list_assigned`; first-write-wins on contention) is honored by *not* having an `assigned_to` field on the model. Contention is acceptable per the requirements.

## Folio allocation

`OrmFolioRepository.allocate(year)`:

```python
with atomic():
    counter, _ = FolioCounter.objects.select_for_update().get_or_create(
        year=year, defaults={"last": 0}
    )
    counter.last += 1
    counter.save(update_fields=["last"])
    return counter.last
```

`DefaultFolioService.next_folio(year)` formats: `f"SOL-{year}-{n:05d}"`.

Throughput is bounded by row-level lock contention. For the project's load profile this is fine. If we ever need higher throughput, swap `OrmFolioRepository` for a Postgres-sequence-per-year strategy and map any `IntegrityError` to `FolioCollision` (currently a placeholder exception with no raise site).

## Outbound ports

### `NotificationService` (`lifecycle/notification_port.py`)

```python
class NotificationService(ABC):
    def notify_creation(self, *, folio: str, responsible_role: Role) -> None: ...
    def notify_state_change(self, *, folio: str, estado_destino: Estado,
                             observaciones: str = "") -> None: ...
```

Lifecycle owns this ABC per the cross-feature dependency rule (the consumer defines the interface). The concrete `DefaultNotificationService` lives in `notificaciones/` (initiative 007) and is wired by `lifecycle/dependencies.py:get_lifecycle_service()`. `NoOpNotificationService` remains in `notification_port.py` and is used by tests and by the read-only lifecycle described below.

`notify_creation` is fired by `IntakeService.create`; `notify_state_change` is fired by `LifecycleService.transition`. Both are called *after* the transaction commits.

#### Construction-cycle break

The lifecycle service depends on the notifier (to fire on transitions); the notifier depends on `LifecycleService.get_detail` (to load `SolicitudDetail` for templating). `lifecycle/dependencies.py` resolves the cycle at construction time without introducing a new narrow port:

1. Build the shared `historial` and `solicitudes` repositories.
2. Build a *read-only* `DefaultLifecycleService` wired with `NoOpNotificationService`. The notifier never calls `transition` on this instance.
3. Build `DefaultNotificationService` taking the read-only lifecycle, plus the recipient resolver and SMTP sender.
4. Build the *production* `DefaultLifecycleService` taking the same shared repos and the real notifier.

Both lifecycle instances share the same repository objects, so reads from the notifier and writes from the production service cannot diverge if a future change starts caching state on a repo.

### Audit log (`_shared/audit.py`)

`audit.write(event, **fields)` emits one INFO line on the `audit` logger with `extra=` carrying the structured fields. No DB persistence in v1 — JSON log stream is the queryable surface. Call sites in this feature: `solicitud.creada` (intake), `solicitud.estado_cambiado` (lifecycle).

## Repository contract

`SolicitudRepository`:

- `create(folio, tipo_id, solicitante_matricula, estado, form_snapshot, valores, requiere_pago, pago_exento) -> SolicitudDetail`
- `get_by_folio(folio) -> SolicitudDetail` — hydrates historial via the injected `HistorialRepository`. Raises `SolicitudNotFound` on miss.
- `list_for_solicitante(matricula, page, filters) -> Page[SolicitudRow]`
- `list_for_responsible_role(responsible_role: str, page, filters) -> Page[SolicitudRow]` — used by personal queues; admin uses `list_all` instead.
- `list_all(page, filters) -> Page[SolicitudRow]`
- `update_estado(folio, new_estado)` — raises `SolicitudNotFound`.
- `exists_for_tipo(tipo_id) -> bool` — used by the tipos service to gate hard-delete.

**Aggregations (added in 009 for the `reportes` consumer):**

- `aggregate_by_estado(filters) -> list[AggregateByEstado]` — `{estado, count}` per estado.
- `aggregate_by_tipo(filters) -> list[AggregateByTipo]` — `{tipo_id, tipo_nombre, count}` per tipo, ordered by `-count, tipo_nombre`.
- `aggregate_by_month(filters) -> list[AggregateByMonth]` — `{year, month, count}` grouped by `TruncMonth("created_at")` in the project's `TIME_ZONE` (`America/Mexico_City`). Caller is responsible for the date window in `filters`; the repo does not synthesize a default.
- `iter_for_admin(filters, chunk_size=500) -> Iterator[SolicitudRow]` — server-side cursor (`.iterator(chunk_size=...)`) for exporters that need to walk every matching row without paying the per-page `count()` round trip baked into the paginated path.

Each `aggregate_by_*` is **single SQL** (`.values(...).annotate(Count("folio"))`). Asserted per-method by `django_assert_num_queries(1)` in `test_solicitud_repository_aggregates.py`. The full dashboard render through `DefaultReportService.dashboard()` is bounded by `django_assert_max_num_queries(12)` in the view test (3 aggregates + 1 filter-dropdown + ~8 auth/savepoint overhead) — this is the canonical N+1 regression catch.

`SolicitudFilter` carries an additive `responsible_role: Role | None` field (added in 009); when set, `_apply_filters` joins via `tipo__responsible_role=...` (the existing `(activo, responsible_role)` index covers the lookup, no schema change).

`SolicitudRow` carries an additive `pago_exento: bool = False` field (added in 009) so list-and-export consumers don't need to re-hydrate a `SolicitudDetail` per row.

List queries cap at **3 SQL queries** (one count, one rows, plus pagination overhead) via `select_related("tipo", "solicitante")`. Asserted by `test_list_uses_at_most_three_queries`.

`iter_for_admin` is **streaming on PostgreSQL** (server-side cursor) and **materialising on SQLite** (Django's iterator silently fetches all rows on SQLite); the call site documents this so dev exports of huge datasets don't surprise.

`HistorialRepository.append(...)` is append-only by contract; there is no update or delete method. `list_for_folio(folio)` returns entries ordered by `created_at` ascending (oldest first) so timelines render naturally.

## Exceptions (`lifecycle/exceptions.py`)

All inherit from `_shared.exceptions` so the global error middleware maps them to HTTP statuses:

- **`SolicitudNotFound`** (NotFound, 404) — folio does not exist.
- **`InvalidStateTransition`** (Conflict, 409) — the (estado, action) pair is not in `TRANSITIONS`. Message includes both estado and action for the user.
- **`FolioCollision`** (Conflict, 409) — reserved for a future allocator strategy. The current `select_for_update` design can't produce this; documented as a future surface, not raised today.

## Tests

- `test_folio_repository.py` — atomic allocation, per-year independence, monotonicity (real DB).
- `test_solicitud_repository.py` — create/read DTO assertions, all filter axes, pagination, query-count cap (`CaptureQueriesContext` ≤3).
- `test_historial_repository.py` — append, `list_for_folio` chronological order.
- `test_folio_service.py` — string formatting + zero-padding (in-memory fake).
- `test_lifecycle_service.py` — full transition matrix with in-memory fakes; `cancelar` authorization truth table; hypothesis property test that exhaustively walks `(Estado, action)` pairs and asserts the matrix is consistent.
- `test_solicitud_repository_aggregates.py` — repo-level aggregate methods, single-query bound (`django_assert_num_queries(1)` per method), `responsible_role` filter, TZ-aware month grouping.
- `test_lifecycle_service_aggregates.py` — service-level pass-through assertions for `aggregate_*`, `list_for_admin`, `iter_for_admin` (using a recording-stub repo so the contract is enforced even if the repo grows a different shape).

`InMemoryFolioRepository`, `InMemorySolicitudRepository`, `InMemoryHistorialRepository`, and `RecordingNotificationService` live in `lifecycle/tests/fakes.py` — reused by the intake service tests.

## Related Specs

- [Initiative 004 plan](../../../planning/004-solicitud-lifecycle/plan.md) — the implementation blueprint this design promotes from.
- [intake/design.md](../intake/design.md) — consumer of `LifecycleService.transition` (for `cancel_own`) and the `NotificationService` port.
- [revision/design.md](../revision/design.md) — consumer of `LifecycleService.transition` (for take/finalize/cancel by personal).
- [tipos/design.md](../tipos/design.md) — provides `TipoService.snapshot()` and `TipoService.get_for_admin()`.
- [formularios/design.md](../formularios/design.md) — `FormSnapshot` shape stored in `Solicitud.form_snapshot`.
- [flows/solicitud-lifecycle.md](../../../flows/solicitud-lifecycle.md) — end-to-end intake→revision→finalize sequence diagram.
- [reportes/dashboard/design.md](../../reportes/dashboard/design.md) — consumer of `LifecycleService.{aggregate_*, iter_for_admin, list_for_admin}` and the `responsible_role` filter (added in 009).
