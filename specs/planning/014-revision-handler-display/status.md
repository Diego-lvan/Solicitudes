# 014 — Revision Handler Display — Status

**Status:** Done
**Last updated:** 2026-04-26

## Checklist

### DTOs
- [x] Add `HandlerRef` frozen DTO to `lifecycle/schemas.py`.
- [x] Add `atendida_por_matricula: str = ""` and `atendida_por_nombre: str = ""` to `SolicitudRow`.
- [x] Add `atendida_por: HandlerRef | None = None` to `SolicitudDetail`.

### Repository
- [x] Annotate `_base_queryset()` in `OrmSolicitudRepository` with `Subquery` columns selecting the actor of the row's `atender` historial entry.
- [x] `_to_row` reads the annotations into the new DTO fields (default to `""` when `None`).
- [x] `_to_detail` derives `HandlerRef` from the already-loaded historial without additional SQL.
- [x] Document in code that `iter_for_admin` inherits the annotation harmlessly (cheap subquery).

### Test fakes
- [x] [P] `InMemorySolicitudRepository` (`lifecycle/tests/fakes.py`) populates the new fields/`HandlerRef` from its in-memory historial.

### Repository tests
- [x] [P] Cases for atendida_por across all four estados (CREADA empty, EN_PROCESO populated, FINALIZADA populated, CANCELADA-from-CREADA empty, CANCELADA-from-EN_PROCESO populated).
- [x] [P] `test_list_uses_at_most_three_queries` still passes after the annotation.
- [x] [P] `get_by_folio` populates `atendida_por` with no additional SQL (`django_assert_num_queries`).

### Templates
- [x] `templates/solicitudes/revision/queue.html`: insert "Atendida por" `<th>` and `<td>`; remove the "Acción" `<th>` and trailing `<td>` with the "Revisar" button.
- [x] `templates/solicitudes/revision/detail.html`: render the **Solicitante** card (nombre · matrícula · email-as-`mailto:`) and the "Atendida por" header line (only when `detail.atendida_por`).

### View tests
- [x] [P] Queue: "Atendida por" header present; "Acción" header absent; populated row for EN_PROCESO; `—` for CREADA.
- [x] [P] Detail: Solicitante card present with matrícula + `mailto:` email; "Atendida por" line present for EN_PROCESO row, absent for CREADA.

### E2E
- [x] Tier 1 (Client): `test_queue_renders_atendida_por_column_and_no_accion` — atender then GET queue; assert column + no Acción/Revisar.
- [x] Tier 1 (Client): `test_detail_renders_solicitante_card_and_handler_line_for_en_proceso` + `test_detail_handler_line_absent_for_creada` — atender then GET detail; assert Solicitante card and handler line.
- [x] Tier 2 (browser/Playwright): extended existing `test_personal_takes_and_finalizes_solicitud` with assertions for the new column, Solicitante card, and handler line.

## Blockers

None.

[P] = can run in parallel
