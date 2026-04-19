# 010-external-auth-provider — External Auth Provider Integration — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25
- Initiative carved out at the end of 002. Scope: replace the DEBUG-only `/auth/dev-login` picker (shipped in 002 as a stand-in) with the real external authentication provider handshake. Resolves OQ-002-1 (JWT transport), OQ-002-2 (provider personal roles), OQ-002-3 (refresh), OQ-002-4 (revocation). Picks up the deferred Tier 2 Playwright E2E and the manual smoke runbook.
- Status: Not Started, blocked on the provider team's answer to OQ-002-1. Plan stub created; full plan fills in after `/brainstorm` once the contract is known.
