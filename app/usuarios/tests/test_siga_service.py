from __future__ import annotations

import logging

import pytest
import requests
import responses

from usuarios.exceptions import SigaUnavailable, UserNotFound
from usuarios.services.siga import HttpSigaService

BASE_URL = "https://siga.example.com"


@pytest.fixture
def service() -> HttpSigaService:
    return HttpSigaService(
        base_url=BASE_URL,
        timeout_seconds=1.0,
        logger=logging.getLogger("test.siga"),
    )


@responses.activate
def test_fetch_profile_returns_dto(service: HttpSigaService) -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/alumnos/A1",
        json={
            "matricula": "A1",
            "full_name": "Ada Lovelace",
            "email": "ada@uaz.edu.mx",
            "programa": "ISW",
            "semestre": 4,
        },
        status=200,
    )
    profile = service.fetch_profile("A1")
    assert profile.full_name == "Ada Lovelace"
    assert profile.semestre == 4


@responses.activate
def test_fetch_profile_raises_user_not_found_on_404(service: HttpSigaService) -> None:
    responses.add(responses.GET, f"{BASE_URL}/alumnos/MISSING", status=404)
    with pytest.raises(UserNotFound):
        service.fetch_profile("MISSING")


@responses.activate
def test_fetch_profile_raises_unavailable_on_5xx(service: HttpSigaService) -> None:
    responses.add(responses.GET, f"{BASE_URL}/alumnos/A1", status=503)
    with pytest.raises(SigaUnavailable):
        service.fetch_profile("A1")


@responses.activate
def test_fetch_profile_raises_unavailable_on_timeout(service: HttpSigaService) -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/alumnos/A1",
        body=requests.Timeout("slow"),
    )
    with pytest.raises(SigaUnavailable):
        service.fetch_profile("A1")


@responses.activate
def test_fetch_profile_raises_unavailable_on_connection_error(service: HttpSigaService) -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/alumnos/A1",
        body=requests.ConnectionError("no route"),
    )
    with pytest.raises(SigaUnavailable):
        service.fetch_profile("A1")


@responses.activate
def test_fetch_profile_raises_unavailable_on_bad_payload(service: HttpSigaService) -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/alumnos/A1",
        json={"matricula": "A1"},  # missing required fields
        status=200,
    )
    with pytest.raises(SigaUnavailable):
        service.fetch_profile("A1")
