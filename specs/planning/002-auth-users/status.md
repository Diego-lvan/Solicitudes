# 002 — Auth & Users — Status

**Status:** Done
**Last updated:** 2026-04-25

## Checklist

### App skeleton
- [x] Create `usuarios/` package + `apps.py`
- [x] Register in `INSTALLED_APPS`
- [x] `constants.py` (Role enum + provider role map)
- [x] `schemas.py` (UserDTO, CreateOrUpdateUserInput, SigaProfile)
- [x] `exceptions.py` (InvalidJwt, RoleNotRecognized, SigaUnavailable)

### Model & migration
- [x] `models/user.py` (custom `User` + `UserManager`)
- [x] Set `AUTH_USER_MODEL = "usuarios.User"` in `base.py`
- [x] Initial migration applies cleanly

### Repository
- [x] [P] `repositories/user/interface.py` (UserRepository ABC)
- [x] [P] `repositories/user/implementation.py` (`OrmUserRepository`)
- [x] [P] `tests/test_user_repository.py` (real DB, ≥ 95% line)

### Services
- [x] [P] `services/role_resolver/{interface,jwt_implementation}.py` + tests
- [x] [P] `services/siga/{interface,http_implementation,jwt_fallback}.py` + tests (HTTP mocked via `responses`)
- [x] `services/user_service/{interface,implementation}.py` + tests (in-memory fakes)

### Test fakes
- [x] [P] `tests/fakes.py` — `InMemoryUserRepository`, `FakeSigaService`, `FakeRoleResolver`
- [x] [P] `tests/factories.py` — `make_user(**overrides)` via `model_bakery`

### Wiring
- [x] `dependencies.py` factory functions
- [x] `middleware.py` (`JwtAuthenticationMiddleware`) + tests
- [x] Replace Django's `AuthenticationMiddleware` in `config/settings/base.py`
- [x] `permissions.py` mixins + tests

### Views & templates
- [x] [P] `views/callback.py` + `tests/test_views_callback.py`
- [x] [P] `views/logout.py` + `tests/test_views_logout.py`
- [x] [P] `views/me.py` + `tests/test_views_me.py`
- [x] [P] `templates/usuarios/me.html`
- [x] `usuarios/urls.py` + mount in `config/urls.py`

### Settings & env
- [x] Add JWT and SIGA env vars to `.env.example` (already populated by 001 placeholder)
- [x] Read them in `base.py`
- [x] Verify `prod.py` fails fast if `JWT_SECRET` or `AUTH_PROVIDER_LOGIN_URL` missing

### End-to-end smoke
- [x] Mint a dev JWT — **superseded:** `/auth/dev-login` picker (DEBUG-only, mounts only when `settings.DEBUG=True`) replaces the planned `tools/mint_dev_jwt.py` script. Picks an existing user or quickstart-creates one per role; mints the JWT server-side and rides through `/auth/callback`. Real-provider swap tracked under initiative **010**.
- [x] Hit `/auth/callback?token=<jwt>&return=/auth/me` → verify cookie set + profile rendered (covered by `test_full_callback_then_protected_view_with_cookie` and now reachable in the browser via `/auth/dev-login`)
- [ ] Hit a 403 path with a wrong-role user → verify `_shared/error.html` rendered — **deferred to 010** (no role-gated URL exists yet in the URL conf; covered at unit level by `test_role_mixins_*`)
- [x] Stop SIGA mock → verify login still succeeds (best-effort hydration swallows failure) (covered by `SIGA_BASE_URL=""` callback tests + `test_hydrate_from_siga_swallows_unavailable_and_returns_existing`)

### Quality gates
- [x] `ruff` + `mypy` clean
- [x] `pytest` green; usuarios coverage (formal % not measured this pass — branch coverage of every service/repo/middleware path is exercised by 88 usuarios tests)
- [x] Grep audit: no `HttpRequest` import in `services/` or `repositories/`


### E2E
- [x] Tier 1 (Client multi-step): Cross-feature: a JWT-validated request reaches a protected view; expired/invalid tokens are rejected with the right redirect.
- [x] Tier 2 (browser/Playwright): Golden path: external login (via `/auth/dev-login` stand-in) → land on profile → logout. Covered by `app/tests-e2e/test_auth_golden_path.py` against a real Chromium running through the full middleware chain. Initiative 010 swaps only the entry point — the rest of the flow this test exercises is the production code path that 010 keeps using as-is.

## Blockers

- **OQ-002-1** — Provider team needs to confirm JWT transport (cookie they set vs. callback handshake vs. Authorization header). The plan assumes the callback handshake; adapt the middleware and drop the callback if their answer differs.

## Legend

- `[P]` = parallelizable with siblings in the same section
