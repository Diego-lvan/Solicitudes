# `notificaciones/notification_dispatch` — Requirements

> WHAT the email-notification feature does, and WHY. No implementation details.

## Purpose

Keep stakeholders informed of solicitud lifecycle events by email, without making delivery a hard dependency of the underlying business operation.

## Scope

In:

- Email to the responsible-role staff when a new solicitud is created.
- Acuse de recibo (receipt confirmation) to the solicitante when their solicitud is created.
- Email to the solicitante on every state transition (atender, finalizar, cancelar).
- HTML body with plain-text alternative; subjects in Spanish.

Out (deferred):

- In-app notifications, push, SMS.
- Per-user notification preferences (opt-out, digest, frequency).
- Throttling or batch digests.
- i18n beyond Spanish.
- Asynchronous dispatch (Celery / queue).

## Behavior

| Event | Recipients | Subject form |
|---|---|---|
| Solicitud created | All users with `tipo.responsible_role` (filtered to non-empty email) | "Nueva solicitud `{folio}`: `{tipo.nombre}`" |
| Solicitud created (acuse) | Solicitante | "Recibimos tu solicitud `{folio}`" |
| State change (any transition) | Solicitante | "Tu solicitud `{folio}` ahora está `{estado}`" |

Each email body links to the relevant in-app page (revision queue for staff, intake detail for the solicitante).

## Non-functional requirements

- **Best-effort delivery.** SMTP failures (timeout, connection refused, server error) MUST NOT propagate to the caller — the underlying state change is what's observable. Failures are logged at WARNING level with a structured event marker so operators can audit dropped messages.
- **One transport.** A single sender abstraction backs dev (Mailhog), tests (locmem outbox), and prod (real SMTP). Behavior is identical across environments; the difference is in the Django backend setting.
- **Synchronous.** Mail is sent inline with the request that triggered it. Acceptable because of low message volume and the best-effort failure policy. If volume grows, this becomes the migration boundary to Celery.
- **No model.** No DB table is owned by this app — it's a pure outbound integration.

## Acceptance criteria

- Creating a solicitud results in `N + 1` emails: one per active staff member with the responsible role, plus one acuse to the solicitante. If no staff exist for the role, the acuse still fires.
- Each lifecycle transition results in exactly one email to the solicitante.
- A patched-failing SMTP transport leaves the database state intact (transition succeeded), the outbox empty (or partially filled — the rest is silently dropped), and a WARNING log line carrying `event=email_delivery_error`, the folio, and the failed recipient.
- HTML and plain-text alternatives both populated; both reference the folio; in-app link resolves to the correct path even when URLs are renamed (the implementation must reverse, not hard-code).
- Coverage for the dispatch service and its collaborators is ≥ 95%.

## Constraints

- Recipient resolution goes through `usuarios.UserService` (interface). Email is treated as the deliverability gate — empty `email` filters the recipient out.
- Subject and body strings are in Spanish only.
- Sender address comes from `DEFAULT_FROM_EMAIL`; required at boot in production.
- Body links use `SITE_BASE_URL` as their host; required at boot in production.

## Open Questions (deferred)

- **OQ-007-1** — Throttling / digest. Default is "send all"; revisit if volume becomes noisy.
- **OQ-007-2** — Per-user notification preferences. Resolver interface is shaped to absorb this without breaking callers.
- **OQ-007-3** — i18n. Spanish is the only currently-supported locale.

## Related specs

- `specs/global/requirements.md` § RF-07 — the contract this feature implements.
- `specs/apps/notificaciones/notification_dispatch/design.md` — HOW.
- `specs/apps/solicitudes/lifecycle/design.md` — `NotificationService` outbound port (consumer side).
- `specs/planning/007-notifications/` — initiative that shipped this.
