"""Tests for DefaultFolioService — thin formatter on top of allocator."""
from __future__ import annotations

from solicitudes.lifecycle.services.folio_service.implementation import (
    DefaultFolioService,
)
from solicitudes.lifecycle.tests.fakes import InMemoryFolioRepository


def test_next_folio_formats_to_canonical_string() -> None:
    svc = DefaultFolioService(folio_repository=InMemoryFolioRepository())
    assert svc.next_folio(year=2026) == "SOL-2026-00001"
    assert svc.next_folio(year=2026) == "SOL-2026-00002"
    assert svc.next_folio(year=2027) == "SOL-2027-00001"


def test_next_folio_pads_to_five_digits() -> None:
    repo = InMemoryFolioRepository()
    repo._counters[2026] = 99
    svc = DefaultFolioService(folio_repository=repo)
    assert svc.next_folio(year=2026) == "SOL-2026-00100"
