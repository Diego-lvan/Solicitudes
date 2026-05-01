"""Tests for :class:`DefaultUserDirectoryService`."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import pytest

from _shared.pagination import Page
from usuarios.constants import Role
from usuarios.directory.repositories.user_directory.interface import (
    UserDirectoryRepository,
)
from usuarios.directory.schemas import UserDetail, UserListFilters, UserListItem
from usuarios.directory.services.user_directory import DefaultUserDirectoryService
from usuarios.exceptions import UserNotFound


class _FakeRepo(UserDirectoryRepository):
    def __init__(self, *, detail: UserDetail | None = None) -> None:
        self._detail = detail
        self.list_calls: list[tuple[UserListFilters, int]] = []

    def list(
        self, filters: UserListFilters, page_size: int
    ) -> Page[UserListItem]:
        self.list_calls.append((filters, page_size))
        return Page[UserListItem](items=[], total=0, page=filters.page, page_size=page_size)

    def get_detail(self, matricula: str) -> UserDetail:
        if self._detail is None:
            raise UserNotFound(f"matricula={matricula}")
        return self._detail


class _FakeMentor:
    def __init__(self, *, result: bool | None = None, raises: Exception | None = None):
        self._result = result
        self._raises = raises
        self.calls: list[str] = []

    def is_mentor(self, matricula: str) -> bool:
        self.calls.append(matricula)
        if self._raises is not None:
            raise self._raises
        assert self._result is not None
        return self._result

    # Unused abstract methods
    def __getattr__(self, name: str) -> Any:
        raise AttributeError(name)


def _detail(**overrides: Any) -> UserDetail:
    base = dict(
        matricula="A1",
        full_name="Ana",
        email="a1@uaz.edu.mx",
        role=Role.ALUMNO,
        programa="Software",
        semestre=4,
        gender="M",
        is_mentor=None,
        last_login_at=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    base.update(overrides)
    return UserDetail(**base)  # type: ignore[arg-type]


def _build(repo: UserDirectoryRepository, mentor: Any) -> DefaultUserDirectoryService:
    return DefaultUserDirectoryService(
        directory_repository=repo,
        mentor_service=mentor,  # type: ignore[arg-type]
        page_size=25,
        logger=logging.getLogger("test"),
    )


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def test_list_delegates_to_repo_with_configured_page_size() -> None:
    repo = _FakeRepo()
    svc = _build(repo, _FakeMentor(result=False))
    filters = UserListFilters(role=Role.ALUMNO, q="ana", page=2)
    svc.list(filters)
    assert repo.list_calls == [(filters, 25)]


# ---------------------------------------------------------------------------
# get_detail — mentor overlay
# ---------------------------------------------------------------------------

def test_get_detail_overlays_is_mentor_true() -> None:
    repo = _FakeRepo(detail=_detail())
    mentor = _FakeMentor(result=True)
    detail = _build(repo, mentor).get_detail("A1")
    assert detail.is_mentor is True
    assert mentor.calls == ["A1"]


def test_get_detail_overlays_is_mentor_false() -> None:
    repo = _FakeRepo(detail=_detail())
    detail = _build(repo, _FakeMentor(result=False)).get_detail("A1")
    assert detail.is_mentor is False


def test_get_detail_swallows_mentor_exception_and_sets_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    repo = _FakeRepo(detail=_detail())
    mentor = _FakeMentor(raises=RuntimeError("boom"))
    with caplog.at_level("WARNING"):
        detail = _build(repo, mentor).get_detail("A1")
    assert detail.is_mentor is None
    assert any(
        "mentor_service.is_mentor failed" in rec.getMessage() for rec in caplog.records
    )


def test_get_detail_propagates_user_not_found_without_calling_mentor() -> None:
    repo = _FakeRepo(detail=None)
    mentor = _FakeMentor(result=True)
    with pytest.raises(UserNotFound):
        _build(repo, mentor).get_detail("NOPE")
    assert mentor.calls == []
