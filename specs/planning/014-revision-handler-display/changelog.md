# 014 — Revision Handler Display — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-26

- Initiative created.
- Brainstorm settled in-session: surface "who is handling this" in the revision queue + detail, drop the "Acción" column, and render solicitante context (nombre · matrícula · email) on the revision detail page.
- Key decisions:
  - "Atendida por" is **derived** from `HistorialEstado` (actor of the most recent `atender` transition). No `assigned_to` field; shared-queue invariant preserved.
  - Display populated for EN_PROCESO, FINALIZADA, and CANCELADA-from-EN_PROCESO; blank for CREADA and CANCELADA-from-CREADA (Option B from brainstorm).
  - Scope is **revision only** (not "Mis solicitudes" / intake list).
  - Queue path keeps the existing 3-query cap via `Subquery` annotation on `_base_queryset()`. Detail path takes zero extra SQL (historial is already loaded).
  - DTO shape split: flat strings on `SolicitudRow` (queue), structured `HandlerRef` on `SolicitudDetail` (detail) — keeps the queue template trivial while letting the detail render `name (matrícula) · date`.
- Out of scope captured: no `assigned_to` semantics, no intake-side changes, no separate finalizer/canceller attribution, no notification copy changes, no new "atendida por" filter on the queue.
