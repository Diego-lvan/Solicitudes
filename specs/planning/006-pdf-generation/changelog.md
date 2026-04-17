# 006-pdf-generation — PDF Generation — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25
- Initiative directory created (stub)
- Plan, status, and changelog files created as drafts pending `/brainstorm` + `/plan`
- Plan filled in: `PlantillaSolicitud` model + admin CRUD + Django-template-engine substitution, on-demand WeasyPrint render, no PDF blob persisted, deterministic re-render under frozen clock. Resolves 003's `plantilla_id` placeholder by adding the FK migration.
