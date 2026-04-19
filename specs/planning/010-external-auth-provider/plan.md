# 010 — External Auth Provider Integration

## Summary

Replace the dev-only `/auth/dev-login` picker (introduced in 002) with the real external authentication provider handshake. This initiative resolves the open questions from 002 and exists to absorb the changes the provider's contract will require — *not* to redesign auth.

The architectural seams are already in place: `JwtAuthenticationMiddleware`, `RoleResolver` ABC, `UserService.get_or_create_from_claims`, and `/auth/callback`. The work here is configuration, contract translation, removal of the dev-only stand-in, and the manual + browser-level smoke testing that was deferred from 002.

## Depends on

- **002** — `usuarios` app, `Role`, `UserRepository`, `RoleResolver`, `UserService`, `JwtAuthenticationMiddleware`, `CallbackView`, `LogoutView`, permission mixins, the `stk` cookie contract.

## Affected Apps / Modules

- `usuarios/` — possibly extend `RoleResolver` (`DirectoryRoleResolver` if OQ-002-2 says yes), possibly adjust middleware token-source if OQ-002-1 picks something other than the cookie callback.
- `config/settings/` — provider URLs, refresh-token settings (OQ-002-3).
- `flows/` — new `flows/external-login.md` documenting the real end-to-end sequence.

## References

- [global/requirements.md](../../global/requirements.md) — RNF-01 (auth externa).
- [planning/002-auth-users/plan.md](../002-auth-users/plan.md) — Open Questions section.
- [planning/002-auth-users/changelog.md](../002-auth-users/changelog.md) — what 002 actually shipped, including the dev-login stand-in.

## Open Questions inherited from 002 (must be resolved before/during this initiative)

- **OQ-002-1** — JWT transport. Three candidate shapes: (a) provider redirects to `/auth/callback?token=…` and we set the `stk` cookie ourselves (what 002 assumed); (b) provider sets a cross-domain cookie directly, and we drop the callback handshake; (c) provider issues a Bearer token from a frontend, and we drop the cookie and read `Authorization`.
- **OQ-002-2** — Personal roles (CONTROL_ESCOLAR, RESPONSABLE_PROGRAMA): does the provider's JWT carry these? If yes, `JwtRoleResolver` is sufficient. If no, we add `DirectoryRoleResolver` backed by an admin-managed mapping table — the `RoleResolver` ABC absorbs the change without rippling.
- **OQ-002-3** — JWT renewal/refresh. The 002 cookie sets `max_age = exp − now`. If the provider issues short-lived tokens, we add a refresh-token flow.
- **OQ-002-4** — User deactivation. Today, a provider revocation only takes effect on the next failed JWT check. Revisit if compliance asks.

## Implementation Details (to be filled in via `/brainstorm` + `/plan` once OQ-002-1 is answered)

This file is a stub. The work here cannot be planned in detail until the provider team confirms their contract. Once they do:

1. Run `/brainstorm` against the answered open questions to produce a draft spec.
2. Run `/plan` to fill in this file (model adjustments if any, settings, sequencing, acceptance criteria).
3. Run `/implement`.

### Things this initiative will definitely do, regardless of OQ-002-1's answer

- **Remove `/auth/dev-login`** — delete `usuarios/views/dev_login.py`, `templates/usuarios/dev_login.html`, `tests/test_views_dev_login.py`, the `if settings.DEBUG` block in `usuarios/urls.py`, and the `/auth/dev-login` entry in `JwtAuthenticationMiddleware.SKIP_PREFIXES`.
- **Write `flows/external-login.md`** with the real sequence diagram (provider → redirect/cookie → middleware → user upsert → first authenticated request).
- **Ship Tier 2 Playwright** (the deferred E2E from 002): real provider stub, golden-path browser flow.
- **Ship the manual smoke runbook** for ops (replaces the deferred `tools/mint_dev_jwt.py` script — no longer needed once a real login exists).
- **Add a 403-with-wrong-role smoke test** once 003+ has mounted role-gated URLs (this was also deferred from 002).

## Acceptance Criteria (preliminary)

- [ ] `/auth/dev-login` and all its supporting code are deleted; grep audit confirms zero references in `usuarios/`, `templates/`, `tests/`, and settings.
- [ ] `flows/external-login.md` exists and references the real provider URL/contract.
- [ ] Tier 2 Playwright golden path passes (`make e2e`).
- [ ] OQ-002-1 through OQ-002-4 are resolved and recorded in this initiative's `changelog.md` — no `[PENDING]` markers remain.
- [ ] Production deploy with the real provider succeeds end-to-end (manual sign-off from ops).
