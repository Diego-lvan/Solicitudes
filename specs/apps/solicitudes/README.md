# specs/apps/solicitudes

Feature specs for the `solicitudes` Django app.

**Scope:** Core domain. Features: tipos (catalog), formularios (dynamic forms), intake (create draft), revision (personal review), lifecycle (state machine), archivos (attachments), pdf (rendering).

## Layout

Each feature inside this app gets its own folder with the canonical pair:

```
specs/apps/solicitudes/<feature>/
├── requirements.md   # WHAT + WHY (no implementation details)
└── design.md         # HOW (canonical reference, updated AFTER initiative completes)
```

Folders are created here when `/brainstorm` produces a `requirements.md` for a feature in this app, or when `/plan` decides a brainstorm draft from `global/explorations/` belongs here.

## Currently planned features

- [tipos/](./tipos/) — admin catalog of tipos de solicitud (delivered in 003)
- [formularios/](./formularios/) — runtime form builder consumed by intake (delivered in 003)
- [lifecycle/](./lifecycle/) — state machine, folio allocation, repos, notifications port, audit (delivered in 004)
- [intake/](./intake/) — solicitante surface: catalog, dynamic form, create, mis_solicitudes, owner-cancel (delivered in 004)
- [revision/](./revision/) — personal surface: queue, detail-with-actions, atender/finalizar/cancelar (delivered in 004)
- [pdf/](./pdf/) — admin plantilla CRUD + on-demand WeasyPrint rendering of solicitudes (delivered in 006)
- _archivos/ — to be added by initiative 005_
