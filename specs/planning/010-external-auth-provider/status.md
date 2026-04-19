# 010 — External Auth Provider Integration — Status

**Status:** Not Started
**Last updated:** 2026-04-25

## Checklist

This initiative cannot be checklisted until OQ-002-1 (provider JWT transport)
is answered. The known-regardless work is:

### Once OQ-002-1 is answered
- [ ] `/brainstorm` against the resolved open questions
- [ ] `/plan` — fill in `plan.md` Implementation Details

### Cleanup of the 002 dev stand-in
- [ ] Remove `usuarios/views/dev_login.py`
- [ ] Remove `templates/usuarios/dev_login.html`
- [ ] Remove `usuarios/tests/test_views_dev_login.py`
- [ ] Remove the `if settings.DEBUG` URL mount in `usuarios/urls.py`
- [ ] Remove `/auth/dev-login` from `JwtAuthenticationMiddleware.SKIP_PREFIXES`
- [ ] Confirm grep audit: zero references to `dev_login` / `DevLoginView` / `_QUICKSTART_USERS`

### Provider integration (shape depends on OQ-002-1)
- [ ] Wire real `JWT_SECRET` and provider URLs in env
- [ ] Adjust `JwtAuthenticationMiddleware` token source if needed (cookie vs. header)
- [ ] If OQ-002-2 says no: add `DirectoryRoleResolver` + admin UI for the mapping
- [ ] If OQ-002-3 says short-lived: add refresh flow

### Documentation & E2E (deferred from 002)
- [x] Write `flows/external-login.md` — done in 002 (v1, with the 010 follow-up flagged inline)
- [x] Tier 2 Playwright golden path — done in 002 against `/auth/dev-login`. **010 must update the test** to use the real provider entry point instead of the dev-login picker (the rest of the flow stays the same).
- [ ] Manual smoke runbook in `README.md` (replaces `tools/mint_dev_jwt.py` plan)
- [ ] 403 wrong-role smoke once 003+ has role-gated URLs

### Quality gates
- [ ] `ruff` + `mypy` clean
- [ ] `pytest` green; `make e2e` green

## Blockers

- **OQ-002-1** — provider team has not confirmed JWT transport. Cannot detail the plan until this lands.
