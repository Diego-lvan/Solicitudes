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


class FieldSource(StrEnum):
    """Where a FieldDefinition's value comes from at intake time.

    `USER_INPUT` is the default and means the alumno fills the form input.
    `USER_*` variants are auto-filled from the alumno's hydrated UserDTO; the
    intake form never renders a control for them and the resolver merges the
    backend value into the persisted `valores` after form validation.
    """

    USER_INPUT = "USER_INPUT"
    USER_FULL_NAME = "USER_FULL_NAME"
    USER_PROGRAMA = "USER_PROGRAMA"
    USER_EMAIL = "USER_EMAIL"
    USER_MATRICULA = "USER_MATRICULA"
    USER_SEMESTRE = "USER_SEMESTRE"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        # User-facing labels in Spanish; identifiers stay English.
        labels: dict[FieldSource, str] = {
            cls.USER_INPUT: "El solicitante lo escribe",
            cls.USER_FULL_NAME: "Auto · Nombre completo",
            cls.USER_PROGRAMA: "Auto · Programa",
            cls.USER_EMAIL: "Auto · Correo",
            cls.USER_MATRICULA: "Auto · Matrícula",
            cls.USER_SEMESTRE: "Auto · Semestre",
        }
        return [(m.value, labels[m]) for m in cls]


# Source ↔ FieldType compatibility — enforced by Pydantic validator on
# CreateFieldInput and (defense in depth) by FieldForm.clean(). USER_* sources
# only make sense on text/numeric fields; SELECT/FILE/DATE/TEXTAREA fields can
# only be USER_INPUT.
FIELD_SOURCE_ALLOWED_TYPES: dict[FieldSource, frozenset[FieldType]] = {
    FieldSource.USER_INPUT: frozenset(FieldType),
    FieldSource.USER_FULL_NAME: frozenset({FieldType.TEXT}),
    FieldSource.USER_PROGRAMA: frozenset({FieldType.TEXT}),
    FieldSource.USER_EMAIL: frozenset({FieldType.TEXT}),
    FieldSource.USER_MATRICULA: frozenset({FieldType.TEXT}),
    FieldSource.USER_SEMESTRE: frozenset({FieldType.NUMBER}),
}


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
