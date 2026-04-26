# `usuarios · directory` — Requirements

> WHAT this feature does and WHY. No implementation details. Shipped by initiative **013 — User Directory (admin read-only)**.

## Purpose

Give administrators a way to **see who exists in the system**: who has logged in, what role they hold, and what cached profile data SIGA has produced. Today the only way to enumerate users is the DEBUG-only dev-login picker, which is mounted only when `settings.DEBUG=True` and is documented in `usuarios/design.md` as "Production code paths should not enumerate users."

This feature ships the **production** read path so an admin can answer day-to-day questions ("does this matrícula have an account?", "what role is this user assigned?", "when did they last log in?") without SSH access to the database.

## Why read-only

User data is owned by the **external auth provider** (identity, role) and **SIGA** (academic profile fields). The Sistema de Solicitudes only **caches** what it sees on login (per `RNF-01`, `RNF-02`, and the cached-fields contract in `usuarios/design.md`). Editing user data here would diverge from those upstream systems and create a stale source of truth. The directory therefore exposes the cached state and nothing more — no edit, no delete, no role change.

## In scope

- An **admin-only paginated list** of every persisted `User`, with role filter and free-text search.
- Search matches case-insensitively against `matricula`, `full_name`, and `email`.
- A **detail page per user** showing identity, cached academic profile, mentor status, and audit timestamps.
- A new sidebar entry "**Usuarios**" under the existing Admin section, visible only to `ADMIN`.
- Anonymous users redirect to login; authenticated non-admin users get 403 (per `RF-USR-07`).

## Out of scope

- Any mutation of user data (create / edit / delete / role change). SIGA + the auth provider own that.
- CSV / Excel / PDF export of the directory. Possible future work; v1 is screen-only.
- Linking from a user row to that user's solicitudes. Possible future work; keeps this feature pure-identity for v1.
- Showing tokens, JWT claims, or any session-internal data.
- Surfacing users that exist in the auth provider but have never logged in (the system only knows users it has materialized).
- Real-time updates / push. The list is fetched per request.

## Functional requirements

| ID | Requirement | Source |
|---|---|---|
| RF-DIR-01 | `GET /usuarios/` must render a paginated list of every persisted user, ordered deterministically by `role` ASC then `matricula` ASC. | RF-USR-07, design.md |
| RF-DIR-02 | The list must accept an optional `role` filter (one of the five `Role` values; empty = all). | scope |
| RF-DIR-03 | The list must accept an optional `q` filter, matched case-insensitively against `matricula`, `full_name`, and `email` (OR-joined; trimmed; empty = ignored). | scope |
| RF-DIR-04 | Pagination uses page size **25** with 1-based page numbers; invalid `page` values fall back to page 1; pagination links must preserve the active filter querystring. | scope, UX |
| RF-DIR-05 | Each list row exposes `matricula`, `full_name`, `role`, `programa`, `email`, and a friendly `last_login_at` (relative; "Nunca" when null). The whole row links to the detail page. | scope |
| RF-DIR-06 | `GET /usuarios/<matricula>/` must render a read-only detail card with: identidad (matrícula, full_name, email, role), académico (programa, semestre, gender rendered as "Hombre" / "Mujer" / "—"), mentor status, auditoría (last_login_at, created_at, updated_at). | scope |
| RF-DIR-07 | The detail page must consult `mentores.MentorService` to populate `is_mentor` live (not stored on `User`, per the cross-feature contract in `usuarios/design.md`). If the mentor service raises, the page must render the rest of the detail and show "Desconocido" for mentor status — **not** 500. | architecture.md (cross-feature contract), UX |
| RF-DIR-08 | An unknown matrícula on the detail URL must return 404 via the standard error template. | UX |
| RF-DIR-09 | Anonymous access to either URL must redirect to the auth provider login (existing middleware behavior). Authenticated non-admin access must return 403 with the standard error template. | RF-USR-07 |
| RF-DIR-10 | The "Volver" link on the detail page must preserve the list's filter querystring so the admin returns to the same filtered page. | UX |
| RF-DIR-11 | A "Usuarios" sidebar entry must appear under the Admin section, visible only to `ADMIN`, marking itself active when the path matches `/usuarios/...`. | UX |

## Non-functional requirements

- **No new ORM model and no migrations.** All required fields already live on `usuarios.User`.
- **No mutation paths anywhere.** Templates contain no forms beyond GET filters; URLs accept GET only.
- **Production-safe enumeration.** A new repository owns the paginated query path; the existing `UserRepository.list_all()` (DEBUG dev-login picker) is **not** reused, preserving its narrowed contract.
- **Cross-feature reads are service-to-service.** Mentor status is fetched through `mentores.MentorService`, never `MentorRepository` (per the rule in `.claude/rules/django-code-architect.md`).
- **Permissive querystring parsing.** Bad `role` values (typo / unknown enum) and bad `page` values degrade silently to "no filter" / page 1 — same posture as `reportes` (RF-REP-06). An admin landing on a stale bookmark sees results, not a 400.
- **Deterministic ordering across pages.** A user does not jump pages or duplicate as the dataset grows; `(role, matricula)` is unique under the schema.
- **Spanish UI copy** end-to-end. Code identifiers in English (per CLAUDE.md).
- **Accessibility.** Bootstrap 5 layout reflows to 320 px; role badges convey role via color **and** text (no color-only signal).

## Open questions

None at brainstorm closeout (2026-04-26).

## Related Specs

- [design.md](./design.md) — HOW (filled at initiative closeout).
- [`specs/apps/usuarios/requirements.md`](../requirements.md) — parent app requirements (RF-USR-07 admin gating).
- [`specs/apps/usuarios/design.md`](../design.md) — `User` model, `UserRepository`, `AdminRequiredMixin`.
- [`specs/apps/mentores/catalog/design.md`](../../mentores/catalog/design.md) — `MentorService.is_mentor` consumed for the detail page.
- [`specs/planning/013-user-directory/plan.md`](../../../planning/013-user-directory/plan.md) — implementation blueprint.
- [`specs/global/requirements.md`](../../../global/requirements.md) — RNF-01, RNF-02, RT-08.
