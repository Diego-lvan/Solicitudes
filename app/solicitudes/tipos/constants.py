"""Constants for the tipos feature."""
from __future__ import annotations

from enum import StrEnum


class FieldType(StrEnum):
    """Supported field types for dynamic forms."""

    TEXT = "TEXT"
    TEXTAREA = "TEXTAREA"
    NUMBER = "NUMBER"
    DATE = "DATE"
    SELECT = "SELECT"
    FILE = "FILE"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(m.value, m.value.title()) for m in cls]


# Hard cap on fields per tipo. 50 covers every real institutional form we've
# seen; if a real tipo legitimately needs more, revisit OQ-003-3 rather than
# bumping this silently.
MAX_FIELDS_PER_TIPO = 50

# Roles that can be set as `creator_roles` on a tipo. Personal/admin roles
# never *file* solicitudes; only ALUMNO and DOCENTE do.
ALLOWED_CREATOR_ROLES = ("ALUMNO", "DOCENTE")

# Roles that can be set as `responsible_role` on a tipo. ADMIN is never a
# responsible because admins manage the catalog, they don't review solicitudes.
ALLOWED_RESPONSIBLE_ROLES = ("CONTROL_ESCOLAR", "RESPONSABLE_PROGRAMA", "DOCENTE")

# Common file extensions an admin can pick when configuring a FILE field.
# Grouped roughly so the picker can show them in sections. Admins can still
# save any extension via the API/legacy path; the UI degrades gracefully by
# rendering unknown saved extensions as additional toggles when editing.
COMMON_FILE_EXTENSIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Documentos", (".pdf", ".doc", ".docx", ".odt", ".txt", ".rtf")),
    ("Imágenes", (".jpg", ".jpeg", ".png", ".gif", ".webp")),
    ("Hojas de cálculo", (".xls", ".xlsx", ".csv", ".ods")),
    ("Otros", (".zip", ".rar", ".7z")),
)
