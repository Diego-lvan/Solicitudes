# `_shared/audit.py` — Design

> Structured activity-log writer. Introduced in initiative 004.

## Purpose

Emit one line per business event (solicitud created, estado changed, etc.) on a dedicated `audit` logger so the events are tail-able and grep-able out of the JSON log stream. v1 has no DB persistence — if compliance later asks for a queryable audit trail we replace the implementation here without touching call sites.

## Contract

```python
# _shared/audit.py
def write(event: str, **fields: Any) -> None:
    """Emit a structured INFO line on the `audit` logger with `extra=` carrying the fields."""
```

Each call writes exactly one line at INFO level. The event name (e.g. `solicitud.creada`, `solicitud.estado_cambiado`) is both the log message and `record.audit_event`; the kwargs become individual `LogRecord` attributes via `extra=`.

The `audit` logger is configured by `_shared/logging_config.py` like any other logger. Filters and handlers are environment-specific (dev tails to stdout; prod ships to the JSON pipeline).

## Call sites (as of 004)

- `IntakeService.create` → `audit.write("solicitud.creada", folio, tipo_id, actor, actor_role)`
- `LifecycleService.transition` → `audit.write("solicitud.estado_cambiado", folio, from_estado, to_estado, action, actor, actor_role)`

Both are fired **outside** the database transaction so a logging hiccup cannot roll back a committed change. The trade-off is "we may commit a state change without an audit line if logging blows up"; that is acceptable because audit is best-effort observability. Future call sites in 005 (file uploads), 007 (notifications dispatched), 008 (mentor toggles) should follow the same pattern.

## Conventions

- Event names are dotted, lowercase, past-tense (`solicitud.creada`, not `create_solicitud`).
- Field names are snake_case primitives (str, int, bool, ISO-8601 timestamps). Don't pass DTOs or model instances — they don't serialize cleanly into the log pipeline.
- One event per action, even if the action has multiple side effects. The audit line records what happened, not how.

## Tests

`_shared/tests/test_audit.py` asserts the level, the message-as-event-name, and that the kwargs land as attributes on the `LogRecord`.

## Related

- [`request_actor.md`](./request_actor.md) — the other shared infra piece introduced in 004.
- [solicitudes lifecycle/design.md](../../apps/solicitudes/lifecycle/design.md) — primary consumer.
