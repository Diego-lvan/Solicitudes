# Flow — External Login

> **Status:** v1 (interim — uses the DEBUG-only dev-login picker).
> **Owners:** `usuarios`. Initiative **010** replaces the entry point with the real provider handshake; the rest of the flow stays the same.

This flow describes how a request goes from "unauthenticated user wants to use the app" to "`request.user_dto` is populated and a protected view renders". It crosses three components that all live in `usuarios/`: the entry point (dev-login or future provider), the callback handshake, and the JWT auth middleware.

## Sequence (current — initiative 002)

```
┌────────┐         ┌──────────────────┐    ┌───────────────────┐    ┌──────────────────────┐    ┌──────────────────┐
│ Browser│         │ /auth/dev-login  │    │  /auth/callback   │    │  JwtAuthMiddleware   │    │  Protected view  │
│        │         │  (DEBUG only)    │    │  (CallbackView)   │    │                      │    │  e.g. /auth/me   │
└───┬────┘         └────────┬─────────┘    └─────────┬─────────┘    └──────────┬───────────┘    └────────┬─────────┘
    │ GET                   │                        │                          │                         │
    │ /auth/dev-login       │                        │                          │                         │
    │──────────────────────▶│                        │                          │                         │
    │                       │ list_all() via repo    │                          │                         │
    │ render picker         │                        │                          │                         │
    │◀──────────────────────│                        │                          │                         │
    │                       │                        │                          │                         │
    │ POST {action,role}    │                        │                          │                         │
    │──────────────────────▶│                        │                          │                         │
    │                       │ upsert user            │                          │                         │
    │                       │ mint JWT               │                          │                         │
    │                       │ 302 to /auth/callback  │                          │                         │
    │                       │  ?token=…&return=…     │                          │                         │
    │◀──────────────────────│                        │                          │                         │
    │                       │                        │                          │                         │
    │ GET /auth/callback    │                        │                          │                         │
    │──────────────────────────────────────────────▶│                          │                         │
    │                       │                        │ decode_jwt → claims      │                         │
    │                       │                        │ user_service.get_or_     │                         │
    │                       │                        │   create_from_claims     │                         │
    │                       │                        │ user_service.hydrate_    │                         │
    │                       │                        │   from_siga (best-effort)│                         │
    │                       │                        │ Set-Cookie: stk=…        │                         │
    │                       │                        │ 302 to <return>          │                         │
    │◀──────────────────────────────────────────────│                          │                         │
    │                       │                        │                          │                         │
    │ GET /auth/me          │                        │                          │                         │
    │ (Cookie: stk=…)       │                        │                          │                         │
    │──────────────────────────────────────────────────────────────────────────▶│                         │
    │                       │                        │                          │ read cookie             │
    │                       │                        │                          │ decode_jwt → claims     │
    │                       │                        │                          │ user_service.get_or_    │
    │                       │                        │                          │   create_from_claims    │
    │                       │                        │                          │ User.objects.get(pk=…)  │
    │                       │                        │                          │ request.user = orm_user │
    │                       │                        │                          │ request.user_dto = dto  │
    │                       │                        │                          │ ──────────────────────▶│
    │                       │                        │                          │                         │ render usuarios/me.html
    │ 200 + HTML            │                        │                          │                         │
    │◀──────────────────────────────────────────────────────────────────────────────────────────────────│
```

## Actors

| Component | Source | Responsibility |
|---|---|---|
| Browser | n/a | Carries the `stk` cookie on every subsequent request. |
| `/auth/dev-login` | `usuarios/views/dev_login.py` (DEBUG only) | Picker for development. Mints a JWT server-side using the production `JWT_SECRET`/`JWT_ALGORITHM` and rides through `/auth/callback`. **Removed in initiative 010.** |
| `/auth/callback` | `usuarios/views/callback.py` | Validates the token, upserts the user, best-effort SIGA hydration, sets the `stk` HttpOnly cookie with `max_age = exp − now`, redirects to the validated `return` URL (or `/solicitudes/`). Always present — initiative 010 keeps this view; only the *upstream* changes. |
| `JwtAuthenticationMiddleware` | `usuarios/middleware.py` | On every request that doesn't match `SKIP_PREFIXES`: read cookie or `Authorization: Bearer`, decode, upsert via `UserService`, set `request.user` (ORM `User`) and `request.user_dto` (typed `UserDTO`). Catches `AuthenticationRequired` inline and redirects to `settings.LOGIN_URL`. |
| `UserService.get_or_create_from_claims` | `usuarios/services/user_service/implementation.py` | Resolves role via `RoleResolver`, upserts via `UserRepository`, stamps `last_login_at`. |
| `UserService.hydrate_from_siga` | same | Best-effort SIGA enrichment. Swallows `SigaUnavailable` and returns the cached DTO unchanged. |

## Step-by-step (cookie-bearing protected request — what every authenticated request does)

1. Browser sends `GET /auth/me` with `Cookie: stk=<jwt>`.
2. `JwtAuthenticationMiddleware.__call__`:
   - `_should_skip("/auth/me")` → `False` (not in `SKIP_PREFIXES`).
   - `_read_token(request)` → returns the cookie value.
   - `decode_jwt(token, secret=settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])` → either returns claims dict or raises `AuthenticationRequired` (via `_shared.auth`).
   - `parse_claims(payload)` → `JwtClaims(sub, email, rol, exp, iat)`.
   - `user_service.get_or_create_from_claims(claims)` → `UserDTO`.
   - `User.objects.get(pk=user_dto.matricula)` → ORM instance for `request.user` (the only sanctioned ORM read outside a repository — required by Django's auth contract).
   - Set `request.user = orm_user`, `request.user_dto = user_dto`.
3. View runs (e.g. `MeView.dispatch` → `LoginRequiredMixin` confirms `request.user.is_authenticated` → `MeView.get` renders `usuarios/me.html` with `user=request.user_dto`).

## Failure modes

| Trigger | Detected by | Outcome |
|---|---|---|
| No token (anonymous, not in skip path) | Middleware | `request.user = AnonymousUser`; downstream `LoginRequiredMixin` raises `AuthenticationRequired` → `AppErrorMiddleware` redirects to `LOGIN_URL`. |
| Invalid signature / malformed JWT | `_shared.auth.decode_jwt` | Raises `AuthenticationRequired`; middleware catches inline and redirects to `LOGIN_URL`. |
| Expired JWT | same | same. |
| Provider role unknown | `JwtRoleResolver.resolve` | Raises `RoleNotRecognized` (a 403 `Unauthorized` subclass); middleware lets it propagate; `AppErrorMiddleware` renders `_shared/error.html` with status 403. |
| SIGA timeout / 5xx / connection error | `HttpSigaService.fetch_profile` | Raises `SigaUnavailable`; `UserService.hydrate_from_siga` swallows and logs — login still succeeds with cached profile. |
| User row vanished between upsert and `User.objects.get` | Middleware | Logs `auth.user_vanished`; raises `InvalidJwt` → caught inline → redirect to `LOGIN_URL`. |
| Off-host `return` URL on `/auth/callback` | `CallbackView._safe_return_url` | Returns `/`; the redirect lands on root. Open-redirect attacks via the `return` query param are not possible. |

## Skip paths (`JwtAuthenticationMiddleware.SKIP_PREFIXES`)

| Path prefix | Why |
|---|---|
| `/health/` | Liveness/readiness probes — no auth. |
| `/static/`, `/media/` | Asset serving. |
| `/auth/callback` | The handshake endpoint that *issues* the cookie; it validates the token itself. |
| `/auth/logout` | Must work even with a stale or invalid cookie. |
| `/auth/dev-login` | DEBUG-only picker; route is unmounted in production. |

## Cookie shape

| Attribute | Value | Source |
|---|---|---|
| Name | `stk` | `usuarios.constants.SESSION_COOKIE_NAME` |
| HttpOnly | `True` | hardcoded in `CallbackView` |
| Secure | `settings.SESSION_COOKIE_SECURE` (`True` in prod) | `prod.py` |
| SameSite | `Lax` | hardcoded in `CallbackView` |
| `max_age` | `exp − now()` (seconds) | computed from claims |

## What changes in initiative 010

- The entry point: `/auth/dev-login` is deleted. The provider redirects directly to `/auth/callback?token=…` (Option 3) **or** sets the cookie itself (Option a) **or** emits a `Bearer` header (Option b) — TBD by OQ-002-1. Whichever shape lands, the rest of this flow (callback → middleware → `request.user_dto`) is unchanged.
- The `SKIP_PREFIXES` entry for `/auth/dev-login` is removed.
- Possibly `JwtAuthenticationMiddleware._read_token` adjusts to the chosen transport (e.g. drops the cookie path or the Bearer path).

## Related Specs

- [`specs/apps/usuarios/requirements.md`](../apps/usuarios/requirements.md) — what the auth layer must do.
- [`specs/apps/usuarios/design.md`](../apps/usuarios/design.md) — how it does it (long-lived reference).
- [`specs/planning/002-auth-users/plan.md`](../planning/002-auth-users/plan.md) — the initiative that built this.
- [`specs/planning/010-external-auth-provider/plan.md`](../planning/010-external-auth-provider/plan.md) — the initiative that swaps the entry point.
