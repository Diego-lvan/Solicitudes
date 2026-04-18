"""HTTP-backed SIGA client."""
from __future__ import annotations

import logging

import requests

from usuarios.exceptions import SigaUnavailable, UserNotFound
from usuarios.schemas import SigaProfile
from usuarios.services.siga.interface import SigaService


class HttpSigaService(SigaService):
    """Calls SIGA's REST endpoint with a hard timeout and maps failures to ``SigaUnavailable``."""

    def __init__(self, *, base_url: str, timeout_seconds: float, logger: logging.Logger) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._logger = logger

    def fetch_profile(self, matricula: str) -> SigaProfile:
        url = f"{self._base_url}/alumnos/{matricula}"
        try:
            response = requests.get(url, timeout=self._timeout)
        except requests.RequestException as exc:
            # Covers Timeout, ConnectionError, MissingSchema, InvalidURL, etc.
            self._logger.warning("siga.unreachable matricula=%s err=%s", matricula, exc)
            raise SigaUnavailable(str(exc)) from exc

        if response.status_code == 404:
            raise UserNotFound(f"siga: matricula={matricula}")
        if not response.ok:
            self._logger.warning(
                "siga.bad_status matricula=%s status=%s", matricula, response.status_code
            )
            raise SigaUnavailable(f"status={response.status_code}")

        try:
            return SigaProfile.model_validate(response.json())
        except ValueError as exc:
            self._logger.warning("siga.bad_payload matricula=%s err=%s", matricula, exc)
            raise SigaUnavailable("invalid payload") from exc
