"""Constants for the mentores app."""
from __future__ import annotations

from enum import StrEnum


class MentorSource(StrEnum):
    """How a mentor entry came to exist in the catalog."""

    MANUAL = "MANUAL"
    CSV = "CSV"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(m.value, m.value.title()) for m in cls]


# Default matricula format. Configurable via the ``MENTOR_MATRICULA_REGEX``
# Django setting; see OQ-008-1 in plan.md.
DEFAULT_MATRICULA_REGEX = r"^\d{8}$"
