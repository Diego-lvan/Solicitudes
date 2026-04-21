"""Outbound port for resolving whether a user is a mentor.

Owned by the consumer (intake) per the cross-feature dependency rule. The
``mentores`` feature (initiative 008) will provide the real adapter; until
then ``FalseMentorService`` is wired in ``dependencies.py`` so 004 ships
without 008. The boolean it returns flows into ``Solicitud.pago_exento``
when the tipo is ``mentor_exempt``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class MentorService(ABC):
    @abstractmethod
    def is_mentor(self, matricula: str) -> bool:
        """Return True iff the user is a current mentor."""


class FalseMentorService(MentorService):
    """Default binding until 008 lands. Always returns False."""

    def is_mentor(self, matricula: str) -> bool:
        return False
