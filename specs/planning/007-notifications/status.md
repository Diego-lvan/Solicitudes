# 007 — Notifications — Status

**Status:** Done
**Last updated:** 2026-04-26

## Checklist

### App skeleton
- [x] Create `notificaciones/` package + `apps.py`
- [x] Register in `INSTALLED_APPS`

### Schemas, exceptions
- [x] [P] `notificaciones/schemas.py` (dropped — no DTO needed; service passes primitives)
- [x] [P] `notificaciones/exceptions.py` (`EmailDeliveryError`)

### Interfaces & implementations
- [x] `services/email_sender/{interface,smtp_implementation}.py` + tests (locmem outbox)
- [x] `services/recipient_resolver/{interface,implementation}.py` + tests
- [x] `services/notification_service/{interface,implementation}.py` + tests
- [x] `dependencies.py` (real wiring lives in `solicitudes/lifecycle/dependencies.py` to break the read-side cycle)

### Extend `UserService`
- [x] Add `list_by_role(role) -> list[UserDTO]` to interface + impl + tests

### Templates
- [x] [P] `templates/notificaciones/email/_base.html`
- [x] [P] `templates/notificaciones/email/nueva_solicitud.html` + `.txt`
- [x] [P] `templates/notificaciones/email/estado_cambiado.html` + `.txt`

### Replace NoOp wiring (in 004's dependencies)
- [x] [P] `solicitudes/intake/dependencies.py` (no edit needed — already imports `get_notification_service` from lifecycle; auto-picks up real impl)
- [x] [P] `solicitudes/revision/dependencies.py` (no edit needed — same)
- [x] [P] `solicitudes/lifecycle/dependencies.py` (real `DefaultNotificationService`, with read-only lifecycle for the notifier to break the wiring cycle)

### Settings
- [x] Verify env vars in `.env.example`: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_TIMEOUT`, `DEFAULT_FROM_EMAIL`, `SITE_BASE_URL`
- [x] `prod.py` fails fast if missing (`EMAIL_HOST`, `DEFAULT_FROM_EMAIL`, `SITE_BASE_URL` now `_required(...)`; `EMAIL_TIMEOUT` defaults to 10s)

### End-to-end smoke
- [x] Alumno creates → `mail.outbox` length = N (one per CONTROL_ESCOLAR user)
- [x] Personal finalizes → `mail.outbox` has one email to solicitante
- [x] Patch SMTP to raise → transition still succeeds; outbox empty; log line with `event=email_delivery_error`

### Quality gates
- [x] `ruff` + `mypy` clean
- [x] `pytest` green; coverage 100% for `notification_service` (overall notificaciones 100% post-removal of unused `schemas.py`)


### E2E
- [x] Tier 1: cross-feature state transition emits one email to solicitante; two transitions produce two distinct emails; SMTP failure does not block transition.

## Blockers

None. Closed out — see `/review` notes in `changelog.md`.

## Legend

- `[P]` = parallelizable with siblings in the same section
