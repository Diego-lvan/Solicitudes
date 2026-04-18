from __future__ import annotations

import pytest

from _shared.auth import JwtClaims
from usuarios.constants import Role
from usuarios.exceptions import RoleNotRecognized
from usuarios.services.role_resolver import JwtRoleResolver


def _claims(rol: str) -> JwtClaims:
    return JwtClaims(sub="A1", email="a1@uaz.edu.mx", rol=rol, exp=0, iat=0)


@pytest.mark.parametrize(
    ("provider_rol", "expected"),
    [
        ("alumno", Role.ALUMNO),
        ("ALUMNO", Role.ALUMNO),  # case-insensitive
        ("docente", Role.DOCENTE),
        ("control_escolar", Role.CONTROL_ESCOLAR),
        ("resp_programa", Role.RESPONSABLE_PROGRAMA),
        ("admin", Role.ADMIN),
    ],
)
def test_jwt_role_resolver_maps_known_roles(provider_rol: str, expected: Role) -> None:
    assert JwtRoleResolver().resolve(_claims(provider_rol)) is expected


def test_jwt_role_resolver_rejects_unknown_role() -> None:
    with pytest.raises(RoleNotRecognized):
        JwtRoleResolver().resolve(_claims("rector"))
