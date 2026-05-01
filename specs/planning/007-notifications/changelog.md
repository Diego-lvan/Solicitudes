# 007-notifications — Notifications — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25
- Initiative directory created (stub)
- Plan, status, and changelog files created as drafts pending `/brainstorm` + `/plan`
- Plan filled in: synchronous email send with try/except (Celery deferred), `NotificationService` ABC matching 004's hook signature, `RecipientResolver` ABC consuming a new `UserService.list_by_role`, HTML+text templates. Replaces 004's `NoOpNotificationService` wiring.

## 2026-04-26
- Implemented full initiative inside isolated worktree `.claude/worktrees/007-notifications` with parallel dev stack (`COMPOSE_PROJECT_NAME=solicitudes007`, nginx 8082/8446).
- `notificaciones/` app added: `apps.py`, `exceptions.py` (`EmailDeliveryError`), `services/email_sender/{interface,smtp_implementation}.py`, `services/recipient_resolver/{interface,implementation}.py`, `services/notification_service/{interface,implementation}.py`, in-memory test fakes.
- `UserService.list_by_role(role)` added across interface + ORM impl + in-memory fake; filters non-empty email; tests cover role filter, empty-email exclusion, and empty-result path.
- `DefaultNotificationService` reads `SolicitudDetail` via the existing `LifecycleService` interface; `notify_creation` fans out per recipient and swallows per-recipient `EmailDeliveryError`; `notify_state_change` emails the solicitante on every transition (incl. self-cancel, per OQ-007 decision).
- Email templates `_base.html`, `nueva_solicitud.{html,txt}`, `estado_cambiado.{html,txt}` under `templates/notificaciones/email/`. `SITE_BASE_URL` injected by the service into the render context (no global processor).
- Wiring: `lifecycle/dependencies.py` builds two `LifecycleService` instances — a read-only one (with `NoOpNotificationService`) consumed by `DefaultNotificationService`, and the real one used by views — to break the wiring cycle without introducing a new narrow port. `intake/dependencies.py` and `revision/dependencies.py` needed no edits because they already pulled `get_notification_service` from lifecycle.
- Settings: `prod.py` now `_required("EMAIL_HOST")`, `_required("DEFAULT_FROM_EMAIL")`, `_required("SITE_BASE_URL")`; `EMAIL_TIMEOUT` default 10s; `.env.example` updated.
- Tests: 466 pytest passing (8 e2e Tier 2 deselected — unchanged Playwright suite). Notificaciones-only coverage: `notification_service` 100%, `email_sender` 100%, `recipient_resolver` 100%. Tier 1 cross-feature suite (`notificaciones/tests/test_e2e_tier1.py`) covers: creation fan-out, transition email to solicitante, two consecutive transitions, SMTP-failure pass-through with `event=email_delivery_error` log line. Ruff + mypy clean.
- Roadmap flipped to `In Progress`.
- Code-reviewer agent dispatched against the full diff. Three Important items addressed:
  1. Tier 1 `notify_creation` test no longer reaches into `lifecycle._notifier` with a `# type: ignore`; `_build()` now returns the notifier alongside the lifecycle and solicitudes repo, and the test calls `notifier.notify_creation` on a typed handle.
  2. `lifecycle/dependencies.py` rewired so the read-side and write-side `LifecycleService` instances share the *same* `historial` and `solicitudes` repository objects — repeated `get_lifecycle_service()` calls no longer build four divergent repos. The `_get_readonly_lifecycle_service` helper was inlined and `get_notification_service` rebuilt to mirror the same shape (used by intake/revision callers that resolve the notifier directly).
  3. Lazy imports inside `get_notification_service` removed. There is no real cycle (`notificaciones.*` only imports leaf modules from `lifecycle`), so `notificaciones.services.*` is now imported at module top and the misleading "one-directional at import resolution" comment is gone.
- Suggestion picked up: `test_email_sender.py` patch target now spelled `"django.core.mail.EmailMultiAlternatives.send"` instead of the `__import__("django.core.mail", ...)` indirection. The `_ESTADO_LABELS` promotion suggestion was deferred (no second consumer yet); the `docker-compose.override.yml` worktree-only file was kept as-is because it follows the same pattern already shipped on `main` for initiative 009.
- Re-verification after fixes: `ruff check .` clean, `mypy` clean, `pytest -m "not e2e"` → 467 passed.
