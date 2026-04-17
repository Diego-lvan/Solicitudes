# 007-notifications — Notifications — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25
- Initiative directory created (stub)
- Plan, status, and changelog files created as drafts pending `/brainstorm` + `/plan`
- Plan filled in: synchronous email send with try/except (Celery deferred), `NotificationService` ABC matching 004's hook signature, `RecipientResolver` ABC consuming a new `UserService.list_by_role`, HTML+text templates. Replaces 004's `NoOpNotificationService` wiring.
