from __future__ import annotations

import pytest

from _shared.pagination import PageRequest
from mentores.constants import MentorSource
from mentores.exceptions import MentorNotFound
from mentores.models import Mentor
from mentores.repositories.mentor import OrmMentorRepository, UpsertOutcome
from mentores.schemas import MentorUpsertInput
from mentores.tests.factories import make_admin_user, make_mentor


@pytest.fixture
def repo() -> OrmMentorRepository:
    return OrmMentorRepository()


@pytest.mark.django_db
def test_get_by_matricula_returns_dto(repo: OrmMentorRepository) -> None:
    admin = make_admin_user()
    make_mentor(matricula="12345678", creado_por=admin)
    dto = repo.get_by_matricula("12345678")
    assert dto.matricula == "12345678"
    assert dto.activo is True
    assert dto.fuente is MentorSource.MANUAL


@pytest.mark.django_db
def test_get_by_matricula_raises_when_missing(repo: OrmMentorRepository) -> None:
    with pytest.raises(MentorNotFound):
        repo.get_by_matricula("99999999")


@pytest.mark.django_db
def test_exists_active_true_for_active_row(repo: OrmMentorRepository) -> None:
    make_mentor(matricula="12345678", activo=True)
    assert repo.exists_active("12345678") is True


@pytest.mark.django_db
def test_exists_active_false_for_inactive_row(repo: OrmMentorRepository) -> None:
    make_mentor(matricula="12345678", activo=False)
    assert repo.exists_active("12345678") is False


@pytest.mark.django_db
def test_exists_active_false_for_missing_row(repo: OrmMentorRepository) -> None:
    assert repo.exists_active("99999999") is False


@pytest.mark.django_db
def test_upsert_inserts_when_absent(repo: OrmMentorRepository) -> None:
    admin = make_admin_user(matricula="ADM1")
    dto, outcome = repo.upsert(
        MentorUpsertInput(
            matricula="12345678",
            fuente=MentorSource.MANUAL,
            nota="Mentor de programa X",
            creado_por_matricula=admin.matricula,
        )
    )
    assert outcome is UpsertOutcome.INSERTED
    assert dto.matricula == "12345678"
    assert dto.activo is True
    assert dto.nota == "Mentor de programa X"
    assert Mentor.objects.count() == 1


@pytest.mark.django_db
def test_upsert_returns_already_active_when_row_active(repo: OrmMentorRepository) -> None:
    admin = make_admin_user(matricula="ADM1")
    make_mentor(matricula="12345678", activo=True, creado_por=admin)
    dto, outcome = repo.upsert(
        MentorUpsertInput(
            matricula="12345678",
            fuente=MentorSource.CSV,
            creado_por_matricula=admin.matricula,
        )
    )
    assert outcome is UpsertOutcome.ALREADY_ACTIVE
    assert dto.activo is True
    # Source must NOT be overwritten on a no-op
    assert dto.fuente is MentorSource.MANUAL


@pytest.mark.django_db
def test_upsert_reactivates_inactive_row(repo: OrmMentorRepository) -> None:
    from datetime import UTC, datetime

    admin = make_admin_user(matricula="ADM1")
    inactive = make_mentor(
        matricula="12345678",
        activo=False,
        fuente=MentorSource.MANUAL.value,
        creado_por=admin,
    )
    inactive.fecha_baja = datetime(2025, 1, 1, tzinfo=UTC)
    inactive.save(update_fields=["fecha_baja"])
    dto, outcome = repo.upsert(
        MentorUpsertInput(
            matricula="12345678",
            fuente=MentorSource.CSV,
            nota="reimport",
            creado_por_matricula=admin.matricula,
        )
    )
    assert outcome is UpsertOutcome.REACTIVATED
    assert dto.activo is True
    assert dto.fecha_baja is None
    assert dto.fuente is MentorSource.CSV
    assert dto.nota == "reimport"


@pytest.mark.django_db
def test_deactivate_sets_inactive_and_fecha_baja(repo: OrmMentorRepository) -> None:
    make_mentor(matricula="12345678", activo=True)
    dto = repo.deactivate("12345678")
    assert dto.activo is False
    assert dto.fecha_baja is not None
    persisted = Mentor.objects.get(pk="12345678")
    assert persisted.activo is False
    assert persisted.fecha_baja is not None


@pytest.mark.django_db
def test_deactivate_idempotent_on_inactive(repo: OrmMentorRepository) -> None:
    make_mentor(matricula="12345678", activo=False)
    dto = repo.deactivate("12345678")
    assert dto.activo is False


@pytest.mark.django_db
def test_deactivate_raises_when_missing(repo: OrmMentorRepository) -> None:
    with pytest.raises(MentorNotFound):
        repo.deactivate("99999999")


@pytest.mark.django_db
def test_list_only_active_excludes_deactivated(repo: OrmMentorRepository) -> None:
    make_mentor(matricula="A1", activo=True)
    make_mentor(matricula="A2", activo=False)
    make_mentor(matricula="A3", activo=True)
    page = repo.list(only_active=True, page=PageRequest(page=1, page_size=10))
    assert [m.matricula for m in page.items] == ["A1", "A3"]
    assert page.total == 2


@pytest.mark.django_db
def test_list_includes_inactive_when_only_active_false(repo: OrmMentorRepository) -> None:
    make_mentor(matricula="A1", activo=True)
    make_mentor(matricula="A2", activo=False)
    page = repo.list(only_active=False, page=PageRequest(page=1, page_size=10))
    assert page.total == 2


@pytest.mark.django_db
def test_list_pagination(repo: OrmMentorRepository) -> None:
    for i in range(5):
        make_mentor(matricula=f"A{i}", activo=True)
    page1 = repo.list(only_active=True, page=PageRequest(page=1, page_size=2))
    assert [m.matricula for m in page1.items] == ["A0", "A1"]
    assert page1.total == 5
    assert page1.has_next is True
    page3 = repo.list(only_active=True, page=PageRequest(page=3, page_size=2))
    assert [m.matricula for m in page3.items] == ["A4"]
    assert page3.has_next is False
