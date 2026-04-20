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
- _intake/, revision/, lifecycle/, archivos/, pdf/ — to be added by initiatives 004–006_
