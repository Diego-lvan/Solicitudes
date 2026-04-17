# 007 — Notifications — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

### App skeleton
- [ ] Create `apps/notificaciones/` package + `apps.py`
- [ ] Register in `INSTALLED_APPS`

### Schemas, exceptions
- [ ] [P] `notificaciones/schemas.py`
- [ ] [P] `notificaciones/exceptions.py` (`EmailDeliveryError`)

### Interfaces & implementations
- [ ] `services/email_sender/{interface,smtp_implementation}.py` + tests (locmem outbox)
- [ ] `services/recipient_resolver/{interface,implementation}.py` + tests
- [ ] `services/notification_service/{interface,implementation}.py` + tests
- [ ] `dependencies.py`

### Extend `UserService`
- [ ] Add `list_by_role(role) -> list[UserDTO]` to interface + impl + tests

### Templates
- [ ] [P] `templates/notificaciones/email/_base.html`
- [ ] [P] `templates/notificaciones/email/nueva_solicitud.html` + `.txt`
- [ ] [P] `templates/notificaciones/email/estado_cambiado.html` + `.txt`

### Replace NoOp wiring (in 004's dependencies)
- [ ] [P] `apps/solicitudes/intake/dependencies.py`
- [ ] [P] `apps/solicitudes/revision/dependencies.py`
- [ ] [P] `apps/solicitudes/lifecycle/dependencies.py`

### Settings
- [ ] Verify env vars in `.env.example`: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`, `SITE_BASE_URL`
- [ ] `prod.py` fails fast if missing

### End-to-end smoke
- [ ] Alumno creates → `mail.outbox` length = N (number of active CONTROL_ESCOLAR users)
- [ ] Personal finalizes → `mail.outbox` has one email to solicitante
- [ ] Patch SMTP to raise → transition still succeeds; outbox empty; log line with `event=email_delivery_error`

### Quality gates
- [ ] `ruff` + `mypy` clean
- [ ] `pytest` green; coverage ≥ 95% for service


### E2E
- [ ] Tier 1 (Client multi-step): Cross-feature: state transition triggers an email; `mail.outbox` receives one message with the correct recipient and subject. Idempotency: two transitions in a row do not duplicate.

## Blockers

None (depends on 002 + 004).

## Legend

- `[P]` = parallelizable with siblings in the same section
