from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory
from django.views import View

from _shared.exceptions import AuthenticationRequired, Unauthorized
from usuarios.constants import Role
from usuarios.permissions import (
    AdminRequiredMixin,
    AlumnoRequiredMixin,
    DocenteRequiredMixin,
    LoginRequiredMixin,
    PersonalRequiredMixin,
)


class _Echo(View):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return HttpResponse("ok")


def _make_request(*, authenticated: bool, role: Role | None = None) -> HttpRequest:
    rf = RequestFactory()
    request = rf.get("/x/")
    user = SimpleNamespace(
        is_authenticated=authenticated,
        is_anonymous=not authenticated,
        role=role.value if role else None,
    )
    request.user = user  # type: ignore[assignment]
    return request


def test_login_required_allows_authenticated() -> None:
    class V(LoginRequiredMixin, _Echo):
        pass

    response = V.as_view()(_make_request(authenticated=True, role=Role.ALUMNO))
    assert response.status_code == 200


def test_login_required_rejects_anonymous() -> None:
    class V(LoginRequiredMixin, _Echo):
        pass

    with pytest.raises(AuthenticationRequired):
        V.as_view()(_make_request(authenticated=False))


@pytest.mark.parametrize(
    ("mixin", "good_role", "bad_role"),
    [
        (AlumnoRequiredMixin, Role.ALUMNO, Role.DOCENTE),
        (DocenteRequiredMixin, Role.DOCENTE, Role.ALUMNO),
        (PersonalRequiredMixin, Role.CONTROL_ESCOLAR, Role.ALUMNO),
        (PersonalRequiredMixin, Role.RESPONSABLE_PROGRAMA, Role.DOCENTE),
        (AdminRequiredMixin, Role.ADMIN, Role.ALUMNO),
    ],
)
def test_role_mixins_allow_match_and_reject_mismatch(
    mixin: type, good_role: Role, bad_role: Role
) -> None:
    class V(mixin, _Echo):  # type: ignore[misc]
        pass

    assert V.as_view()(_make_request(authenticated=True, role=good_role)).status_code == 200
    with pytest.raises(Unauthorized):
        V.as_view()(_make_request(authenticated=True, role=bad_role))


def test_role_mixins_reject_anonymous() -> None:
    class V(AlumnoRequiredMixin, _Echo):
        pass

    with pytest.raises(AuthenticationRequired):
        V.as_view()(_make_request(authenticated=False))
