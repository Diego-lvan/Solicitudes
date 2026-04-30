from __future__ import annotations

import logging

from notificaciones.services.recipient_resolver import DefaultRecipientResolver
from usuarios.constants import Role
from usuarios.schemas import CreateOrUpdateUserInput
from usuarios.services.user_service import DefaultUserService
from usuarios.tests.fakes import (
    FakeRoleResolver,
    FakeSigaService,
    InMemoryUserRepository,
)


def _service() -> tuple[DefaultUserService, InMemoryUserRepository]:
    repo = InMemoryUserRepository()
    svc = DefaultUserService(
        user_repository=repo,
        role_resolver=FakeRoleResolver(),
        siga_service=FakeSigaService(),
        logger=logging.getLogger("test"),
    )
    return svc, repo


def test_resolves_users_by_role() -> None:
    svc, repo = _service()
    repo.upsert(CreateOrUpdateUserInput(matricula="C1", email="c1@x.com", role=Role.CONTROL_ESCOLAR))
    repo.upsert(CreateOrUpdateUserInput(matricula="C2", email="c2@x.com", role=Role.CONTROL_ESCOLAR))
    repo.upsert(CreateOrUpdateUserInput(matricula="A1", email="a1@x.com", role=Role.ALUMNO))

    resolver = DefaultRecipientResolver(user_service=svc)
    assert [u.matricula for u in resolver.resolve_by_role(Role.CONTROL_ESCOLAR)] == ["C1", "C2"]


def test_returns_empty_when_no_users_match() -> None:
    svc, _ = _service()
    resolver = DefaultRecipientResolver(user_service=svc)
    assert resolver.resolve_by_role(Role.CONTROL_ESCOLAR) == []
