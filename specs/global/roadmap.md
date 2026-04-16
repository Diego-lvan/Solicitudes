# Roadmap — Sistema de Solicitudes

## Initiatives

| # | Name | Status | Depends On | Affected Apps | Plan |
|---|------|--------|-----------|---------------|------|
| 001 | Project Setup & Base | Not Started | — | config, templates | [plan](../planning/001-project-setup/plan.md) |
| 002 | Auth & Users | Not Started | 001 | usuarios | [plan](../planning/002-auth-users/plan.md) |
| 003 | Catalog & Dynamic Forms | Not Started | 002 | solicitudes | [plan](../planning/003-catalog-forms/plan.md) |
| 004 | Solicitud Lifecycle | Not Started | 003 | solicitudes | [plan](../planning/004-solicitud-lifecycle/plan.md) |
| 005 | File Management | Not Started | 004 | solicitudes | [plan](../planning/005-file-management/plan.md) |
| 006 | PDF Generation | Not Started | 004 | solicitudes | [plan](../planning/006-pdf-generation/plan.md) |
| 007 | Notifications | Not Started | 004 | notificaciones | [plan](../planning/007-notifications/plan.md) |
| 008 | Mentors | Not Started | 002 | mentores | [plan](../planning/008-mentors/plan.md) |
| 009 | Reports & Dashboard | Not Started | 004 | reportes | [plan](../planning/009-reports/plan.md) |

## Dependency Graph

```
001 Project Setup
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

- Initiatives 005, 006, 007, 009 can run in parallel after 004 completes.
- 008 (Mentors) only depends on 002 — can run in parallel with 003/004.
- Each initiative should be completable in 1-3 sessions.
