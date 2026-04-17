# 004-solicitud-lifecycle — Solicitud Lifecycle — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25
- Initiative directory created (stub)
- Plan, status, and changelog files created as drafts pending `/brainstorm` + `/plan`
- Plan filled in: `Solicitud` + `HistorialEstado` + `FolioCounter` models, state machine `CREADA → EN_PROCESO → FINALIZADA`/`CANCELADA` with action-based transition matrix, `SOL-YYYY-NNNNN` folio (atomic counter), shared queue (no `assigned_to`), form snapshot at creation, intake + revision feature packages, three NoOp/False/discard placeholders for cross-app deps until 005/007/008 land. Largest initiative; expect 2–3 sessions.
