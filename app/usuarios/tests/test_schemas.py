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


# ---- gender coercion (Important #2 from review) ------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("H", "H"),
        ("M", "M"),
        ("h", "H"),  # lower-case normalises to upper
        ("m", "M"),
        (" H ", "H"),  # whitespace stripped
        ("", ""),
        (None, ""),
        ("X", ""),  # unknown code → empty (the regression case)
        ("F", ""),  # English-localised SIGA payload coerces, doesn't crash
        ("Hombre", ""),  # full word, only single-letter codes are accepted
        (1, ""),  # non-string nonsense coerces silently
    ],
)
def test_gender_coerced_at_dto_boundary(raw: object, expected: str) -> None:
    """The DTO normalises any unknown SIGA gender code to ``""`` so PDF
    plantillas branching on ``solicitante.genero`` never see garbage."""
    dto = UserDTO(
        matricula="123",
        email="a@example.com",
        role=Role.ALUMNO,
        gender=raw,  # type: ignore[arg-type]
    )
    assert dto.gender == expected
    profile = SigaProfile(
        matricula="123",
        full_name="x",
        email="a@example.com",
        programa="x",
        gender=raw,  # type: ignore[arg-type]
    )
    assert profile.gender == expected
    inp = CreateOrUpdateUserInput(
        matricula="123",
        email="a@example.com",
        role=Role.ALUMNO,
        gender=raw,  # type: ignore[arg-type]
    )
    assert inp.gender == expected
