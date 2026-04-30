from __future__ import annotations

from datetime import UTC, datetime

import pytest

from usuarios.constants import Role
from usuarios.exceptions import UserNotFound
from usuarios.models import User
from usuarios.repositories.user import OrmUserRepository
from usuarios.schemas import CreateOrUpdateUserInput, UserDTO


@pytest.fixture
def repo() -> OrmUserRepository:
    return OrmUserRepository()


@pytest.mark.django_db
def test_upsert_inserts_when_absent(repo: OrmUserRepository) -> None:
    dto = repo.upsert(
        CreateOrUpdateUserInput(
            matricula="A1",
            email="a1@uaz.edu.mx",
            role=Role.ALUMNO,
            full_name="Ada Lovelace",
            programa="ISW",
            semestre=4,
        )
    )
    assert isinstance(dto, UserDTO)
    assert dto.matricula == "A1"
    assert dto.role is Role.ALUMNO
    assert dto.full_name == "Ada Lovelace"
    assert dto.semestre == 4
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_upsert_updates_when_present(repo: OrmUserRepository) -> None:
    repo.upsert(CreateOrUpdateUserInput(matricula="A1", email="a@x.com", role=Role.ALUMNO))
    dto = repo.upsert(
        CreateOrUpdateUserInput(
            matricula="A1",
            email="b@x.com",
            role=Role.DOCENTE,
            full_name="Renamed",
        )
    )
    assert dto.email == "b@x.com"
    assert dto.role is Role.DOCENTE
    assert dto.full_name == "Renamed"
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_upsert_preserves_semestre_when_input_is_none(repo: OrmUserRepository) -> None:
    repo.upsert(
        CreateOrUpdateUserInput(matricula="A1", email="a@x.com", role=Role.ALUMNO, semestre=3)
    )
    dto = repo.upsert(
        CreateOrUpdateUserInput(matricula="A1", email="a@x.com", role=Role.ALUMNO, semestre=None)
    )
    assert dto.semestre == 3


@pytest.mark.django_db
def test_upsert_preserves_cached_siga_fields_on_jwt_only_relogin(
    repo: OrmUserRepository,
) -> None:
    """Acceptance criterion: after SIGA hydration, a subsequent JWT-only login
    (which has no SIGA data) must NOT clobber the cached profile fields.

    Regression guard: this is the divergence the in-memory fake used to mask.
    """
    # First write: full SIGA-enriched profile.
    repo.upsert(
        CreateOrUpdateUserInput(
            matricula="A1",
            email="a@x.com",
            role=Role.ALUMNO,
            full_name="Ada Lovelace",
            programa="ISW",
            semestre=4,
        )
    )
    # Second write: JWT-only — no SIGA fields. Must preserve previous values.
    dto = repo.upsert(
        CreateOrUpdateUserInput(matricula="A1", email="a@x.com", role=Role.ALUMNO)
    )
    assert dto.full_name == "Ada Lovelace"
    assert dto.programa == "ISW"
    assert dto.semestre == 4


@pytest.mark.django_db
def test_get_by_matricula_returns_dto(repo: OrmUserRepository) -> None:
    repo.upsert(CreateOrUpdateUserInput(matricula="A1", email="a@x.com", role=Role.ADMIN))
    dto = repo.get_by_matricula("A1")
    assert dto.matricula == "A1"
    assert dto.role is Role.ADMIN


@pytest.mark.django_db
def test_get_by_matricula_raises_when_missing(repo: OrmUserRepository) -> None:
    with pytest.raises(UserNotFound):
        repo.get_by_matricula("MISSING")


@pytest.mark.django_db
def test_update_last_login_sets_timestamp(repo: OrmUserRepository) -> None:
    repo.upsert(CreateOrUpdateUserInput(matricula="A1", email="a@x.com", role=Role.ALUMNO))
    when = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    repo.update_last_login("A1", when=when)
    assert User.objects.get(pk="A1").last_login_at == when


@pytest.mark.django_db
def test_update_last_login_raises_when_missing(repo: OrmUserRepository) -> None:
    with pytest.raises(UserNotFound):
        repo.update_last_login("MISSING", when=datetime.now(tz=UTC))


@pytest.mark.django_db
def test_list_all_returns_dtos_ordered_by_role_then_matricula(
    repo: OrmUserRepository,
) -> None:
    repo.upsert(CreateOrUpdateUserInput(matricula="Z2", email="z2@x.com", role=Role.ADMIN))
    repo.upsert(CreateOrUpdateUserInput(matricula="A1", email="a1@x.com", role=Role.ALUMNO))
    repo.upsert(CreateOrUpdateUserInput(matricula="A2", email="a2@x.com", role=Role.ALUMNO))
    rows = repo.list_all()
    assert [r.matricula for r in rows] == ["Z2", "A1", "A2"]
    assert all(isinstance(r, UserDTO) for r in rows)


@pytest.mark.django_db
def test_list_all_returns_empty_list_on_empty_db(repo: OrmUserRepository) -> None:
    assert repo.list_all() == []


@pytest.mark.django_db
def test_list_all_respects_limit(repo: OrmUserRepository) -> None:
    for i in range(5):
        repo.upsert(
            CreateOrUpdateUserInput(
                matricula=f"L{i}", email=f"l{i}@x.com", role=Role.ALUMNO
            )
        )
    assert len(repo.list_all(limit=3)) == 3


@pytest.mark.django_db
def test_orm_and_in_memory_repos_produce_same_ordering() -> None:
    """Pin the contract: the two `UserRepository` impls must agree on the
    ``list_all`` ordering, so service-level tests against the fake cannot
    drift from the production behavior."""
    from usuarios.tests.fakes import InMemoryUserRepository

    inputs = [
        CreateOrUpdateUserInput(matricula="Z2", email="z2@x.com", role=Role.ADMIN),
        CreateOrUpdateUserInput(matricula="A2", email="a2@x.com", role=Role.ALUMNO),
        CreateOrUpdateUserInput(matricula="A1", email="a1@x.com", role=Role.ALUMNO),
        CreateOrUpdateUserInput(matricula="C1", email="c1@x.com", role=Role.DOCENTE),
    ]
    orm = OrmUserRepository()
    fake = InMemoryUserRepository()
    for dto in inputs:
        orm.upsert(dto)
        fake.upsert(dto)
    assert [r.matricula for r in orm.list_all()] == [
        r.matricula for r in fake.list_all()
    ]


@pytest.mark.django_db
def test_list_by_role_returns_only_matching_role(repo: OrmUserRepository) -> None:
    repo.upsert(CreateOrUpdateUserInput(matricula="A1", email="a1@x.com", role=Role.ALUMNO))
    repo.upsert(CreateOrUpdateUserInput(matricula="C1", email="c1@x.com", role=Role.CONTROL_ESCOLAR))
    repo.upsert(CreateOrUpdateUserInput(matricula="C2", email="c2@x.com", role=Role.CONTROL_ESCOLAR))

    rows = repo.list_by_role(Role.CONTROL_ESCOLAR)

    assert [r.matricula for r in rows] == ["C1", "C2"]
    assert all(r.role is Role.CONTROL_ESCOLAR for r in rows)


@pytest.mark.django_db
def test_list_by_role_excludes_users_with_empty_email(repo: OrmUserRepository) -> None:
    from usuarios.models import User

    repo.upsert(CreateOrUpdateUserInput(matricula="C1", email="c1@x.com", role=Role.CONTROL_ESCOLAR))
    User.objects.create(matricula="C2", email="", role=Role.CONTROL_ESCOLAR.value)

    rows = repo.list_by_role(Role.CONTROL_ESCOLAR)

    assert [r.matricula for r in rows] == ["C1"]


@pytest.mark.django_db
def test_list_by_role_returns_empty_when_no_matches(repo: OrmUserRepository) -> None:
    repo.upsert(CreateOrUpdateUserInput(matricula="A1", email="a1@x.com", role=Role.ALUMNO))
    assert repo.list_by_role(Role.CONTROL_ESCOLAR) == []
