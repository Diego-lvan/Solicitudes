"""Pydantic DTOs for the usuarios feature — boundary types between layers."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from usuarios.constants import Role

# Allowed values for the cached SIGA gender code. Anything else (a SIGA
# regression returning ``"X"``/``"F"``/numbers) coerces to ``""`` at the DTO
# boundary so plantillas downstream never see garbage. Keeps the cache
# forgiving while pinning the rendered domain.
_VALID_GENDER_CODES: frozenset[str] = frozenset({"H", "M", ""})


def _coerce_gender(value: Any) -> str:
    """Normalise a SIGA gender code to ``"H"``, ``"M"``, or ``""``.

    Forgiving by design: trims, uppercases, and treats anything outside
    the allowed set as ``""`` (unknown). Same posture as the resolver's
    forgiving lookup on the read side.
    """
    if value is None:
        return ""
    code = str(value).strip().upper()
    return code if code in _VALID_GENDER_CODES else ""


class UserDTO(BaseModel):
    """Frozen DTO returned by repositories and services to the view layer."""

    model_config = ConfigDict(frozen=True)

    matricula: str
    email: EmailStr
    role: Role
    full_name: str = ""
    programa: str = ""
    semestre: int | None = None
    # Single-letter code: ``"H"`` (hombre) / ``"M"`` (mujer) / ``""``
    # (not provided). Consumers needing gendered Spanish (e.g. the PDF
    # template's ``{% if solicitante.genero == "H" %}…{% endif %}``)
    # read this. Never used for identity; kept best-effort like programa.
    gender: str = ""
    is_mentor: bool = False  # populated by mentores service when needed; never persisted on User

    @field_validator("gender", mode="before")
    @classmethod
    def _normalize_gender(cls, v: Any) -> str:
        return _coerce_gender(v)


class CreateOrUpdateUserInput(BaseModel):
    """Input DTO for upserting a user from the auth callback."""

    matricula: str = Field(min_length=1, max_length=20)
    email: EmailStr
    role: Role
    full_name: str = ""
    programa: str = ""
    semestre: int | None = None
    gender: str = ""

    @field_validator("gender", mode="before")
    @classmethod
    def _normalize_gender(cls, v: Any) -> str:
        return _coerce_gender(v)


class SigaProfile(BaseModel):
    """Shape returned by the SIGA HTTP service."""

    matricula: str
    full_name: str
    email: EmailStr
    programa: str
    semestre: int | None = None
    # Optional single-letter code (``"H"`` / ``"M"``). Older SIGA payloads
    # may omit it entirely; the empty default keeps them valid. Unknown
    # codes are coerced to ``""`` at the boundary — see ``_coerce_gender``.
    gender: str = ""

    @field_validator("gender", mode="before")
    @classmethod
    def _normalize_gender(cls, v: Any) -> str:
        return _coerce_gender(v)
