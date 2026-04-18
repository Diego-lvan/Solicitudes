from __future__ import annotations

from _shared.auth import JwtClaims
from usuarios.services.siga.jwt_fallback import JwtFallbackSigaService


def test_jwt_fallback_builds_profile_from_claims() -> None:
    captured: dict[str, JwtClaims] = {
        "A1": JwtClaims(sub="A1", email="a1@uaz.edu.mx", rol="alumno", exp=0, iat=0),
    }
    service = JwtFallbackSigaService(claims_provider=lambda matricula: captured[matricula])
    profile = service.fetch_profile("A1")
    assert profile.matricula == "A1"
    assert profile.email == "a1@uaz.edu.mx"
    assert profile.full_name == ""
    assert profile.programa == ""
    assert profile.semestre is None
