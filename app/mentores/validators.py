"""Domain validators shared by forms, services, and the CSV importer."""
from __future__ import annotations

import re

from django.conf import settings

from mentores.constants import DEFAULT_MATRICULA_REGEX


def _matricula_pattern() -> re.Pattern[str]:
    pattern = getattr(settings, "MENTOR_MATRICULA_REGEX", DEFAULT_MATRICULA_REGEX)
    return re.compile(pattern)


def is_valid_matricula(value: str) -> bool:
    """Pure check — returns ``True`` iff ``value`` matches the configured regex."""
    return bool(_matricula_pattern().fullmatch(value))


def matricula_format_message() -> str:
    """User-facing description of the expected format (Spanish)."""
    return "La matrícula debe tener 8 dígitos."
