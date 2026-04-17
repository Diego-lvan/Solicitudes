# 007 — Notifications

## Summary

Synchronous email dispatch on solicitud creation and on every state transition. SMTP failures are swallowed and logged — they never block the underlying state change. Two recipient flows: (a) on creation, email all users with the responsible role; (b) on state change, email the solicitante. Templates are HTML-with-text-fallback Django templates living under `templates/notificaciones/email/`. No queueing, no Celery — RF-07 is the contract, low user volume justifies the simplicity.

## Depends on

- **001** — `_shared/exceptions.py`, logging
- **002** — `UserService` (recipient resolution by role and matricula)
- **004** — `SolicitudDetail`, transition hooks (currently calling `NoOpNotificationService`)

## Affected Apps / Modules

- `notificaciones/` — new app
- `solicitudes/intake/dependencies.py`, `solicitudes/lifecycle/dependencies.py`, `solicitudes/revision/dependencies.py` — replace NoOp with the real service

## References

- [global/requirements.md](../../global/requirements.md) — RF-07
- 004 plan, OQ-004-1 — interface signature

## Implementation Details

### Layout

```
notificaciones/
├── __init__.py
├── apps.py
├── exceptions.py
├── schemas.py
├── dependencies.py
├── services/
│   ├── notification_service/{interface,implementation}.py
│   ├── recipient_resolver/{interface,implementation}.py
│   └── email_sender/{interface,smtp_implementation,locmem_implementation}.py
└── tests/
templates/notificaciones/email/
├── _base.html               # consistent header/footer
├── nueva_solicitud.html     # to responsible-role recipients
├── nueva_solicitud.txt
├── estado_cambiado.html     # to solicitante
└── estado_cambiado.txt
```

### Interface (matches 004's expectation)

```python
class NotificationService(ABC):
    @abstractmethod
    def notify_creation(self, *, folio: str, responsible_role: Role) -> None: ...
    @abstractmethod
    def notify_state_change(self, *, folio: str, estado_destino: Estado, observaciones: str) -> None: ...
```

Default implementation (`DefaultNotificationService`):

`notify_creation(folio, responsible_role)`:
1. `solicitud = lifecycle_service.get_detail(folio)`
2. `recipients = recipient_resolver.resolve_by_role(responsible_role)` → `list[UserDTO]` filtered to `email != ""`
3. For each recipient: render `nueva_solicitud.{html,txt}` with `{solicitud, recipient}` context, send via `email_sender.send(...)`. Each send is wrapped in try/except — log warning on failure, continue with the next.

`notify_state_change(folio, estado_destino, observaciones)`:
1. `solicitud = lifecycle_service.get_detail(folio)`
2. Recipient is `solicitud.solicitante`; render `estado_cambiado.{html,txt}` with `{solicitud, observaciones}`.
3. Try/except SMTP, log on failure.

### Recipient resolver

```python
class RecipientResolver(ABC):
    @abstractmethod
    def resolve_by_role(self, role: Role) -> list[UserDTO]: ...
```

`DefaultRecipientResolver` queries `UserService.list_by_role(role)`. We add a `list_by_role(role) -> list[UserDTO]` method to `UserService` in 007 (small extension to 002's interface — backward compatible). Filter out users with empty `email`.

### Email sender

```python
class EmailSender(ABC):
    @abstractmethod
    def send(self, *, subject: str, to: str, html: str, text: str) -> None: ...   # raises EmailDeliveryError
```

- `SmtpEmailSender` uses `django.core.mail.EmailMultiAlternatives` (which uses settings' `EMAIL_BACKEND`). On failure (`SMTPException`, `socket.timeout`, etc.) raises `EmailDeliveryError`.
- `LocmemEmailSender` is just `SmtpEmailSender` — Django's `locmem` backend captures into `mail.outbox`. Tests assert on `outbox`. We don't actually need a separate impl; the difference is in settings.

### Schemas / exceptions

```python
class EmailDeliveryError(ExternalServiceError):
    code = "email_delivery_error"
    user_message = "No fue posible enviar el correo de notificación."
```

The exception is **never raised to the caller** (`DefaultNotificationService` always swallows). It's a logging hook.

### Settings

| Var | Notes |
|---|---|
| `EMAIL_BACKEND` | `locmem` in tests, **SMTP in dev (Mailhog at host `mailhog:1025`, see 001 dev compose)**, SMTP in prod |
| `DEFAULT_FROM_EMAIL` | `no-reply@uaz.edu.mx` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | from env (already in 001's `.env.example`); `dev.py` defaults to `mailhog:1025`, no auth, no TLS |
| `EMAIL_TIMEOUT` | default 10 seconds |
| `SITE_BASE_URL` | base URL for email links; `https://localhost` in dev (through nginx), real host in prod |

### Templates

Subjects (Spanish, short, action-driven):
- nueva-solicitud: `"Nueva solicitud {{ folio }}: {{ tipo_nombre }}"`
- estado-cambiado: `"Tu solicitud {{ folio }} ahora está {{ estado }}"`

Bodies link to `https://{HOST}/revision/{folio}/` (personal) or `https://{HOST}/solicitudes/{folio}/` (solicitante). Host comes from `settings.SITE_BASE_URL`.

### Wire-up

`solicitudes/{intake,revision,lifecycle}/dependencies.py` replace:

```python
def get_notification_service() -> NotificationService:
    return NoOpNotificationService()
```

with:

```python
def get_notification_service() -> NotificationService:
    return DefaultNotificationService(
        recipient_resolver=DefaultRecipientResolver(user_service=usuarios_dependencies.get_user_service()),
        lifecycle_service=lifecycle_dependencies.get_lifecycle_service(),
        email_sender=SmtpEmailSender(),
        logger=logging.getLogger("notificaciones"),
    )
```

To avoid a circular import (lifecycle calls notifications, notifications reads solicitud detail through lifecycle), `DefaultNotificationService` accepts `LifecycleService` as a constructor dependency — wired at app boot in `dependencies.py`. No module-level cycles because `dependencies.py` imports happen lazily.

### Sequencing

1. `notificaciones/` skeleton.
2. Schemas, exceptions.
3. Interfaces (NotificationService, RecipientResolver, EmailSender).
4. Implementations + tests with locmem outbox.
5. Templates (.html + .txt).
6. Add `UserService.list_by_role` (002 extension) + tests.
7. Replace NoOp wiring in 004's three `dependencies.py` files.
8. End-to-end: alumno creates → outbox has N emails (one per CONTROL_ESCOLAR user). Personal finalizes → outbox has one email to alumno.


## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)
- Cross-feature: state transition triggers an email; `mail.outbox` receives one message with the correct recipient and subject. Idempotency: two transitions in a row do not duplicate.

### Browser (Tier 2 — `pytest-playwright`)
- _None — email content tested via outbox (Tier 1)._

## Acceptance Criteria

- [ ] Creating a solicitud emits one email per active user with `tipo.responsible_role`.
- [ ] Each transition emits one email to the solicitante.
- [ ] If `EMAIL_HOST` is unreachable (mocked timeout), the transition still succeeds; a `WARNING` log carries `event=email_delivery_error`, `folio=…`, `request_id=…`.
- [ ] Tests assert email counts via `mail.outbox`; subjects in Spanish; HTML and text alternatives both populated.
- [ ] No code path raises `EmailDeliveryError` to a view.
- [ ] Coverage: services ≥ 95%; templates rendered in tests (assert key context keys present).

## Open Questions

- **OQ-007-1** — Throttling / digest: emailing every CONTROL_ESCOLAR on every creation could be noisy. Default for v1: send all. If volumes grow, add a per-recipient throttle or batch digest.
- **OQ-007-2** — Per-user notification preferences (RF-07 doesn't ask for them, architecture.md mentions). Defer to a future initiative; the resolver interface absorbs the change.
- **OQ-007-3** — i18n: subjects and bodies are hard-coded in Spanish; if other languages ever appear, switch to Django's gettext.
