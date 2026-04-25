# `usuarios` — Requirements

> WHAT this app does and WHY. No implementation details.

## Purpose

Provide identity and authorization for the Sistema de Solicitudes. Authentication is **delegated to an external provider** (RNF-01); this app validates tokens issued by that provider, materializes a user record, and exposes role-based access control to the rest of the system.

## In scope

- **JWT validation** on every request, with anonymous users allowed through to the view layer (views decide whether to require auth).
- **A custom `User` model** keyed by `matricula` — no passwords, no `username`. Cached fields for SIGA-sourced data (`full_name`, `programa`, `semestre`, `gender`).
- **Role taxonomy** — `ALUMNO`, `DOCENTE`, `CONTROL_ESCOLAR`, `RESPONSABLE_PROGRAMA`, `ADMIN` — and role-resolution from provider claims.
- **SIGA enrichment** — best-effort, asynchronous-from-the-user's-POV fetch of academic profile fields. SIGA outages must never block login.
- **Session cookie management** — set on callback, cleared on logout, validated on every protected request.
- **Permission mixins** — declarative role gates for views (`AlumnoRequiredMixin`, `DocenteRequiredMixin`, `PersonalRequiredMixin`, `AdminRequiredMixin`, plus the underlying `LoginRequiredMixin` and `RoleRequiredMixin`).

## Out of scope

- Issuing tokens. The external provider does that.
- Password storage, password reset, MFA. The provider owns the credential layer.
- Self-service user signup. Users are upserted from validated provider claims.
- Full SIGA mirror. We cache only fields needed for display; everything else is fetched on demand if/when a feature requires it.
- Mentor catalog and mentor-status determination. That's `mentores/` (initiative 008).

## Functional requirements

| ID | Requirement | Source |
|---|---|---|
| RF-USR-01 | A request with a valid JWT must populate `request.user` (Django auth contract) and `request.user_dto` (typed Pydantic DTO). | RNF-01 |
| RF-USR-02 | A request with no token must allow the request through with `request.user = AnonymousUser`; views decide whether to require auth. | architecture.md |
| RF-USR-03 | A request with an invalid or expired JWT must redirect to the provider login URL. | RNF-01 |
| RF-USR-04 | Hitting `/auth/callback?token=…&return=…` must validate the token, persist the user, set the session cookie, and redirect to a safe `return` URL — same-host or relative paths only. Off-host targets must fall back to a safe default to prevent open-redirect attacks. | global/architecture.md |
| RF-USR-05 | Hitting `/auth/logout` must clear the session cookie and redirect to the provider's logout URL (or `/` if none configured), regardless of whether the cookie is valid. | architecture.md |
| RF-USR-06 | Hitting `/auth/me` while authenticated must render the user's profile from the typed DTO. | plan.md (debug aid that doubles as integration check) |
| RF-USR-07 | A user whose role is not in a view's `required_roles` set must be denied with HTTP 403 and the standard error template. | RNF-06 |
| RF-USR-08 | SIGA outages (timeout, connection error, 5xx, malformed payload) must not prevent login. The user's cached fields are kept; new login proceeds. | RNF-02 |

## Non-functional requirements

- **No password storage.** The model has no `set_password` path, and the manager rejects `create_user`/`create_superuser`.
- **The auth provider owns email.** SIGA enriches `full_name`, `programa`, `semestre`, `gender` only. SIGA's `email` is never persisted.
- **Cached SIGA fields are sticky.** A subsequent JWT-only login (no SIGA data) must not clobber a previously cached `full_name`/`programa`/`semestre`/`gender`.
- **Gender is normalised at the DTO boundary.** SIGA's single-letter code is coerced to `"H"` / `"M"` / `""` by a Pydantic validator on `UserDTO`/`SigaProfile`/`CreateOrUpdateUserInput`; any unknown value (`"F"`, `"X"`, full words, non-strings) collapses to `""`. PDF plantillas branching on `solicitante.genero` therefore never see garbage. Added by initiative 011 alongside the auto-fill plumbing.
- **Provider role vocabulary is isolated.** Changes to the provider's role strings are absorbed in one place (`PROVIDER_ROLE_MAP` + the `RoleResolver` ABC), never rippled through the codebase.
- **Production fail-fast.** `JWT_SECRET`, `AUTH_PROVIDER_LOGIN_URL`, and `SIGA_BASE_URL` are required at boot in `prod.py`.

## Open questions (carried forward)

- **OQ-002-1** (transport) — the provider team has not yet confirmed JWT transport. The current implementation assumes redirect to `/auth/callback?token=…` and a server-set HttpOnly cookie. Tracked in initiative **010**.
- **OQ-002-2** (personal roles) — does the provider's JWT carry `CONTROL_ESCOLAR`/`RESPONSABLE_PROGRAMA`? If not, a `DirectoryRoleResolver` backed by an admin-managed mapping table will be added — the `RoleResolver` ABC already absorbs the change.
- **OQ-002-3** (refresh) — does the provider issue short-lived tokens? If yes, a refresh flow lands in 010.
- **OQ-002-4** (deactivation) — provider-side revocations only take effect on the next failed JWT check today. Acceptable for v1.
- **OQ-002-5** (SIGA shape per role) — `SigaProfile` is alumno-shaped today (`matricula`, `email`, `full_name`, `programa`, `semestre`). The SIGA team has not confirmed whether docente / control escolar profiles share the schema or expose distinct fields (`departamento`, `categoria`, `materias`, etc.). Action when answered: extend `SigaProfile` with the new fields (additive — existing optional fields stay), and any feature that surfaces docente data extends its consumers (e.g., initiative 011's `FieldSource` enum gains `USER_DEPARTAMENTO`). Until confirmed, the system degrades gracefully because all academic fields on `UserDTO` are optional. Cross-referenced from initiative 011 as **OQ-011-2**.

## Related Specs

- [design.md](./design.md) — HOW.
- [`specs/flows/external-login.md`](../../flows/external-login.md) — end-to-end sequence.
- [`specs/planning/002-auth-users/plan.md`](../../planning/002-auth-users/plan.md) — initiative that shipped this.
- [`specs/planning/010-external-auth-provider/plan.md`](../../planning/010-external-auth-provider/plan.md) — provider integration follow-up.
