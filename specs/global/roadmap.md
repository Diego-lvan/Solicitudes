# Roadmap — Sistema de Solicitudes

> Single source of truth for project status. Each initiative links to its detailed plan in `planning/`. Update the **Status** column whenever an initiative's state changes; append a row when a new initiative is added; never delete rows for completed work.

## Initiatives

| #   | Initiative                | Status      | Depends on    | Added      | Plan                                                       | Affects                                                                 |
| --- | ------------------------- | ----------- | ------------- | ---------- | ---------------------------------------------------------- | ----------------------------------------------------------------------- |
| 001 | Project Setup & Base      | Done        | —             | 2026-04-25 | [plan](../planning/001-project-setup/plan.md)              | `config`, `_shared`, `templates`, `shared/infrastructure`, `shared/best-practices` |
| 002 | Auth & Users              | Done        | 001           | 2026-04-25 | [plan](../planning/002-auth-users/plan.md)                 | `usuarios`, `_shared/auth`                                    |
| 003 | Catalog & Dynamic Forms   | Done        | 002           | 2026-04-25 | [plan](../planning/003-catalog-forms/plan.md)              | `solicitudes/tipos`, `solicitudes/formularios`                |
| 004 | Solicitud Lifecycle       | Done        | 003           | 2026-04-25 | [plan](../planning/004-solicitud-lifecycle/plan.md)        | `solicitudes/intake`, `solicitudes/revision`, `solicitudes/lifecycle`, `flows` |
| 005 | File Management           | Done        | 004           | 2026-04-25 | [plan](../planning/005-file-management/plan.md)            | `solicitudes/archivos`, `_shared` (storage)                   |
| 006 | PDF Generation            | Done        | 004           | 2026-04-25 | [plan](../planning/006-pdf-generation/plan.md)             | `solicitudes/pdf`, `_shared/pdf`                              |
| 007 | Notifications             | Done        | 004           | 2026-04-25 | [plan](../planning/007-notifications/plan.md)              | `notificaciones`, `flows`                                          |
| 008 | Mentors                   | Done        | 002           | 2026-04-25 | [plan](../planning/008-mentors/plan.md)                    | `mentores`                                                         |
| 009 | Reports & Dashboard       | Done        | 004           | 2026-04-25 | [plan](../planning/009-reports/plan.md)                    | `reportes`                                                         |
| 010 | External Auth Provider    | Blocked     | 002 + OQ-002-1 | 2026-04-25 | [plan](../planning/010-external-auth-provider/plan.md)     | `usuarios`, `flows`                                                  |
| 011 | Field Auto-fill from User | Done        | 003 + 004     | 2026-04-25 | [plan](../planning/011-field-autofill/plan.md)             | `solicitudes/tipos`, `solicitudes/formularios`, `solicitudes/intake`, `usuarios` (gender), `solicitudes/pdf` (context) |
| 012 | Mentor Catalog Historicization | Done        | 008           | 2026-04-25 | [plan](../planning/012-mentor-historicization/plan.md)     | `mentores` (model + repo + service + views), `mentores/migrations` |
| 013 | User Directory (admin read-only) | Done        | 002 + 008     | 2026-04-26 | [plan](../planning/013-user-directory/plan.md)             | `usuarios/directory` (new feature), `usuarios/urls`, `templates/usuarios/directory`, `templates/components/sidebar.html` |
| 014 | Revision Handler Display  | Done        | 004 + 002     | 2026-04-26 | [plan](../planning/014-revision-handler-display/plan.md)   | `solicitudes/lifecycle` (DTOs + repo annotation), `solicitudes/revision` (templates), `templates/solicitudes/revision/{queue,detail}.html` |
| 015 | Tailwind v4 Frontend Migration | Done        | 001 (+ all shipped initiatives' templates) | 2026-04-26 | [plan](../planning/015-tailwind-migration/plan.md) | All `app/templates/**`, `app/static/{css,js,vendor,fonts}/**`, `Dockerfile`, `docker-compose.dev.yml`, `Makefile`, `.gitignore`, `.claude/skills/frontend-design`, `.claude/skills/django-patterns/{forms,platform}.md`, `.claude/rules/django.md`, `CLAUDE.md`, `specs/global/{architecture,requirements}.md` |
| 016 | Response Files & Comments | Done        | 004 + 005 + 006 + 014 | 2026-05-15 | [plan](../planning/016-respuesta/plan.md) | `solicitudes/respuesta` (new), `solicitudes/models` (`respuesta_solicitud`, `archivo_respuesta`), `solicitudes/migrations`, `solicitudes/pdf` (authz amend), `templates/solicitudes/{intake,revision}/detail.html` |
| 017 | Plantilla Editor & Asset Library | Done        | 006 + 003 + 015 | 2026-05-17 | [plan](../planning/017-plantilla-editor/plan.md) | `solicitudes/pdf` (editor redesign + preview endpoints + assets resolver), `solicitudes/plantilla_assets` (new feature), `solicitudes/models/plantilla_asset.py` (new), `solicitudes/migrations/0007`, `templates/solicitudes/admin/{plantillas,plantilla_assets,_partials}/**`, `templates/components/sidebar.html`, `static/js/plantilla_editor.js` (new) |

**Status values:** `Not Started` · `In Progress` · `Blocked` · `Done`

## Dependency Graph

```
001 Project Setup & Base
 └── 002 Auth & Users
      ├── 003 Catalog & Dynamic Forms
      │    └── 004 Solicitud Lifecycle
      │         ├── 005 File Management
      │         ├── 006 PDF Generation
      │         ├── 007 Notifications
      │         ├── 009 Reports & Dashboard
      │         └── 011 Field Auto-fill from User Data   (extends 003 + intake)
      ├── 008 Mentors
      │    ├── 012 Mentor Catalog Historicization
      │    └── 013 User Directory (admin read-only)   (also depends on 002)
      │
      └── 014 Revision Handler Display   (additive on 004; templates + lifecycle DTOs)
      └── 010 External Auth Provider   (blocked on OQ-002-1)

015 Tailwind v4 Frontend Migration   (cross-cutting infra; touches every shipped initiative's templates; blocks 013/014 template work while in progress)

016 Response Files & Comments   (additive on 004/005/006/014; new respuesta feature + pdf authz amendment)
```

## Notes

- After 004 lands, **005, 006, 007, 009 can run in parallel** — they share no critical-path files.
- **008 (Mentors)** depends only on 002, so it can run in parallel with 003/004.
- **010 (External Auth Provider)** swaps the DEBUG-only `/auth/dev-login` picker shipped in 002 for the real provider handshake; blocked on OQ-002-1. Can run any time after 002 once the provider contract is known.
- **012 (Mentor Catalog Historicization)** rewrites the catalog from "current state only" (one row per matrícula) to a per-period model (`MentorPeriodo`). Hard-blocked on 008 — must merge to `main` first since 012 replaces 008's `Mentor` table.
- **015 (Tailwind v4 Frontend Migration)** is cross-cutting infrastructure; it touches every shipped initiative's templates. Single feature branch `feat/015-tailwind-migration`, single PR, big-bang merge. While in progress, **013** and **014** template work should pause — otherwise their Bootstrap-based templates would need a second rewrite immediately after merging. Backend work on 013/014 (models, services, repos, views) can proceed in parallel.
- Each initiative is sized for 1–3 implementation sessions. If a `plan.md` grows past that, decompose into sub-initiatives before starting `/implement`.

## Update protocol

- When `/plan` creates a new initiative → append a row with today's date in `Added`.
- When `/implement` starts work on an initiative → flip `Status` to `In Progress`.
- When a blocker appears → flip to `Blocked` and document the cause in the initiative's `status.md`.
- When `/review` confirms an initiative is complete and `design.md` has been updated → flip to `Done`. Do not delete the row.
