# 014 — Revision Handler Display

## Summary

Surface "Atendida por" in the revision queue and detail views, drop the redundant "Acción" column from the queue, and render solicitante context (nombre, matrícula, email) prominently on the revision detail page. Pure additive change derived from existing `HistorialEstado` rows: no schema migration, no change to the shared-queue invariant, no change to the lifecycle state machine or its authorization rules.

## Depends on

- **004 — Solicitud Lifecycle** — owns `Solicitud`, `HistorialEstado`, `SolicitudRepository`, `SolicitudRow`, `SolicitudDetail`.
- **002 — Auth & Users** — `UserDTO.email` and `full_name` are already populated on `SolicitudDetail.solicitante`.

## Affected Modules

- `solicitudes/lifecycle` — DTO additions (`HandlerRef`, two fields on `SolicitudRow`, one on `SolicitudDetail`); repository annotation on the queue queryset; in-memory derivation of `atendida_por` in `_to_detail`.
- `solicitudes/revision` — template-only changes (queue + detail). No service or view contract change.

## References

- [revision/requirements.md](../../apps/solicitudes/revision/requirements.md) — Addendum 014 (RF-REV-10..15).
- [revision/design.md](../../apps/solicitudes/revision/design.md) — current revision design; will be updated at closeout.
- [lifecycle/design.md](../../apps/solicitudes/lifecycle/design.md) — `SolicitudRepository`, query-count cap, `_to_detail`, historial shape.
- [tipos/design.md](../../apps/solicitudes/tipos/design.md) — `responsible_role` drives queue scoping (unchanged).
- [flows/solicitud-lifecycle.md](../../flows/solicitud-lifecycle.md) — end-to-end sequence (unchanged).
- `.claude/rules/django-code-architect.md` — layering rules.
- `.claude/skills/frontend-design/` — Bootstrap 5 + accessibility conventions for the new Solicitante card and the column change.

## Implementation Details

### 1. DTO additions — `app/solicitudes/lifecycle/schemas.py`

Add a new frozen DTO and extend the two existing ones. All additions are defaulted so callers and tests that don't care about handler data don't break.

```python
class HandlerRef(BaseModel):
    """Who performed the atender transition. Empty for never-atendida rows."""

    model_config = ConfigDict(frozen=True)

    matricula: str
    full_name: str
    taken_at: datetime


class SolicitudRow(BaseModel):
    # ... existing fields ...
    atendida_por_matricula: str = ""
    atendida_por_nombre: str = ""


class SolicitudDetail(BaseModel):
    # ... existing fields ...
    atendida_por: HandlerRef | None = None
```

Rationale for the split shape:
- Queue path: two flat strings keep the row template trivially renderable and avoid leaking `None` into Jinja-style truthiness checks.
- Detail path: a structured `HandlerRef` (with `taken_at`) lets the template render `"Atendida por: X (matrícula) · 26/04/2026 14:32"` cleanly.

### 2. Repository — `app/solicitudes/lifecycle/repositories/solicitud/implementation.py`

**Queue paths** (`list_for_solicitante`, `list_for_responsible_role`, `list_all` — all flow through `_base_queryset` → `_paginate` → `_to_row`):

Annotate the queryset in `_base_queryset` with two `Subquery` columns sourced from `HistorialEstado`. The subquery selects the actor of the row's `atender` transition (most recent if ever multiple, though the current state machine only allows one CREADA→EN_PROCESO):

```python
from django.db.models import OuterRef, Subquery

from solicitudes.models import HistorialEstado  # existing app-level model

_atender_actor_qs = HistorialEstado.objects.filter(
    solicitud_id=OuterRef("folio"),
    estado_nuevo=Estado.EN_PROCESO.value,
).order_by("-created_at")

# inside _base_queryset():
return (
    Solicitud.objects.select_related("tipo", "solicitante")
    .annotate(
        _atendida_por_matricula=Subquery(
            _atender_actor_qs.values("actor__matricula")[:1]
        ),
        _atendida_por_nombre=Subquery(
            _atender_actor_qs.values("actor__full_name")[:1]
        ),
    )
    .order_by("-created_at")
)
```

`_to_row` reads the annotations (defaulting to `""` when `None`):

```python
SolicitudRow(
    # ... existing fields ...
    atendida_por_matricula=getattr(row, "_atendida_por_matricula", "") or "",
    atendida_por_nombre=getattr(row, "_atendida_por_nombre", "") or "",
)
```

**Detail path** (`_to_detail`): historial is already loaded into memory by the call to `self._historial.list_for_folio(folio)`. Iterate it once and pick the latest `EN_PROCESO` entry; build `HandlerRef` if found. **No additional SQL.**

```python
atendida_por = next(
    (
        HandlerRef(
            matricula=h.actor_matricula,
            full_name=h.actor_nombre or h.actor_matricula,
            taken_at=h.created_at,
        )
        for h in sorted(historial, key=lambda h: h.created_at, reverse=True)
        if h.estado_nuevo == Estado.EN_PROCESO
    ),
    None,
)
```

**Aggregations and `iter_for_admin`** must NOT inherit the new annotation (it's pure overhead for them). The aggregations build their queryset from `Solicitud.objects.all()`, not `_base_queryset()`, so they're already isolated. `iter_for_admin` does use `_base_queryset()` — the subquery is included but the streaming export does not need the fields. Either (a) leave it (subquery is cheap) or (b) introduce a `_base_queryset(*, with_handler: bool = True)` flag and pass `False` from the iterator. **Pick (a)** — simpler, the subquery cost on streamed exports is bounded by the same index the historial repo already relies on (`(solicitud, -created_at)`). Document this trade in the implementation comment.

### 3. Query-count cap

The existing test `test_list_uses_at_most_three_queries` (in `lifecycle/tests/test_solicitud_repository.py`) asserts the queue path stays at ≤ 3 queries. The annotation is a SELECT-time subquery, not a JOIN that fans out, so the count remains 3. Re-assert after the change; if it grows, fall back to a `Prefetch` strategy, but verify first.

### 4. Templates — `app/templates/solicitudes/revision/`

**`queue.html`** — column changes only:

Header row:
```html
<th scope="col">Folio</th>
<th scope="col">Tipo</th>
<th scope="col" class="d-none d-lg-table-cell">Solicitante</th>
<th scope="col" class="d-none d-lg-table-cell">Atendida por</th>
<th scope="col" class="d-none d-md-table-cell">Fecha</th>
<th scope="col">Estado</th>
{# "Acción" column removed (RF-REV-11) #}
```

Body row: the folio cell remains a link; replace the trailing `<td>` (Acción button) with the new `Atendida por` cell:
```html
<td class="d-none d-lg-table-cell">
  {% if row.atendida_por_nombre %}
    {{ row.atendida_por_nombre }}
  {% else %}
    <span class="text-muted">—</span>
  {% endif %}
</td>
```
Place this cell between Solicitante and Fecha. Drop the entire `<td class="text-end">` that holds the "Revisar" button.

**`detail.html`** — two surgical inserts:

Below the existing `<h1>{{ detail.folio }}</h1>` line, replace the muted subtitle (`Solicitante: {{ detail.solicitante.full_name|… }}`) with a tighter "tipo only" subtitle, and add a new **Solicitante** card to the right column (or above "Datos de la solicitud" — implementor's call, but follow `frontend-design` conventions):

```html
{# RF-REV-12: Solicitante card #}
<div class="card mb-4">
  <div class="card-body">
    <h2 class="h6 card-title text-muted text-uppercase small">Solicitante</h2>
    <div class="fw-semibold">{{ detail.solicitante.full_name|default:detail.solicitante.matricula }}</div>
    <div class="small text-muted">Matrícula: {{ detail.solicitante.matricula }}</div>
    <div class="small">
      <a href="mailto:{{ detail.solicitante.email }}">{{ detail.solicitante.email }}</a>
    </div>
  </div>
</div>
```

And the "Atendida por" line near the header (RF-REV-13), shown only when populated:

```html
{% if detail.atendida_por %}
  <div class="text-muted small">
    Atendida por: <span class="fw-semibold">{{ detail.atendida_por.full_name }}</span>
    ({{ detail.atendida_por.matricula }}) · {{ detail.atendida_por.taken_at|date:"d/m/Y H:i" }}
  </div>
{% endif %}
```

No JS, no new partial files unless the implementor judges the Solicitante card belongs in `_partials/`.

### 5. Service layer

**No change.** `ReviewService.list_assigned` and `get_detail_for_personal` already pass `SolicitudRow`/`SolicitudDetail` through unchanged. In-memory fakes used by tests (`InMemorySolicitudRepository`) need to populate the new fields — see test plan below.

### 6. Tests

**Repository** (`app/solicitudes/lifecycle/tests/test_solicitud_repository.py`):
- New cases: a CREADA row has `atendida_por_*` empty; an EN_PROCESO row has it populated with the atender's matrícula and full_name; a FINALIZADA row preserves the atender (not the finalizer); a CANCELADA-from-CREADA row stays empty; a CANCELADA-from-EN_PROCESO row stays populated.
- Extend `test_list_uses_at_most_three_queries` to confirm the new annotation does not push past 3.
- `get_by_folio` returns `SolicitudDetail.atendida_por` correctly for each estado, with **no extra SQL** (assert via `django_assert_num_queries`).

**Service** (`app/solicitudes/lifecycle/tests/fakes.py`, `test_lifecycle_service.py`):
- `InMemorySolicitudRepository._to_row` and `_to_detail` derive the new fields from the in-memory historial list (matching the ORM derivation). Existing transition-matrix tests untouched.

**Views** (`app/solicitudes/revision/tests/test_revision_views.py`):
- Queue render: column header "Atendida por" present; "Acción" header absent; row populated for an EN_PROCESO row, blank cell for a CREADA row.
- Detail render: Solicitante card present with full name, matrícula, and a `mailto:` link with the user's email. "Atendida por" line present and includes name + matrícula + formatted date for an EN_PROCESO row; absent for a CREADA row.

**Templates / accessibility**: the column header is a `<th scope="col">`; the empty cell uses `—` not blank to avoid empty-cell screen-reader confusion (consistent with `frontend-design`).

### 7. Out of scope

- Adding `assigned_to` / claim semantics. Shared queue + first-write-wins stays.
- Solicitante-side ("Mis solicitudes") list or detail.
- Showing a separate "finalizada por" / "cancelada por" attribution. Historial already has this; the page's existing historial card is the audit surface.
- Notifications mentioning the handler.
- Filter UI on the queue for "atendida por" — out of scope; can be added later if needed.

### 8. Sequencing

1. DTOs + in-memory fakes (so service/repo tests can be written before the ORM annotation lands).
2. Repository annotation + `_to_row`/`_to_detail` derivation; query-count regression test.
3. Templates + view tests.
4. E2E.

## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)
- `revision_queue_shows_atendida_por_and_no_accion_column` — log in as personal in the responsible role, atender a CREADA solicitud, GET `/solicitudes/revision/`, assert the response HTML contains the new column header and the personal user's name in the relevant row, and does **not** contain `>Acción<` in a `<th>` or a `Revisar` action button.
- `revision_detail_shows_solicitante_card_and_handler_line` — same setup; GET the detail URL and assert the Solicitante card shows the alumno's matrícula and email-as-`mailto:`, and the "Atendida por" line names the personal user.

### Browser (Tier 2 — `pytest-playwright`)
- `test_personal_takes_and_finalizes_solicitud` already exists and walks queue → detail → atender → finalizar. **Extend** (don't add a new test) to assert: the new column is visible after atender, the Solicitante card is visible on the detail page, and the "Atendida por" line is visible after the atender step. Single browser session reuse keeps this cheap.

## Acceptance Criteria

- [ ] `SolicitudRow` carries `atendida_por_nombre` / `atendida_por_matricula`; `SolicitudDetail` carries `atendida_por: HandlerRef | None`; both default to empty/`None`.
- [ ] Repository annotation populates the queue fields without growing the query count past 3 for the queue path.
- [ ] `_to_detail` populates `atendida_por` from in-memory historial with no additional SQL.
- [ ] Revision queue renders the "Atendida por" column and no "Acción" column.
- [ ] Revision detail renders a Solicitante card (nombre · matrícula · email-as-`mailto:`) and an "Atendida por: name (matrícula) · date" line whenever the row has been atendida.
- [ ] All new tests pass; existing transition-matrix and lifecycle tests untouched.
- [ ] No DB migration; no service contract change; shared-queue invariant preserved.
