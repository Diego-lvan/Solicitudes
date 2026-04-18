"""Pydantic DTOs for the usuarios feature — boundary types between layers."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from usuarios.constants import Role


class UserDTO(BaseModel):
    """Frozen DTO returned by repositories and services to the view layer."""

    model_config = ConfigDict(frozen=True)

    matricula: str
    email: EmailStr
    role: Role
    full_name: str = ""
    programa: str = ""
    semestre: int | None = None
    is_mentor: bool = False  # populated by mentores service when needed; never persisted on User


class CreateOrUpdateUserInput(BaseModel):
    """Input DTO for upserting a user from the auth callback."""

    matricula: str = Field(min_length=1, max_length=20)
    email: EmailStr
    role: Role
    full_name: str = ""
    programa: str = ""
    semestre: int | None = None


class SigaProfile(BaseModel):
    """Shape returned by the SIGA HTTP service."""

    matricula: str
    full_name: str
    email: EmailStr
    programa: str
    semestre: int | None = None
