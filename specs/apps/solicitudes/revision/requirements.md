# revision — Requirements

> WHAT this feature does and WHY. No implementation details. Shipped by initiative **004 — Solicitud Lifecycle**.

## Purpose

The personal-side mirror of intake. Revision is the surface where Control Escolar, Responsable de Programa, Docente, and Admin see incoming solicitudes, take them, finalize them, or cancel them. Without revision, solicitudes file but never get reviewed — the whole pipeline stops.

The feature satisfies **RF-06** (routing by responsible role), **RF-08** (consult/track for personal), and **RF-09** (atender/finalizar/cancelar). It is intentionally a **thin wrapper over `LifecycleService`**: the wrapper adds personal-side authorization for read and translates three personal verbs into transition calls; everything else (the state machine, historial append, notifications, audit) is owned by lifecycle.

## Why a wrapper instead of using `LifecycleService` directly

The personal HTTP boundary has its own UX shape: a queue, role-scoped filtering on the read path, the action button gating on detail, and a single `observaciones` form shared across three POST views. Wrapping `LifecycleService` lets the personal surface have its own service contract to test, mock, and evolve without forcing presentation concerns into the state-machine layer.

The trade-off — one extra hop on each call — is worth it: the read-path role check (`role != detail.tipo.responsible_role` → `Unauthorized`) lives in one place, and the verb-mapping (`take` → `transition(action="atender")`, etc.) keeps view code free of state-machine vocabulary.

## In scope

- A **role-scoped queue** at `/solicitudes/revision/`: admins see all rows; personal see only rows where `tipo.responsible_role` matches their role. Filterable by folio (substring), solicitante (matrícula or full name substring), estado, and date range.
- A **detail-with-actions view** at `/solicitudes/revision/<folio>/`: same data shape as the intake detail page plus an "Acciones" card with three buttons gated by current estado, all submitting through a shared `observaciones` textarea.
- Three **transition POST endpoints**:
  - `atender` — `CREADA → EN_PROCESO`
  - `finalizar` — `EN_PROCESO → FINALIZADA`
  - `cancelar` — `CREADA` or `EN_PROCESO` → `CANCELADA`
- A **shared queue contention model**: there is no `assigned_to` field. Any user with the responsible role can take any row; first-write-wins on contention is acceptable.
- **Read-path authorization** (`get_detail_for_personal`): rejects role mismatch with `Unauthorized`; admins bypass.

## Out of scope

- The state machine, the transition matrix, the action authorization rules, the historial append, the notification fan-out, the audit log. All of that is `lifecycle`.
- The solicitante-side flow (catalog, create form, "Mis solicitudes", `cancel_own`). That's `intake`.
- Sending email — `notificaciones` (initiative 007); revision only invokes lifecycle's notification port indirectly via the transition.
- PDF generation. Revision's detail template renders a "Generar PDF" button gated on `tipo.plantilla_id`; the actual rendering is `pdf` (initiative 006).
- Per-user assignment / claim semantics. The queue is shared.
- A separate "my actions" history view. The solicitud's detail page shows the historial; that's the audit surface for personal as well.

## Functional requirements

| ID | Requirement | Source |
|---|---|---|
| RF-REV-01 | Personal in `Role.CONTROL_ESCOLAR`, `Role.RESPONSABLE_PROGRAMA`, `Role.DOCENTE`, or `Role.ADMIN` may access the revision queue. Other roles are denied at the URL boundary. | RF-06, RNF-06 |
| RF-REV-02 | The queue must scope rows to the actor's role: a personal user sees only solicitudes whose `tipo.responsible_role` matches their role. Admin sees all rows. | RF-06 |
| RF-REV-03 | The queue must support filters on folio (substring), solicitante (matrícula or full name substring), estado, and date range, with pagination. | RF-08 |
| RF-REV-04 | The detail view must reject access when the actor's role does not match `tipo.responsible_role` and the actor is not admin. | RF-06, RF-09 |
| RF-REV-05 | The `atender` action must advance `CREADA → EN_PROCESO`; the `finalizar` action must advance `EN_PROCESO → FINALIZADA`; the `cancelar` action must advance from `CREADA` or `EN_PROCESO` to `CANCELADA`. Any other (estado, action) combination must be rejected. | RF-05, RF-09 |
| RF-REV-06 | Each transition must accept an optional `observaciones` field (≤ 2000 chars), preserved on the historial entry. Invalid input must flash an error and redirect to detail without invoking the transition (no silent truncation). | RF-05, RF-09, audit clarity |
| RF-REV-07 | The detail page's action buttons must be visible only when the current estado allows that verb. Authoritative authorization, however, must still happen at the lifecycle layer (a hand-crafted POST against the wrong action must be rejected with `InvalidStateTransition`, not relied on UX gating). | RF-09, defense-in-depth |
| RF-REV-08 | After a successful transition the user must land on a sensible page with a Spanish success message — detail for `atender`/`finalizar`, queue for `cancelar` (the row leaves the queue). | UX |
| RF-REV-09 | All transition errors (`InvalidStateTransition`, `Unauthorized`, `SolicitudNotFound`) must surface as flashed Spanish messages and redirect back to detail; views must not raise to a 500. | RF-09, UX, error contract |

## Non-functional requirements

- **Authoritative authorization is in lifecycle.** Revision's only authorization concern is the read path. The state machine and the per-action role rules live in `LifecycleService._authorize` and must not be duplicated here.
- **Shared queue, first-write-wins.** No `assigned_to` field; concurrency is bounded only by the lifecycle service's transition atomicity. This is a deliberate simplification documented in lifecycle's design.
- **Cross-feature direction is one-way.** Revision consumes `lifecycle`. Lifecycle does not import from revision.
- **URL namespacing.** All revision routes live under `/solicitudes/revision/` so reverse names share the `solicitudes` parent namespace. The plan considered a top-level `/revision/`; the chosen path keeps namespace consistency at the cost of a longer URL.
- **Spanish UI copy** end-to-end (queue table, detail view, action buttons, confirmation prompts, flash messages). Code identifiers in English.
- **Accessibility.** Estado is conveyed by both color and text in every badge (WCAG color-as-only-signal). The cancel button uses an inline confirm prompt — acceptable for v1; a richer modal is a future improvement.

## Open questions

None at initiative closeout. If/when the queue grows large enough that contention becomes a real problem, an `assigned_to` claim flow can be added; until then, the shared-queue model stands.

## Addendum — initiative 014 (2026-04-26): handler visibility + solicitante context

Extends RF-REV-* with surfaces that answer two recurring operator questions: "who is currently handling this?" and "who is sending it?" — without changing the shared-queue invariant or the data model.

| ID | Requirement | Source |
|---|---|---|
| RF-REV-10 | The revision queue must show an **"Atendida por"** column whose value is the user (full name, falling back to matrícula) who performed the `atender` transition on the row. The column must be blank when the row has never been atendida (estado is `CREADA`, or `CANCELADA` direct from `CREADA`). The column must remain populated for `EN_PROCESO`, `FINALIZADA`, and `CANCELADA-from-EN_PROCESO`. | Operator visibility |
| RF-REV-11 | The revision queue must **not** render an "Acción" column. Navigation to the detail page is the existing folio-cell link; the redundant action button is removed. | UX simplification |
| RF-REV-12 | The revision detail page must render a **"Solicitante"** card showing nombre completo, matrícula, and email (email as a `mailto:` link). This data is already present on the loaded `SolicitudDetail.solicitante`; the requirement is to surface it prominently rather than as a one-line subtitle. | RF-09, operator context |
| RF-REV-13 | The revision detail page must show, near the header, a line `"Atendida por: {nombre} ({matrícula}) · {fecha}"` whenever the row has been atendida. The line is hidden otherwise. | RF-09, operator context |
| RF-REV-14 | "Atendida por" data must be derivable from existing `HistorialEstado` rows (actor of the most recent transition with `estado_nuevo == EN_PROCESO`). No `assigned_to` field is added; the shared-queue model documented in this spec stands. | Data-model invariance |
| RF-REV-15 | The queue list query must remain bounded at **≤ 3 SQL queries** after the addendum (one count, one rows, pagination overhead). Asserted by an existing query-count test that this initiative extends. | Performance contract |

## Related Specs

- [design.md](./design.md) — HOW.
- [`specs/apps/solicitudes/lifecycle/design.md`](../lifecycle/design.md) — owns the state machine, the transition service, and the historial. Revision wraps this.
- [`specs/apps/solicitudes/intake/design.md`](../intake/design.md) — solicitante-side mirror.
- [`specs/apps/solicitudes/tipos/design.md`](../tipos/design.md) — `responsible_role` on tipo drives queue scoping.
- [`specs/flows/solicitud-lifecycle.md`](../../../flows/solicitud-lifecycle.md) — end-to-end sequence.
- [`specs/global/requirements.md`](../../../global/requirements.md) — RF-05, RF-06, RF-08, RF-09, RNF-06.
