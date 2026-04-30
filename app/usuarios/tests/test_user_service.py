from __future__ import annotations

import logging
from datetime import UTC, datetime

import pytest
from freezegun import freeze_time

from _shared.auth import JwtClaims
from usuarios.constants import Role
from usuarios.exceptions import UserNotFound
from usuarios.schemas import SigaProfile, UserDTO
from usuarios.services.user_service import DefaultUserService
from usuarios.tests.fakes import FakeRoleResolver, FakeSigaService, InMemoryUserRepository


def _make_service(
    *,
    repo: InMemoryUserRepository | None = None,
    role: Role = Role.ALUMNO,
    siga: FakeSigaService | None = None,
) -> tuple[DefaultUserService, InMemoryUserRepository, FakeSigaService]:
    repo = repo or InMemoryUserRepository()
    siga = siga or FakeSigaService(unavailable=True)
    service = DefaultUserService(
        user_repository=repo,
        role_resolver=FakeRoleResolver(role),
        siga_service=siga,
        logger=logging.getLogger("test.user_service"),
    )
    return service, repo, siga


def _claims(sub: str = "A1", email: str = "a1@uaz.edu.mx") -> JwtClaims:
    return JwtClaims(sub=sub, email=email, rol="alumno", exp=0, iat=0)


@freeze_time("2026-04-25T12:00:00+00:00")
def test_get_or_create_from_claims_inserts_and_stamps_login() -> None:
    service, repo, _ = _make_service(role=Role.DOCENTE)
    dto = service.get_or_create_from_claims(_claims())
    assert dto.matricula == "A1"
    assert dto.role is Role.DOCENTE
    assert repo.last_login_for("A1") == datetime(2026, 4, 25, 12, 0, tzinfo=UTC)


def test_get_or_create_from_claims_updates_role_on_change() -> None:
    service, repo, _ = _make_service(role=Role.ALUMNO)
    service.get_or_create_from_claims(_claims())
    service2, _, _ = _make_service(repo=repo, role=Role.DOCENTE)
    dto = service2.get_or_create_from_claims(_claims())
    assert dto.role is Role.DOCENTE


def test_get_by_matricula_raises_when_missing() -> None:
    service, _, _ = _make_service()
    with pytest.raises(UserNotFound):
        service.get_by_matricula("missing")


def test_hydrate_from_siga_writes_profile_when_available() -> None:
    profile = SigaProfile(
        matricula="A1",
        full_name="Ada Lovelace",
        email="ada@uaz.edu.mx",
        programa="ISW",
        semestre=4,
    )
    service, _repo, siga = _make_service(siga=FakeSigaService(profile=profile))
    service.get_or_create_from_claims(_claims(email="jwt@uaz.edu.mx"))

    enriched = service.hydrate_from_siga("A1")
    assert enriched.full_name == "Ada Lovelace"
    assert enriched.programa == "ISW"
    assert enriched.semestre == 4
    # Email is owned by the auth provider; SIGA's email must NOT overwrite it.
    assert enriched.email == "jwt@uaz.edu.mx"
    assert siga.calls == ["A1"]


def test_hydrate_from_siga_swallows_unavailable_and_returns_existing() -> None:
    service, _, _ = _make_service(siga=FakeSigaService(unavailable=True))
    service.get_or_create_from_claims(_claims())
    dto = service.hydrate_from_siga("A1")
    assert isinstance(dto, UserDTO)
    assert dto.full_name == ""  # unchanged


def test_hydrate_from_siga_raises_user_not_found_when_user_unknown() -> None:
    service, _, _ = _make_service()
    with pytest.raises(UserNotFound):
        service.hydrate_from_siga("NOPE")


def test_list_by_role_delegates_to_repository() -> None:
    from usuarios.schemas import CreateOrUpdateUserInput

    service, repo, _ = _make_service()
    repo.upsert(CreateOrUpdateUserInput(matricula="C1", email="c1@x.com", role=Role.CONTROL_ESCOLAR))
    repo.upsert(CreateOrUpdateUserInput(matricula="A1", email="a1@x.com", role=Role.ALUMNO))

    result = service.list_by_role(Role.CONTROL_ESCOLAR)

    assert [u.matricula for u in result] == ["C1"]
