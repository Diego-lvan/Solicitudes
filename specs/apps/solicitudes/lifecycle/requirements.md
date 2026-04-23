# lifecycle — Requirements

> WHAT this feature does and WHY. No implementation details. Shipped by initiative **004 — Solicitud Lifecycle** and extended additively by initiative **009 — Reports & Dashboard**.

## Purpose

Lifecycle is the **canonical home of the solicitud as a domain entity**. It owns the data model (`Solicitud`, `HistorialEstado`, `FolioCounter`), the state machine that defines what estados exist and which transitions are legal, the rules about *who* may invoke each transition, and the read APIs (detail and role-scoped lists) that every other feature consumes.

Both surfaces that move a solicitud — intake (alumno cancelling their own) and revision (personal taking, finalizing, cancelling) — go through this feature's `LifecycleService.transition`. A single service is the only place state changes happen, the only place the historial is appended, and the only place outbound notifications and audit are fired.

## Why a single state machine

The university's process has subtle authorization rules that must remain consistent no matter which UI surface invokes them — for instance:
- the solicitante can cancel their own row but **only** while it's `CREADA`;
- personal in the row's `responsible_role` can take it from `CREADA` to `EN_PROCESO`, finalize it from `EN_PROCESO`, or cancel from either;
- admins bypass role checks but still respect the state matrix.

Splitting these rules across intake and revision would inevitably drift. Centralizing them in `LifecycleService._authorize` keeps "who may do what when" provably consistent. The state diagram, the action verb names, and the legal `(estado, action) -> estado_destino` map are this feature's authoritative output.

## In scope

- The **`Solicitud` model**: folio, tipo FK, solicitante FK, estado, frozen `form_snapshot`, `valores` payload, `requiere_pago`, `pago_exento`, timestamps.
- The **`HistorialEstado` model**: append-only state-transition log with `estado_anterior` (nullable for the initial row), `estado_nuevo`, `actor` + snapshotted `actor_role`, `observaciones`, `created_at`.
- The **`FolioCounter` model** + folio allocator: `SOL-YYYY-NNNNN`, sequential per year, allocated under row-level lock.
- The **state machine**: estados (`CREADA`, `EN_PROCESO`, `FINALIZADA`, `CANCELADA`), the legal transition matrix, and `display_name` mapping for Spanish labels.
- The **transition service** (`LifecycleService.transition`): authorization, state advance, historial append (atomic), then post-commit notification + audit.
- **Read APIs**: detail by folio, paginated lists scoped to solicitante / responsible role / admin-wide, plus the additive aggregations (`aggregate_by_estado`, `aggregate_by_tipo`, `aggregate_by_month`) and the admin-wide cursor (`iter_for_admin`) consumed by `reportes` since 009.
- Two **outbound ports** the consumer owns: `NotificationService` (adapted by `notificaciones` in 007) and the `_shared/audit.py` log.
- The cross-feature DTOs other features depend on: `SolicitudDetail`, `SolicitudRow`, `HistorialEntry`, `SolicitudFilter`, `TransitionInput`.

## Out of scope

- The HTTP boundaries that drive transitions. Intake hosts the solicitante's `cancel_own` action; revision hosts the queue + `atender` / `finalizar` / `cancelar` views. Lifecycle has no views of its own.
- Form rendering, file upload, comprobante validation — owned by `intake`/`formularios`/`archivos`.
- Email dispatch — `notificaciones` (initiative 007) plugs into the `NotificationService` port.
- PDF rendering — `pdf` (initiative 006) consumes `LifecycleService.get_detail` but lives elsewhere.
- Aggregation **presentation** — `reportes` consumes the aggregation methods; lifecycle never knows about dashboards or exports.
- An `assigned_to` field. The queue is intentionally shared — first-write-wins on contention is the chosen trade-off.

## Functional requirements

| ID | Requirement | Source |
|---|---|---|
| RF-LIF-01 | Estados and the legal transition matrix must match RF-05: `Creada → En proceso → Finalizada`; `Creada → Cancelada`; `En proceso → Cancelada`. No other transitions exist. | RF-05 |
| RF-LIF-02 | Every transition must produce a historial entry capturing the previous estado, the new estado, the actor, the actor's role at the time, observations, and a timestamp. The initial `CREADA` insertion must produce a historial row with `estado_anterior = None`. | RF-05, RF-08, RNF-04 |
| RF-LIF-03 | The state advance and the historial append must commit atomically. Notifications and audit fire after commit and must not roll back a committed transition. | RF-05, RF-07 |
| RF-LIF-04 | Folios must follow `SOL-YYYY-NNNNN`, be unique system-wide, and be allocated sequentially within a calendar year under row-level lock. | RF-04 |
| RF-LIF-05 | The transition service must enforce: solicitante may only `cancelar` from `CREADA`; personal in `tipo.responsible_role` may `atender` (CREADA → EN_PROCESO), `finalizar` (EN_PROCESO → FINALIZADA), and `cancelar` (CREADA or EN_PROCESO); admin bypasses role checks but still respects the state matrix. | RF-05, RF-06, RF-09 |
| RF-LIF-06 | The detail read must hydrate the historial in chronological order and include the snapshotted form definition, the values, the comprobante flags, and the tipo's plantilla reference. | RF-08, RF-09 |
| RF-LIF-07 | Role-scoped paginated lists must filter by estado, tipo, folio substring, solicitante substring, and date range, and must cap query work to a small, regression-pinned number of SQL statements. | RF-08 |
| RF-LIF-08 | The model and read APIs must preserve the **immutability of `form_snapshot`, `requiere_pago`, and `pago_exento`** captured at create time. | RF-04, RF-11 |
| RF-LIF-09 | The repository must expose admin-wide aggregations by estado, tipo, and month, plus an admin-wide streaming iterator that bypasses the per-page count round trip. Each aggregation must execute as a single SQL statement. | RNF-05, perf budget |
| RF-LIF-10 | The repository must support filtering by `responsible_role` for the reports surface, leveraging the existing tipo index. | RNF-05 |

## Non-functional requirements

- **One state-change surface.** No model save in any other feature may bypass `LifecycleService.transition` to advance estado. The historial is the auditable record of every transition; missing rows are a correctness bug, not a logging gap.
- **Snapshot fields are write-once.** `form_snapshot`, `valores`, `requiere_pago`, `pago_exento` are set at create-time and never mutated. Read-time recomputation of `pago_exento` from the current mentor catalog is forbidden — the stamp is the answer.
- **`actor_role` is snapshotted on every historial entry**, not derived from the actor at read time. A user's role can change later; "who finalized this in 2026?" must keep answering with the role they had then.
- **Cross-feature direction is consumer-defined.** The `NotificationService` port is owned here (lifecycle is the consumer); the email feature adapts. The reverse import is forbidden.
- **Aggregation queries are bounded.** Each `aggregate_by_*` method is a single SQL statement (regression-pinned); the dashboard render is bounded at ~12 queries total.
- **Streaming iterator is server-side on PostgreSQL.** SQLite materializes — acceptable for dev only and documented at the call site.
- **Listing is pagination-aware** with a max page size that prevents abuse from the HTTP boundary.
- **Spanish display labels are centralized** in `Estado.display_name`. Templates render labels via this helper rather than `value.title()` so multi-word labels ("En proceso") render correctly.

## Open questions

- **Folio collision strategy.** Today's allocator is `select_for_update` on a per-year counter. If higher throughput is ever needed, a Postgres-sequence-per-year strategy can replace the row-lock approach; a placeholder `FolioCollision` exception is documented for that future surface but is unreachable in the current implementation.

## Related Specs

- [design.md](./design.md) — HOW.
- [`specs/apps/solicitudes/intake/design.md`](../intake/design.md) — consumer (creates the row, calls `cancel_own`).
- [`specs/apps/solicitudes/revision/design.md`](../revision/design.md) — consumer (calls `atender` / `finalizar` / `cancelar`).
- [`specs/apps/reportes/dashboard/design.md`](../../reportes/dashboard/design.md) — consumer of the aggregation + cursor APIs added in 009.
- [`specs/apps/solicitudes/tipos/design.md`](../tipos/design.md) — provides `responsible_role`, `creator_roles`, `requires_payment`, `mentor_exempt`, `plantilla_id`.
- [`specs/flows/solicitud-lifecycle.md`](../../../flows/solicitud-lifecycle.md) — end-to-end sequence.
- [`specs/global/requirements.md`](../../../global/requirements.md) — RF-04, RF-05, RF-06, RF-08, RF-09, RNF-04, RNF-05.
