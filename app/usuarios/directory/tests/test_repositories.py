"""Tests for :class:`OrmUserDirectoryRepository`."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.utils import timezone

from usuarios.constants import Role
from usuarios.directory.repositories.user_directory import (
    OrmUserDirectoryRepository,
)
from usuarios.directory.schemas import UserListFilters
from usuarios.exceptions import UserNotFound
from usuarios.tests.factories import make_user


@pytest.fixture
def repo() -> OrmUserDirectoryRepository:
    return OrmUserDirectoryRepository()


# ---------------------------------------------------------------------------
# list — filters
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_no_filters_returns_all_ordered_by_role_then_matricula(
    repo: OrmUserDirectoryRepository,
) -> None:
    make_user(matricula="Z9", role=Role.ALUMNO.value)
    make_user(matricula="A1", role=Role.ALUMNO.value)
    make_user(matricula="B2", role=Role.ADMIN.value)
    page = repo.list(UserListFilters(), page_size=10)
    assert page.total == 3
    assert [item.matricula for item in page.items] == ["B2", "A1", "Z9"]


@pytest.mark.django_db
def test_list_role_filter_returns_only_that_role(
    repo: OrmUserDirectoryRepository,
) -> None:
    make_user(matricula="A1", role=Role.ALUMNO.value)
    make_user(matricula="D1", role=Role.DOCENTE.value)
    page = repo.list(UserListFilters(role=Role.DOCENTE), page_size=10)
    assert page.total == 1
    assert page.items[0].matricula == "D1"


@pytest.mark.django_db
def test_list_q_matches_matricula_substring_case_insensitive(
    repo: OrmUserDirectoryRepository,
) -> None:
    make_user(matricula="ABC123", role=Role.ALUMNO.value)
    make_user(matricula="XYZ789", role=Role.ALUMNO.value)
    page = repo.list(UserListFilters(q="abc"), page_size=10)
    assert page.total == 1
    assert page.items[0].matricula == "ABC123"


@pytest.mark.django_db
def test_list_q_matches_full_name(repo: OrmUserDirectoryRepository) -> None:
    make_user(matricula="A1", full_name="Juan Pérez", role=Role.ALUMNO.value)
    make_user(matricula="A2", full_name="María López", role=Role.ALUMNO.value)
    page = repo.list(UserListFilters(q="pérez"), page_size=10)
    assert [item.matricula for item in page.items] == ["A1"]


@pytest.mark.django_db
def test_list_q_matches_email(repo: OrmUserDirectoryRepository) -> None:
    make_user(matricula="A1", email="alice@uaz.edu.mx", role=Role.ALUMNO.value)
    make_user(matricula="A2", email="bob@uaz.edu.mx", role=Role.ALUMNO.value)
    page = repo.list(UserListFilters(q="ALICE"), page_size=10)
    assert [item.matricula for item in page.items] == ["A1"]


@pytest.mark.django_db
def test_list_role_and_q_combined(repo: OrmUserDirectoryRepository) -> None:
    make_user(matricula="A1", full_name="Ana", role=Role.ALUMNO.value)
    make_user(matricula="A2", full_name="Ana", role=Role.DOCENTE.value)
    page = repo.list(
        UserListFilters(role=Role.ALUMNO, q="ana"), page_size=10
    )
    assert [item.matricula for item in page.items] == ["A1"]


# ---------------------------------------------------------------------------
# list — pagination
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_paginates_by_page_size(repo: OrmUserDirectoryRepository) -> None:
    for i in range(7):
        make_user(matricula=f"A{i:02d}", role=Role.ALUMNO.value)
    page1 = repo.list(UserListFilters(page=1), page_size=3)
    page2 = repo.list(UserListFilters(page=2), page_size=3)
    page3 = repo.list(UserListFilters(page=3), page_size=3)
    assert page1.total == page2.total == page3.total == 7
    assert [i.matricula for i in page1.items] == ["A00", "A01", "A02"]
    assert [i.matricula for i in page2.items] == ["A03", "A04", "A05"]
    assert [i.matricula for i in page3.items] == ["A06"]
    assert page1.has_next is True
    assert page3.has_next is False


@pytest.mark.django_db
def test_list_past_end_returns_empty(repo: OrmUserDirectoryRepository) -> None:
    make_user(matricula="A1", role=Role.ALUMNO.value)
    page = repo.list(UserListFilters(page=99), page_size=10)
    assert page.total == 1
    assert page.items == []


@pytest.mark.django_db
def test_list_empty_database(repo: OrmUserDirectoryRepository) -> None:
    page = repo.list(UserListFilters(), page_size=10)
    assert page.total == 0
    assert page.items == []
    assert page.total_pages == 0


# ---------------------------------------------------------------------------
# get_detail
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_detail_returns_full_user_with_is_mentor_none(
    repo: OrmUserDirectoryRepository,
) -> None:
    last_login = timezone.now()
    make_user(
        matricula="A1",
        email="a1@uaz.edu.mx",
        full_name="Ana",
        role=Role.ALUMNO.value,
        programa="Ing. en Software",
        semestre=4,
        gender="M",
        last_login_at=last_login,
    )
    detail = repo.get_detail("A1")
    assert detail.matricula == "A1"
    assert detail.full_name == "Ana"
    assert detail.email == "a1@uaz.edu.mx"
    assert detail.role is Role.ALUMNO
    assert detail.programa == "Ing. en Software"
    assert detail.semestre == 4
    assert detail.gender == "M"
    assert detail.is_mentor is None
    assert detail.last_login_at == last_login


@pytest.mark.django_db
def test_get_detail_unknown_matricula_raises(
    repo: OrmUserDirectoryRepository,
) -> None:
    with pytest.raises(UserNotFound):
        repo.get_detail("NOPE")
