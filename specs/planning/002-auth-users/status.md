# 002 — Auth & Users — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

### App skeleton
- [ ] Create `apps/usuarios/` package + `apps.py`
- [ ] Register in `INSTALLED_APPS`
- [ ] `constants.py` (Role enum + provider role map)
- [ ] `schemas.py` (UserDTO, CreateOrUpdateUserInput, SigaProfile)
- [ ] `exceptions.py` (InvalidJwt, RoleNotRecognized, SigaUnavailable)

### Model & migration
- [ ] `models/user.py` (custom `User` + `UserManager`)
- [ ] Set `AUTH_USER_MODEL = "usuarios.User"` in `base.py`
- [ ] Initial migration applies cleanly

### Repository
- [ ] [P] `repositories/user/interface.py` (UserRepository ABC)
- [ ] [P] `repositories/user/implementation.py` (`OrmUserRepository`)
- [ ] [P] `tests/test_user_repository.py` (real DB, ≥ 95% line)

### Services
- [ ] [P] `services/role_resolver/{interface,jwt_implementation}.py` + tests
- [ ] [P] `services/siga/{interface,http_implementation,jwt_fallback}.py` + tests (HTTP mocked via `responses`)
- [ ] `services/user_service/{interface,implementation}.py` + tests (in-memory fakes)

### Test fakes
- [ ] [P] `tests/fakes.py` — `InMemoryUserRepository`, `FakeSigaService`, `FakeRoleResolver`
- [ ] [P] `tests/factories.py` — `make_user(**overrides)` via `model_bakery`

### Wiring
- [ ] `dependencies.py` factory functions
- [ ] `middleware.py` (`JwtAuthenticationMiddleware`) + tests
- [ ] Replace Django's `AuthenticationMiddleware` in `config/settings/base.py`
- [ ] `permissions.py` mixins + tests

### Views & templates
- [ ] [P] `views/callback.py` + `tests/test_views_callback.py`
- [ ] [P] `views/logout.py` + `tests/test_views_logout.py`
- [ ] [P] `views/me.py` + `tests/test_views_me.py`
- [ ] [P] `templates/usuarios/me.html`
- [ ] `apps/usuarios/urls.py` + mount in `config/urls.py`

### Settings & env
- [ ] Add JWT and SIGA env vars to `.env.example`
- [ ] Read them in `base.py`
- [ ] Verify `prod.py` fails fast if `JWT_SECRET` or `AUTH_PROVIDER_LOGIN_URL` missing

### End-to-end smoke
- [ ] Mint a dev JWT (script in `tools/mint_dev_jwt.py` — out of repo scope, document command in README)
- [ ] Hit `/auth/callback?token=<jwt>&return=/auth/me` → verify cookie set + profile rendered
- [ ] Hit a 403 path with a wrong-role user → verify `_shared/error.html` rendered
- [ ] Stop SIGA mock → verify login still succeeds (best-effort hydration swallows failure)

### Quality gates
- [ ] `ruff` + `mypy` clean
- [ ] `pytest` green; usuarios coverage targets met (services 95% / repo 95% / views 80%)
- [ ] Grep audit: no `HttpRequest` import in `services/` or `repositories/`


### E2E
- [ ] Tier 1 (Client multi-step): Cross-feature: a JWT-validated request reaches a protected view; expired/invalid tokens are rejected with the right redirect.
- [ ] Tier 2 (browser/Playwright): Golden path: external login → land on dashboard → logout. (UI portion of auth.)

## Blockers

- **OQ-002-1** — Provider team needs to confirm JWT transport (cookie they set vs. callback handshake vs. Authorization header). The plan assumes the callback handshake; adapt the middleware and drop the callback if their answer differs.

## Legend

- `[P]` = parallelizable with siblings in the same section
