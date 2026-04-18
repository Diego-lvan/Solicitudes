from __future__ import annotations

import pytest
from pydantic import ValidationError

from usuarios.constants import Role
from usuarios.schemas import CreateOrUpdateUserInput, SigaProfile, UserDTO


def test_user_dto_is_frozen() -> None:
    dto = UserDTO(matricula="123", email="a@example.com", role=Role.ALUMNO)
    with pytest.raises(ValidationError):
        dto.matricula = "456"  # type: ignore[misc]


def test_user_dto_defaults() -> None:
    dto = UserDTO(matricula="123", email="a@example.com", role=Role.ALUMNO)
    assert dto.full_name == ""
    assert dto.programa == ""
    assert dto.semestre is None
    assert dto.is_mentor is False


def test_create_or_update_user_input_rejects_blank_matricula() -> None:
    with pytest.raises(ValidationError):
        CreateOrUpdateUserInput(matricula="", email="a@example.com", role=Role.ALUMNO)


def test_create_or_update_user_input_rejects_bad_email() -> None:
    with pytest.raises(ValidationError):
        CreateOrUpdateUserInput(matricula="123", email="not-an-email", role=Role.ALUMNO)


def test_siga_profile_parses() -> None:
    profile = SigaProfile(
        matricula="123",
        full_name="Ada Lovelace",
        email="ada@uaz.edu.mx",
        programa="Ingeniería de Software",
        semestre=4,
    )
    assert profile.semestre == 4
