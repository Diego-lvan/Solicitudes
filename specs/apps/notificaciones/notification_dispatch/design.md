# `notificaciones/notification_dispatch` — Design

> HOW the email-dispatch feature is built. Long-lived reference; promoted from `planning/007-notifications/plan.md` after that initiative shipped. Update when behavior changes; do not update with implementation churn.

## Architectural shape

```
LifecycleService.transition  ─┐
IntakeService.create  ────────┼──▶  NotificationService  ──▶  RecipientResolver  ──▶  UserService.list_by_role
                              │           (port owned by    │
                              │            lifecycle)       └─▶  EmailSender  ──▶  django.core.mail
                              │
                              └──▶  notification adapter reads SolicitudDetail via LifecycleService.get_detail
```

The port `NotificationService` lives in `solicitudes/lifecycle/notification_port.py` (consumer-owned, per the cross-feature dependency rule). The concrete `DefaultNotificationService` lives here in `notificaciones/`. Wiring happens at `solicitudes/lifecycle/dependencies.py`.

`notificaciones/` owns no model, no migration, no view, no URL — it's a pure outbound integration. No `repositories/` directory exists; all "data" is read through `LifecycleService` (for solicitud detail) and `UserService` (for recipient lists).

## Layout

```
notificaciones/
├── __init__.py
├── apps.py                                   # NotificacionesConfig
├── exceptions.py                             # EmailDeliveryError (ExternalServiceError)
├── services/
│   ├── email_sender/
│   │   ├── interface.py                      # EmailSender ABC
│   │   └── smtp_implementation.py            # SmtpEmailSender (works in dev/test/prod via EMAIL_BACKEND swap)
│   ├── recipient_resolver/
│   │   ├── interface.py                      # RecipientResolver ABC
│   │   └── implementation.py                 # DefaultRecipientResolver(UserService)
│   └── notification_service/
│       └── implementation.py                 # DefaultNotificationService
└── tests/
    ├── fakes.py                              # StubRecipientResolver, RecordingEmailSender
    ├── test_email_sender.py
    ├── test_recipient_resolver.py
    ├── test_notification_service.py
    └── test_e2e_tier1.py                     # cross-feature flow against locmem outbox

templates/notificaciones/email/
├── _base.html                                # shared header/footer
├── nueva_solicitud.{html,txt}                # to responsible-role staff
├── acuse_recibo.{html,txt}                   # to solicitante on creation
└── estado_cambiado.{html,txt}                # to solicitante on transition
```

## Service contract

### `NotificationService` (port — defined by lifecycle, implemented here)

```python
class NotificationService(ABC):
    def notify_creation(self, *, folio: str, responsible_role: Role) -> None: ...
    def notify_state_change(self, *, folio: str, estado_destino: Estado,
                             observaciones: str = "") -> None: ...
```

`DefaultNotificationService.notify_creation` does:

1. Loads `SolicitudDetail` via `LifecycleService.get_detail(folio)`.
2. Resolves staff via `RecipientResolver.resolve_by_role(responsible_role)`.
3. Sends one `nueva_solicitud` email per staff recipient (subject: `"Nueva solicitud {folio}: {tipo.nombre}"`).
4. Sends one `acuse_recibo` email to `solicitud.solicitante` (subject: `"Recibimos tu solicitud {folio}"`). Step 4 fires regardless of whether step 3 produced any recipients.

`DefaultNotificationService.notify_state_change` does:

1. Loads `SolicitudDetail` via `LifecycleService.get_detail(folio)`.
2. Sends one `estado_cambiado` email to `solicitud.solicitante` (subject: `"Tu solicitud {folio} ahora está {estado}"`, body shows `observaciones` if non-empty).

Every send is wrapped in try/except. `EmailDeliveryError` is logged at WARNING (`event=email_delivery_error folio=… to=… reason=…`) and absorbed; never raised to the caller. RF-07 says SMTP outages must not block the underlying business operation.

### `RecipientResolver`

```python
class RecipientResolver(ABC):
    def resolve_by_role(self, role: Role) -> list[UserDTO]: ...
```

Default implementation wraps `UserService.list_by_role(role)`. Filtering for deliverability (non-empty email) happens inside the `UserRepository` so callers cannot accidentally re-implement the rule.

### `EmailSender`

```python
class EmailSender(ABC):
    def send(self, *, subject: str, to: str, html: str, text: str) -> None: ...
```

`SmtpEmailSender` builds an `EmailMultiAlternatives` and calls `.send(fail_silently=False)`. On `(TimeoutError, SMTPException, OSError)` raises `EmailDeliveryError`. Only one concrete implementation — Django's locmem backend reuses the same class in tests; the difference is the `EMAIL_BACKEND` setting.

## Templates

- All templates extend `_base.html` (shared header / footer).
- Inline styles only (mail clients drop `<link>` and most `<style>` rules).
- In-app links use Django's `{% url %}` reverser (`solicitudes:revision:detail` for staff, `solicitudes:intake:detail` for solicitante) prefixed with `{{ SITE_BASE_URL }}`. Hard-coded paths are not allowed — they drift with URL refactors.
- Context is injected by the dispatch service: `{solicitud, recipient?, estado_label?, observaciones?, SITE_BASE_URL}`. There is no context processor — keeping the dispatch standalone makes a future Celery move trivial.

## Wiring (`solicitudes/lifecycle/dependencies.py`)

The lifecycle service depends on `NotificationService` (to fire on transitions); the notifier depends on `LifecycleService` (to load `SolicitudDetail`). The cycle is broken at construction time:

1. Build the shared `historial` and `solicitudes` repositories (one instance each per `get_lifecycle_service()` call).
2. Build a *read-only* `DefaultLifecycleService` wired with `NoOpNotificationService`. This is the instance handed to the notifier; it never receives a `transition` call.
3. Build `DefaultNotificationService` taking the read-only lifecycle, the recipient resolver, and the SMTP sender.
4. Build the *production* `DefaultLifecycleService` taking the same shared repos and the real notifier. This is what views consume.

Both lifecycle instances share the same repository objects so reads from the notifier and writes from the production service cannot diverge.

`get_notification_service()` exposes the same wiring to consumers (`intake`, `revision`) that resolve the notifier directly.

## Exception hierarchy

| Class | Subclass of | Notes |
|---|---|---|
| `EmailDeliveryError` | `ExternalServiceError` (`_shared`) | Raised by `SmtpEmailSender` only. Never reaches a view — `DefaultNotificationService` always swallows it. The exception exists primarily as a logging hook. |

## Settings

| Var | Default | Required in prod |
|---|---|---|
| `EMAIL_BACKEND` | `locmem` (base.py) → `smtp` (dev.py, prod.py) | (set per env) |
| `EMAIL_HOST` | `mailhog` (dev) | yes (`_required`) |
| `EMAIL_PORT` | `1025` (dev) / `587` (prod) | no |
| `EMAIL_HOST_USER` | `""` | no |
| `EMAIL_HOST_PASSWORD` | `""` | no |
| `EMAIL_USE_TLS` | `False` (dev) / `True` (prod) | no |
| `EMAIL_TIMEOUT` | `10` (seconds) | no |
| `DEFAULT_FROM_EMAIL` | `no-reply@uaz.edu.mx` | yes (`_required`) |
| `SITE_BASE_URL` | `https://localhost` (dev) | yes (`_required`) |

`prod.py` calls `_required(...)` on the three "yes" rows so a misconfigured deployment fails to boot rather than silently dropping mail.

## Cross-feature contract

- The `UserService.list_by_role(role)` method is the contract surface for recipient lookup. Consumers other than `notificaciones` should not introspect `UserRepository` — see `usuarios/design.md`.
- The `SITE_BASE_URL` setting is shared with anywhere else that emits external-facing absolute URLs (currently only this feature).

## Test stack

- **Service tests** (`test_notification_service.py`) — `StubRecipientResolver` + `RecordingEmailSender` exercise the dispatch logic without DB or SMTP. Cover the staff fan-out, the acuse, per-recipient failure handling.
- **Sender test** (`test_email_sender.py`) — locmem outbox proves the `EmailMultiAlternatives` shape (HTML alternative attached, `from_email` resolved). One test patches `.send` to verify exception wrapping.
- **Resolver test** (`test_recipient_resolver.py`) — wired against the real `DefaultUserService` over `InMemoryUserRepository` to pin the role + non-empty-email contract.
- **Tier 1 cross-feature** (`test_e2e_tier1.py`) — wires the production service shape against in-memory lifecycle/historial fakes and the locmem outbox. Covers: creation fan-out + acuse, transition email, two consecutive transitions producing two distinct emails, SMTP failure does not block transition (logged + absorbed).
- **Tier 2 (browser)** — none. Email content is pure server-side.

## Coverage thresholds

| Layer | Threshold |
|---|---|
| Services | ≥ 95% line |

Currently 100% across `notification_service`, `email_sender`, `recipient_resolver`.

## Related specs

- [requirements.md](./requirements.md) — WHAT/WHY.
- [`specs/apps/solicitudes/lifecycle/design.md`](../../solicitudes/lifecycle/design.md) — `NotificationService` port (consumer side) and the construction-cycle break.
- [`specs/apps/usuarios/design.md`](../../usuarios/design.md) — `UserService.list_by_role`.
- [`specs/planning/007-notifications/`](../../../planning/007-notifications/) — initiative that shipped this.
- `.claude/rules/django-code-architect.md` — architectural law.
