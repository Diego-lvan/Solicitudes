# revision — Design

> Canonical reference for the personal-side review feature. Updated after initiative 004 closed.

## Scope

The revision feature is the personal-side mirror of intake. It owns the queue (role-scoped list of solicitudes assigned to the actor's role), the detail-with-actions view, and the three transition verbs that personnel can invoke: **atender** (CREADA → EN_PROCESO), **finalizar** (EN_PROCESO → FINALIZADA), and **cancelar** (CREADA or EN_PROCESO → CANCELADA, when the personal owns the row's responsible_role or is admin).

There is no `assigned_to` field — the queue is shared. Any user with the responsible role can take any row; first-write-wins on contention. Acceptable per requirements.

## Layer wiring

```
Browser → views/{queue,detail,take,finalize,cancel}.py
            │
            ▼
       ReviewService (services/review_service/interface.py)
            │
            └── LifecycleService (owned by lifecycle)
            │
            ▼
       (state machine, repos, audit, notification — see lifecycle/design.md)
```

`ReviewService` is intentionally a thin wrapper over `LifecycleService`: it adds personal-side authorization for read (`get_detail_for_personal` rejects role mismatch) and translates the three personal verbs into `LifecycleService.transition` calls. Keeping the wrapper means the personal HTTP boundary has its own surface to test, mock, and evolve without touching the lifecycle service.

`revision/dependencies.py` wires `LifecycleService → DefaultReviewService`.

## Service contract

`ReviewService` (`services/review_service/interface.py`):

- `list_assigned(role, *, page, filters) -> Page[SolicitudRow]` — admin sees all; everyone else sees rows where `tipo.responsible_role == role`.
- `get_detail_for_personal(folio, role) -> SolicitudDetail` — fetches via lifecycle; raises `Unauthorized` if `role != detail.tipo.responsible_role` (admin bypasses).
- `take(folio, *, actor, observaciones) -> SolicitudDetail` → `transition(action="atender", ...)`
- `finalize(folio, *, actor, observaciones) -> SolicitudDetail` → `transition(action="finalizar", ...)`
- `cancel(folio, *, actor, observaciones) -> SolicitudDetail` → `transition(action="cancelar", ...)`

Cross-cutting authorization (which role may invoke which action) is enforced *inside* `LifecycleService._authorize`, not duplicated here. The wrapper's only authorization concern is the read path.

## Forms

`TransitionForm` (`forms/transition_form.py`) is a single-field Django form: `observaciones = CharField(required=False, max_length=2000)` rendered as a textarea with a maxlength attribute. Validity is enforced explicitly: on `not form.is_valid()`, the view flashes `messages.error(...)` and redirects back to the detail page without invoking the transition. Silent truncation of invalid input was an early bug caught in code review.

## Views

| URL                                            | View                  | Method | Mixin                  |
| ---------------------------------------------- | --------------------- | ------ | ---------------------- |
| `/solicitudes/revision/`                       | `QueueView`           | GET    | `ReviewerRequiredMixin` |
| `/solicitudes/revision/<folio>/`               | `RevisionDetailView`  | GET    | `ReviewerRequiredMixin` |
| `/solicitudes/revision/<folio>/atender/`       | `TakeView`            | POST   | `ReviewerRequiredMixin` |
| `/solicitudes/revision/<folio>/finalizar/`     | `FinalizeView`        | POST   | `ReviewerRequiredMixin` |
| `/solicitudes/revision/<folio>/cancelar/`      | `CancelByPersonalView` | POST  | `ReviewerRequiredMixin` |

`ReviewerRequiredMixin` (in `revision/permissions.py`) admits `Role.CONTROL_ESCOLAR`, `Role.RESPONSABLE_PROGRAMA`, `Role.DOCENTE`, and `Role.ADMIN`. (Docente is included because some tipos route to docente as the responsible role.)

The transition POST views all share the same shape:

1. `actor_from_request(request)` → typed `UserDTO`
2. Validate the `TransitionForm`; on failure flash + redirect to detail
3. Call `ReviewService.{take,finalize,cancel}` inside a try/except `AppError`
4. On success: flash `messages.success(...)` and redirect (detail for take/finalize, queue for cancel since the row leaves the queue)
5. On `AppError`: flash `messages.error(exc.user_message)` and redirect to detail

### URL prefix decision

The plan specified `/revision/` at the project root. The implementation mounts revision at `/solicitudes/revision/` so reverse names stay `solicitudes:revision:queue` rather than a top-level `revision:queue`. Django namespaces aren't nestable across `include()`, and we judged namespace consistency more valuable than the shorter URL. **All solicitudes-app routes share the `solicitudes` parent namespace.**

## Templates

- `templates/solicitudes/revision/queue.html` — filterable, paginated table. Filters: folio (substring), solicitante (matches matricula or full_name), estado (select), date range. Tipo filter is omitted for the same reason as `mis_solicitudes`. **Columns (014):** Folio · Tipo · Solicitante · Atendida por · Fecha · Estado. The folio cell is the row's navigation link; there is no separate "Acción" / "Revisar" column. The "Atendida por" cell renders the personal's full_name (falling back to matrícula via the DTO) when populated, or a muted em-dash (`—`) otherwise — never an empty cell, for screen-reader clarity. Solicitante and Atendida por collapse below `lg`; Fecha collapses below `md`.
- `templates/solicitudes/revision/detail.html` — same data shape as `intake/detail.html` plus an "Acciones" card with a shared `observaciones` textarea and three buttons (Atender / Finalizar / Cancelar) gated by the row's current estado. The cancelar button uses an inline `confirm(...)` JS prompt. **From 014:**
  - The header subtitle shows `tipo.nombre` only (the inline "Solicitante:" prefix was removed; that information now lives in a dedicated card).
  - When `detail.atendida_por` is set, an additional muted line under the heading reads `Atendida por **{full_name}** ({matricula}) · {taken_at|date:"d/m/Y H:i"}`. Hidden otherwise.
  - The right column carries a **Solicitante** card *above* Historial: a `text-muted text-uppercase small` eyebrow, the alumno's `full_name` (`fw-semibold`, falling back to matrícula), `Matrícula: {matricula}` muted, and the email rendered as a `mailto:` link. The card is unconditional — it always renders, since `solicitante` is always present on `SolicitudDetail`.

The action buttons are rendered conditionally:

| Button     | Visible when              |
| ---------- | ------------------------- |
| Atender    | `estado == CREADA`        |
| Finalizar  | `estado == EN_PROCESO`    |
| Cancelar   | `estado in {CREADA, EN_PROCESO}` |

Visibility is a *user-experience* gate; the lifecycle service is the authoritative authorization surface. A user who hand-crafts a POST against the wrong action gets `InvalidStateTransition` from the service.

## Tests

- `test_revision_views.py` — covers all five views: queue role-scoping (CE sees only CE-responsible rows; admin sees all), detail role mismatch rejected, atender CREADA→EN_PROCESO, finalizar EN_PROCESO→FINALIZADA, finalizar from CREADA blocked (state-machine error → flash + redirect), cancel by personal succeeds, cross-role atender blocked (302 with flash or 403 from auth — both acceptable). **From 014:** queue exposes the "Atendida por" header and not "Acción" / "Revisar"; row populated for an EN_PROCESO solicitud and blank for CREADA. Detail renders the Solicitante card with the matrícula and a `mailto:` link, and the "Atendida por" line surfaces only for atendida rows.

The Tier-1 multi-step e2e in `intake/tests/test_e2e_tier1.py::test_alumno_creates_personal_atiende_and_finaliza` exercises the cross-feature happy path. The Tier-2 Playwright `test_personal_takes_and_finalizes_solicitud` walks through the queue → detail → atender → finalizar flow in a real browser with screenshots; from 014 it also asserts the new column, the Solicitante card, and the handler line, and clicks the folio link rather than a separate "Revisar" button.

## Related Specs

- [Initiative 004 plan](../../../planning/004-solicitud-lifecycle/plan.md)
- [Initiative 014 plan](../../../planning/014-revision-handler-display/plan.md) — surfaced "Atendida por" on the queue + detail, dropped the Acción column, added the Solicitante card on detail.
- [lifecycle/design.md](../lifecycle/design.md) — `LifecycleService.transition` is the service this feature wraps.
- [intake/design.md](../intake/design.md) — solicitante-side mirror.
- [tipos/design.md](../tipos/design.md) — `responsible_role` on `TipoSolicitud` drives queue scoping.
- [flows/solicitud-lifecycle.md](../../../flows/solicitud-lifecycle.md) — end-to-end sequence.
