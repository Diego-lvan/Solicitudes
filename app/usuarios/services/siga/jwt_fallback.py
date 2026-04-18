"""Deterministic JWT-only ``SigaService`` — used when SIGA is unreachable.

Returns a minimal :class:`SigaProfile` built from the data already in the JWT,
so callers always get a usable profile even with no network access.
"""
from __future__ import annotations

from collections.abc import Callable

from _shared.auth import JwtClaims
from usuarios.schemas import SigaProfile
from usuarios.services.siga.interface import SigaService

# Given a matricula, return the JwtClaims captured for the current request.
# Decoupled from Django so the fallback remains framework-free.
ClaimsProvider = Callable[[str], JwtClaims]


class JwtFallbackSigaService(SigaService):
    """Builds a profile straight from the JWT claims; never raises ``SigaUnavailable``."""

    def __init__(self, *, claims_provider: ClaimsProvider) -> None:
        self._claims_provider = claims_provider

    def fetch_profile(self, matricula: str) -> SigaProfile:
        claims = self._claims_provider(matricula)
        return SigaProfile(
            matricula=matricula,
            full_name="",
            email=claims.email,
            programa="",
            semestre=None,
        )
