from __future__ import annotations

import logging

import pytest

from _shared.exceptions import DomainValidationError
from _shared.pagination import PageRequest
from mentores.constants import MentorSource
from mentores.exceptions import MentorAlreadyActive, MentorNotFound
from mentores.services.mentor_service import DefaultMentorService
from mentores.tests.fakes import InMemoryMentorRepository
from usuarios.constants import Role
from usuarios.schemas import UserDTO


def make_user_dto_admin(matricula: str = "ADM1") -> UserDTO:
    return UserDTO(matricula=matricula, email=f"{matricula.lower()}@x.com", role=Role.ADMIN)


@pytest.fixture
def repo() -> InMemoryMentorRepository:
    return InMemoryMentorRepository()


@pytest.fixture
def service(repo: InMemoryMentorRepository) -> DefaultMentorService:
    return DefaultMentorService(
        mentor_repository=repo,
        logger=logging.getLogger("test.mentor_service"),
    )


def test_is_mentor_true_for_active(service: DefaultMentorService, repo: InMemoryMentorRepository) -> None:
    repo._seed_active("12345678")
    assert service.is_mentor("12345678") is True


def test_is_mentor_false_for_missing(service: DefaultMentorService) -> None:
    assert service.is_mentor("12345678") is False


def test_add_inserts_new_mentor(service: DefaultMentorService) -> None:
    actor = make_user_dto_admin()
    dto = service.add(matricula="12345678", fuente=MentorSource.MANUAL, nota="x", actor=actor)
    assert dto.matricula == "12345678"
    assert dto.activo is True


def test_add_rejects_invalid_matricula_format(service: DefaultMentorService) -> None:
    actor = make_user_dto_admin()
    with pytest.raises(DomainValidationError) as exc_info:
        service.add(matricula="abc", fuente=MentorSource.MANUAL, nota="", actor=actor)
    assert "matricula" in exc_info.value.field_errors


def test_add_raises_already_active_on_duplicate(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    actor = make_user_dto_admin()
    repo._seed_active("12345678")
    with pytest.raises(MentorAlreadyActive):
        service.add(
            matricula="12345678", fuente=MentorSource.MANUAL, nota="", actor=actor
        )


def test_add_reactivates_inactive_silently(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    actor = make_user_dto_admin()
    # Seed inactive
    from datetime import UTC, datetime

    from mentores.schemas import MentorDTO

    repo._seed(
        MentorDTO(
            matricula="12345678",
            activo=False,
            fuente=MentorSource.CSV,
            nota="",
            fecha_alta=datetime(2025, 1, 1, tzinfo=UTC),
            fecha_baja=datetime(2025, 6, 1, tzinfo=UTC),
        )
    )
    dto = service.add(
        matricula="12345678", fuente=MentorSource.MANUAL, nota="back", actor=actor
    )
    assert dto.activo is True
    assert dto.fecha_baja is None


def test_deactivate_returns_dto(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    actor = make_user_dto_admin()
    repo._seed_active("12345678")
    dto = service.deactivate("12345678", actor)
    assert dto.activo is False


def test_deactivate_raises_when_missing(service: DefaultMentorService) -> None:
    actor = make_user_dto_admin()
    with pytest.raises(MentorNotFound):
        service.deactivate("99999999", actor)


def test_list_passes_through_to_repo(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    repo._seed_active("11111111")
    repo._seed_active("22222222")
    page = service.list(only_active=True, page=PageRequest(page=1, page_size=10))
    assert page.total == 2
    assert [m.matricula for m in page.items] == ["11111111", "22222222"]
