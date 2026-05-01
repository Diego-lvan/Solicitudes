"""Pydantic DTOs for the admin user directory feature."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from usuarios.constants import Role


class UserListFilters(BaseModel):
    """Parsed querystring → repository input."""

    model_config = {"frozen": True}

    role: Role | None = None
    q: str = ""
    page: int = Field(default=1, ge=1)


class UserListItem(BaseModel):
    """One row in the directory list. Built by the repository."""

    model_config = {"frozen": True}

    matricula: str
    full_name: str
    role: Role
    programa: str
    email: str
    last_login_at: datetime | None


class UserDetail(BaseModel):
    """Full read-only detail. Built by the service (combines repo + mentor service)."""

    model_config = {"frozen": True}

    matricula: str
    full_name: str
    email: str
    role: Role
    programa: str
    semestre: int | None
    gender: str
    is_mentor: bool | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
