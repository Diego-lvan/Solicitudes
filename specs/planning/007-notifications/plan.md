# 007-notifications — Notifications

> **Draft.** This is a stub plan. The initiative has not been brainstormed or planned yet. Run `/brainstorm` against the relevant scope to produce a draft `requirements.md`, then `/plan` to fill in this file.

## Summary

Email dispatch on state transitions (Celery + Redis); per-user notification preferences; deduplication of repeated transitions; templated emails with the solicitud snapshot.

## Depends on

- **004** — see roadmap

## Affected Apps / Modules

- `apps/notificaciones`

## References

- [requirements.md](../../global/requirements.md) — system-wide requirements
- [architecture.md](../../global/architecture.md) — tech stack and structure
- [.claude/rules/django-code-architect.md](../../../.claude/rules/django-code-architect.md) — architectural rules (mandatory read)

## Implementation Details

_Not yet written. Run `/brainstorm` and `/plan` to fill in:_

- DB schema changes (full model definitions, migrations)
- Pydantic DTO definitions per layer boundary
- Repository interface(s) + implementation outline
- Service interface(s) + implementation outline (business rules, state transitions)
- View structure (per actor: solicitante / personal / admin)
- Forms (boundary parsers → DTO conversion)
- URL routing (project → app → feature)
- Permission classes / mixins
- Templates needed (which extend, which new)
- Custom exception types in feature `exceptions.py`
- Cross-app dependencies (which feature's service this consumes)
- Settings / env-var changes
- Sequencing notes

## Acceptance Criteria

_Not yet written. Each criterion will become one or more tasks in `status.md` once `/plan` is run._

## Open Questions

_None yet captured. Brainstorm will surface them._
