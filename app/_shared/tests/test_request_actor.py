"""Tests for :func:`_shared.request_actor.actor_from_request`."""
from __future__ import annotations

import pytest
from django.test import RequestFactory

from _shared.exceptions import AuthenticationRequired
from _shared.request_actor import actor_from_request
from usuarios.constants import Role
from usuarios.schemas import UserDTO


def _actor() -> UserDTO:
    return UserDTO(matricula="A1", email="a1@uaz.edu.mx", role=Role.ALUMNO)


def test_returns_typed_actor_when_present() -> None:
    request = RequestFactory().get("/")
    request.user_dto = _actor()  # type: ignore[attr-defined]
    assert actor_from_request(request).matricula == "A1"


def test_raises_authentication_required_when_actor_missing() -> None:
    # Models an anonymous request that slipped past the login mixin.
    request = RequestFactory().get("/")
    with pytest.raises(AuthenticationRequired):
        actor_from_request(request)
