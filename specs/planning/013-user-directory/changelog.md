# 013 — User Directory (admin read-only) — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-26
- Initiative created via `/brainstorm` → `/plan`.
- Scope: admin-only paginated list of `usuarios.User` + read-only detail page; role filter + free-text search; mentor status overlaid live via `MentorService`.
- Key decisions:
  - **Read-only by design.** SIGA + the auth provider own user data; no mutation paths shipped.
  - **New `UserDirectoryRepository` instead of reusing `UserRepository.list_all()`** — preserves the existing DEBUG-only contract documented in `usuarios/design.md` ("Production code paths should not enumerate users").
  - **Cross-feature read via `MentorService`** (interface), not `MentorRepository` — per the architectural rule.
  - **Permissive querystring parsing** (mirrors `reportes` RF-REP-06) — bad `role` / `page` degrades to "no filter" / page 1, never 400.
  - **CSV/Excel/PDF export, links to user's solicitudes, edit/delete: explicit non-goals** for v1.
  - **No Tier-2 Playwright in v1** — internal admin tooling, low risk; Tier-1 in-process coverage only.
  - **Sidebar entry under existing ADMIN section**, "Directorio · Usuarios", active-path excludes `/auth/...` to avoid false highlighting on the profile page.
- Files written: `specs/apps/usuarios/directory/{requirements,design}.md`, `specs/planning/013-user-directory/{plan,status,changelog}.md`.
- Roadmap row added.
