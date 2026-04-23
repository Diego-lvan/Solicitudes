# intake — Design

> Canonical reference for the solicitud intake feature. Updated after initiative 004 closed.

## Scope

The intake feature owns the solicitante's surface: discovering which tipos they can file, rendering the dynamic form, validating it, and persisting a new `Solicitud` row. It also hosts the solicitante-side `cancel_own` verb.

Notifications are out of scope here — intake delegates to a port owned by lifecycle (`NotificationService`). File persistence is delegated to `ArchivoService` (005); the contract is documented under "File handling" below and in detail in `apps/solicitudes/archivos/design.md`.

## Layer wiring

```
Browser → views/{catalog,create,mis_solicitudes,detail,cancel}.py
            │
            ▼
       Form: build_intake_form(snapshot, with_comprobante=...)  (cleaned_data → CreateSolicitudInput)
            │
            ▼
       IntakeService (services/intake_service/interface.py)
            │
            ├── TipoService                  (services interface, owned by tipos)
            ├── SolicitudRepository          (owned by lifecycle)
            ├── HistorialRepository          (owned by lifecycle)
            ├── FolioService                 (owned by lifecycle)
            ├── LifecycleService             (owned by lifecycle — for cancel_own)
            ├── NotificationService          (port owned by lifecycle, NoOp until 007)
            └── MentorService                (port owned by intake, False until 008)
            │
            ▼
       ORM (Solicitud, HistorialEstado, FolioCounter, TipoSolicitud)
```

`intake/dependencies.py` wires everything; the views call the factory once per request.

## Data shapes

### DTOs (`intake/schemas.py`)

- **`CreateSolicitudInput`** — input to `IntakeService.create`. Carries:
  - `tipo_id: UUID`
  - `solicitante_matricula: str`
  - `valores: dict[str, Any]` — JSON-safe primitives keyed by stringified field UUID, produced by `DynamicTipoForm.to_values_dict()`
  - `is_mentor_at_creation: bool` — resolved by the view via `MentorService.is_mentor(matricula)` *before* this DTO is built; the service trusts it.

  The view is responsible for the mentor lookup. The service deliberately does *not* call `MentorService` itself — that keeps the cross-feature reach to the view boundary and the service stays pure-domain.

## Forms

### `build_intake_form(snapshot, *, with_comprobante: bool) -> type[forms.Form]`

Wraps `formularios.builder.build_django_form(snapshot)` and conditionally appends a required `comprobante` `FileField` (`ClearableFileInput`, accept = `.pdf,.jpg,.jpeg,.png`, ≤ 5 MB) when payment is required and the actor is not exempt.

The decision is made by the view (and re-checked in the service-side snapshot logic). The field name is exported as `COMPROBANTE_FIELD` so the create view can detect it in `request.FILES` and surface the file-discard warning until 005 lands.

## Service contract

`IntakeService` (`services/intake_service/interface.py`):

- `list_creatable_tipos(role) -> list[TipoSolicitudRow]` — delegates to `TipoService.list_for_creator(role)`.
- `get_intake_form(slug, *, role, is_mentor) -> tuple[TipoSolicitudDTO, type[forms.Form]]` — looks up the tipo via `TipoService.get_for_creator` (which raises `Unauthorized` if `role ∉ tipo.creator_roles`), captures a `FormSnapshot`, builds the dynamic form. Used by both GET and POST.
- `create(input_dto, *, actor: UserDTO) -> SolicitudDetail` — see flow below.
- `cancel_own(folio, *, actor, observaciones) -> SolicitudDetail` — thin wrapper that calls `LifecycleService.transition(action="cancelar", ...)`. Owner-only authorization is enforced by the lifecycle service's `_authorize`.

### `create` flow

1. `tipo = tipo_service.get_for_admin(input_dto.tipo_id)` — fetch the live tipo.
2. **Re-check creator authorization**: if `actor.role ∉ tipo.creator_roles` or not `tipo.activo` → `CreatorRoleNotAllowed`. Defense in depth on top of the URL-level role mixin.
3. `snapshot = tipo_service.snapshot(tipo.id)` — captured **now**, not at GET time. If the admin edited the tipo between form-render and submit, the persisted snapshot reflects submit-time state. Asserted by `test_create_captures_snapshot_at_create_time_not_earlier`.
4. Compute `pago_exento = tipo.requires_payment AND tipo.mentor_exempt AND input_dto.is_mentor_at_creation`. Full truth table tested in `test_pago_exento_truth_table`.
5. **Inside `transaction.atomic()`**:
   - `folio = folio_service.next_folio(year=now.year)`
   - `solicitud_repository.create(folio, tipo_id, solicitante_matricula, estado=CREADA, form_snapshot=snapshot.model_dump(mode="json"), valores, requiere_pago=tipo.requires_payment, pago_exento)`
   - `historial_repository.append(folio, estado_anterior=None, estado_nuevo=CREADA, actor_matricula, actor_role, observaciones="")`
6. **Outside the atomic block**: `notification_service.notify_creation(folio, responsible_role=tipo.responsible_role)` then `audit.write("solicitud.creada", folio, tipo_id, actor, actor_role)`.
7. Return `solicitud_repository.get_by_folio(folio)` — fresh detail with the initial historial entry.

`requiere_pago` is always `tipo.requires_payment` at the moment of creation, regardless of exemption. `pago_exento` rides alongside as the "did we waive payment for this row?" answer. Both are stored on the row to keep audit/reporting queries stable as the tipo or mentor list change.

## Views

| URL                                  | View                  | Method     | Mixin                  |
| ------------------------------------ | --------------------- | ---------- | ---------------------- |
| `/solicitudes/`                      | `CatalogView`         | GET        | `CreatorRequiredMixin` |
| `/solicitudes/crear/<slug>/`         | `CreateSolicitudView` | GET / POST | `CreatorRequiredMixin` |
| `/solicitudes/mis/`                  | `MisSolicitudesView`  | GET        | `CreatorRequiredMixin` |
| `/solicitudes/<folio>/`              | `SolicitudDetailView` | GET        | `LoginRequiredMixin` (owner OR responsible-role personal OR admin) |
| `/solicitudes/<folio>/cancelar/`     | `CancelOwnView`       | POST       | `CreatorRequiredMixin` (owner; lifecycle enforces estado=CREADA) |

`CreatorRequiredMixin` (in `intake/permissions.py`) admits `Role.ALUMNO` and `Role.DOCENTE`.

`SolicitudDetailView` is in `intake/` because the URL is reached from `mis_solicitudes`. Personal in the responsible role can also reach it; the view's authorization branches on `is_owner` / `is_responsible` / `is_admin` and a non-matching role gets `Unauthorized`. Personal typically reach the same data via the revision feature's detail view, which adds action buttons.

### View → service translation

Views never call repositories. They:

1. Use `_shared/request_actor.actor_from_request(request)` to materialize a typed `UserDTO` from the JWT-authenticated request. The helper raises `AuthenticationRequired` if `user_dto` is missing — a defense-in-depth guard for views that forget the login mixin.
2. Read `request.GET` for filters and `request.POST` / `request.FILES` for the form, then build the input DTO and pass it to `IntakeService`.
3. Catch `AppError` and translate to the appropriate response (re-render with form errors for validation, redirect with `messages.error` for state/auth conflicts, redirect with `messages.success` on the happy path).

### File handling (delivered in 005)

`CreateSolicitudView.post` validates `FileField`s as part of form validation (extensions + size are caught at the form layer, returning **400** with the form re-rendered before any upload buffer reaches the service). After `form.is_valid()`, the view wraps everything in an outer `transaction.atomic()`:

1. `intake_service.create(input_dto, actor=actor)` — inserts the `Solicitud` + initial `HistorialEstado`.
2. For each file in `request.FILES`: `archivo_service.store_for_solicitud(folio=detail.folio, field_id=..., kind=..., uploaded_file=..., uploader=actor)`. The comprobante (form field name `comprobante`) becomes `kind=COMPROBANTE`; every other `field_<32-hex>` becomes `kind=FORM` with `field_id` decoded from the suffix.

The whole block runs in one atomic — if any `store_for_solicitud` call raises, the `Solicitud` row rolls back too. After the block the view calls `storage.cleanup_pending()` in a `try/finally` so any `.partial` files left by a rolled-back transaction are removed (on success the storage's own on_commit hook drains the pending list, so cleanup is a no-op).

Service-level rejections (e.g. comprobante extension/size, FORM `field_id` not in snapshot) raise `AppError` and surface as **422** with the form re-rendered. Both layers enforce: the form provides fast feedback, the service is the canonical authority.

The service interface lives in 005 (`solicitudes.archivos.services.archivo_service.ArchivoService`); intake depends on the interface only — the cross-feature dependency rule.

## Outbound ports

### `MentorService` (`intake/mentor_port.py`)

```python
class MentorService(ABC):
    def is_mentor(self, matricula: str) -> bool: ...
```

Owned by the consumer (intake) per the cross-feature dependency rule. Until 008 lands the real adapter (which will look up the mentor catalog), `intake/dependencies.py:get_mentor_service()` returns `FalseMentorService` — every `is_mentor` call returns `False`, so `pago_exento` is always `False` regardless of `tipo.mentor_exempt`. Real exemption testing is deferred to 008's E2E pass.

The view calls `MentorService.is_mentor(actor.matricula)` exactly twice on the create path: once in `get_intake_form` to decide whether to inject the comprobante field, once after form validation to populate `is_mentor_at_creation` on the input DTO.

## Templates

- `templates/solicitudes/intake/catalog.html` — card grid of available tipos for the actor's role; empty state directs back to `home`.
- `templates/solicitudes/intake/create.html` — bound dynamic form with comprobante field (when applicable), breadcrumb, primary "Enviar solicitud" + secondary "Cancelar" buttons.
- `templates/solicitudes/intake/mis_solicitudes.html` — filterable, paginated table of own solicitudes. Filters: folio (substring), estado (select), date range. `tipo_id` filter is intentionally not surfaced — alumno volume doesn't justify the extra control yet.
- `templates/solicitudes/intake/detail.html` — snapshot field values + historial timeline + owner-only "Cancelar solicitud" button (only when estado=CREADA).
- `templates/solicitudes/_partials/{_estado_badge,_solicitud_row,_historial,_valores_render}.html` — shared with revision.

`_valores_render.html` uses the `get_valor` filter (`solicitudes/templatetags/solicitudes_tags.py`) to look up snapshot field values by stringified UUID — Django templates can't index dicts with dynamic keys natively.

`_estado_badge.html` renders `{{ estado.display_name }}` (Spanish single/multi-word labels: "Creada", "En proceso", "Finalizada", "Cancelada") with semantic Bootstrap badge colors. Status is conveyed by both color *and* text so the WCAG color-as-only-signal rule is satisfied.

## Exceptions (`intake/exceptions.py`)

- **`CreatorRoleNotAllowed`** (Unauthorized, 403) — actor's role is not in `tipo.creator_roles` or the tipo is inactive. Raised by the service; the view-level `CreatorRequiredMixin` is a coarser pre-filter.
- **`ComprobanteRequired`** (DomainValidationError, 422) — reserved for service-level enforcement of the comprobante rule. Today the requirement is enforced at the form layer (a required `FileField`); this exception is the right surface if we later move the check (e.g., to validate a server-issued receipt rather than an upload).

## Tests

- `test_intake_service.py` — direct unit tests with in-memory fakes covering: snapshot captured at create-time, `pago_exento` truth table (all 8 combinations), initial historial has `estado_anterior=None` and snapshots `actor_role`, notification fires with `tipo.responsible_role`, role/inactive-tipo guards, `cancel_own` delegates to lifecycle with `action="cancelar"`.
- `test_intake_views.py` — auth (anonymous, wrong role), catalog scoping, create form GET, create POST happy path + invalid-form path + creator-role mismatch, parallel folios, `mis_solicitudes` owner scoping, detail authorization (owner / unrelated alumno), `cancel_own` from CREADA / blocked from EN_PROCESO.
- `test_e2e_tier1.py` (multi-step Django Client) — alumno→personal→finalize, owner cancel from CREADA + blocked at EN_PROCESO, distinct folios on parallel creates, snapshot integrity when the tipo's labels change.
- `tests-e2e/test_solicitud_golden_path.py::test_alumno_creates_solicitud_through_dynamic_form` — Tier-2 Playwright golden path with desktop + mobile screenshots.

## Related Specs

- [Initiative 004 plan](../../../planning/004-solicitud-lifecycle/plan.md)
- [lifecycle/design.md](../lifecycle/design.md) — owner of `Solicitud`/`HistorialEstado`/`FolioCounter`, state machine, `NotificationService` port.
- [revision/design.md](../revision/design.md) — personal-side mirror of intake.
- [tipos/design.md](../tipos/design.md) — `TipoService.get_for_creator` / `snapshot` consumed by intake.
- [formularios/design.md](../formularios/design.md) — `build_django_form` and `FormSnapshot` consumed by `build_intake_form`.
- [flows/solicitud-lifecycle.md](../../../flows/solicitud-lifecycle.md) — end-to-end sequence.
