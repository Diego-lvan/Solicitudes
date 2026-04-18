from __future__ import annotations

from usuarios.constants import PROVIDER_ROLE_MAP, Role


def test_role_is_string_enum_with_value_equality() -> None:
    assert Role.ALUMNO.value == "ALUMNO"
    assert Role("ALUMNO") is Role.ALUMNO


def test_role_choices_are_human_readable() -> None:
    choices = dict(Role.choices())
    assert choices["CONTROL_ESCOLAR"] == "Control Escolar"
    assert choices["RESPONSABLE_PROGRAMA"] == "Responsable Programa"
    assert set(choices) == {m.value for m in Role}


def test_provider_role_map_covers_every_role() -> None:
    assert set(PROVIDER_ROLE_MAP.values()) == set(Role)
