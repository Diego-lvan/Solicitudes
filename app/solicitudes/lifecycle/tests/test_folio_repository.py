"""Tests for OrmFolioRepository — atomic per-year sequence allocation."""
from __future__ import annotations

import pytest

from solicitudes.lifecycle.repositories.folio.implementation import (
    OrmFolioRepository,
)
from solicitudes.models import FolioCounter


@pytest.fixture
def repo() -> OrmFolioRepository:
    return OrmFolioRepository()


@pytest.mark.django_db
def test_allocate_creates_counter_and_returns_one_first(
    repo: OrmFolioRepository,
) -> None:
    n = repo.allocate(2026)
    assert n == 1
    counter = FolioCounter.objects.get(year=2026)
    assert counter.last == 1


@pytest.mark.django_db
def test_allocate_is_monotonic_within_year(repo: OrmFolioRepository) -> None:
    seq = [repo.allocate(2026) for _ in range(5)]
    assert seq == [1, 2, 3, 4, 5]


@pytest.mark.django_db
def test_allocate_per_year_independent(repo: OrmFolioRepository) -> None:
    repo.allocate(2026)
    repo.allocate(2026)
    repo.allocate(2027)
    assert FolioCounter.objects.get(year=2026).last == 2
    assert FolioCounter.objects.get(year=2027).last == 1
