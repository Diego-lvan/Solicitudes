"""Adapter satisfying intake's outbound ``MentorService`` port.

Per `.claude/rules/django-code-architect.md` cross-feature dependency rule,
the *consumer* (intake) declares the port abstraction at
``solicitudes.intake.mentor_port.MentorService``; the *producer* (mentores)
provides the concrete adapter that delegates the port to its richer service.

Living on the producer side keeps intake's runtime code free of mentores
imports — only ``solicitudes.intake.dependencies`` touches mentores, and
only at wiring time (the same place ``tipos.dependencies`` is imported).
"""
from __future__ import annotations

from mentores.services.mentor_service.interface import (
    MentorService as MentoresMentorService,
)
from solicitudes.intake.mentor_port import MentorService as IntakeMentorService


class MentoresIntakeAdapter(IntakeMentorService):
    """Implements intake's ``MentorService`` port by delegating to mentores."""

    def __init__(self, mentores_service: MentoresMentorService) -> None:
        self._mentores = mentores_service

    def is_mentor(self, matricula: str) -> bool:
        return self._mentores.is_mentor(matricula)
