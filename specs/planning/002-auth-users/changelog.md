# 002-auth-users — Auth & Users — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25
- Initiative directory created (stub)
- Plan, status, and changelog files created as drafts pending `/brainstorm` + `/plan`
- Plan filled in: custom `User` model (no password), `Role` enum, `RoleResolver` ABC + JWT impl, JWT auth middleware, `/auth/callback` handshake (Option 3), SIGA service with timeout + soft fallback, role-based mixins. Open: provider JWT transport (OQ-002-1, **pending**), whether provider's JWT carries CONTROL_ESCOLAR / RESPONSABLE_PROGRAMA roles (OQ-002-2).
