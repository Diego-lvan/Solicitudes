"""Abstract SIGA client — fetches academic profile data for a matricula."""
from __future__ import annotations

from abc import ABC, abstractmethod

from usuarios.schemas import SigaProfile


class SigaService(ABC):
    """Adapter for the university's SIGA HTTP API."""

    @abstractmethod
    def fetch_profile(self, matricula: str) -> SigaProfile:
        """Return the full academic profile for ``matricula``.

        Raises:
            UserNotFound: SIGA returned 404.
            SigaUnavailable: timeout, connection error, or non-2xx response.
        """
