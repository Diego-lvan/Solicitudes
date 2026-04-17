# Roadmap — Sistema de Solicitudes

> Single source of truth for project status. Each initiative links to its detailed plan in `planning/`. Update the **Status** column whenever an initiative's state changes; append a row when a new initiative is added; never delete rows for completed work.

## Initiatives

| #   | Initiative                | Status      | Depends on    | Added      | Plan                                                       | Affects                                                                 |
| --- | ------------------------- | ----------- | ------------- | ---------- | ---------------------------------------------------------- | ----------------------------------------------------------------------- |
| 001 | Project Setup & Base      | Not Started | —             | 2026-04-25 | [plan](../planning/001-project-setup/plan.md)              | `config`, `apps/_shared`, `templates`, `shared/infrastructure`, `shared/best-practices` |
| 002 | Auth & Users              | Not Started | 001           | 2026-04-25 | [plan](../planning/002-auth-users/plan.md)                 | `apps/usuarios`, `apps/_shared/auth`                                    |
| 003 | Catalog & Dynamic Forms   | Not Started | 002           | 2026-04-25 | [plan](../planning/003-catalog-forms/plan.md)              | `apps/solicitudes/tipos`, `apps/solicitudes/formularios`                |
| 004 | Solicitud Lifecycle       | Not Started | 003           | 2026-04-25 | [plan](../planning/004-solicitud-lifecycle/plan.md)        | `apps/solicitudes/intake`, `apps/solicitudes/revision`, `apps/solicitudes/lifecycle`, `flows` |
| 005 | File Management           | Not Started | 004           | 2026-04-25 | [plan](../planning/005-file-management/plan.md)            | `apps/solicitudes/archivos`, `apps/_shared` (storage)                   |
| 006 | PDF Generation            | Not Started | 004           | 2026-04-25 | [plan](../planning/006-pdf-generation/plan.md)             | `apps/solicitudes/pdf`, `apps/_shared/pdf`                              |
| 007 | Notifications             | Not Started | 004           | 2026-04-25 | [plan](../planning/007-notifications/plan.md)              | `apps/notificaciones`, `flows`                                          |
| 008 | Mentors                   | Not Started | 002           | 2026-04-25 | [plan](../planning/008-mentors/plan.md)                    | `apps/mentores`                                                         |
| 009 | Reports & Dashboard       | Not Started | 004           | 2026-04-25 | [plan](../planning/009-reports/plan.md)                    | `apps/reportes`                                                         |

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
      │         └── 009 Reports & Dashboard
      └── 008 Mentors
```

## Notes

- After 004 lands, **005, 006, 007, 009 can run in parallel** — they share no critical-path files.
- **008 (Mentors)** depends only on 002, so it can run in parallel with 003/004.
- Each initiative is sized for 1–3 implementation sessions. If a `plan.md` grows past that, decompose into sub-initiatives before starting `/implement`.

## Update protocol

- When `/plan` creates a new initiative → append a row with today's date in `Added`.
- When `/implement` starts work on an initiative → flip `Status` to `In Progress`.
- When a blocker appears → flip to `Blocked` and document the cause in the initiative's `status.md`.
- When `/review` confirms an initiative is complete and `design.md` has been updated → flip to `Done`. Do not delete the row.
