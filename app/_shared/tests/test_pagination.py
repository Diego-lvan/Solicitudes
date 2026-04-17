from __future__ import annotations

import pytest
from pydantic import ValidationError

from _shared.pagination import Page, PageRequest


def test_page_request_defaults() -> None:
    req = PageRequest()
    assert req.page == 1
    assert req.page_size == 20
    assert req.offset == 0


def test_page_request_offset() -> None:
    assert PageRequest(page=3, page_size=10).offset == 20


@pytest.mark.parametrize("bad", [{"page": 0}, {"page_size": 0}, {"page_size": 200}])
def test_page_request_validates(bad: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        PageRequest(**bad)


def test_page_computes_total_pages() -> None:
    page = Page[int](items=[1, 2, 3], total=25, page=1, page_size=10)
    assert page.total_pages == 3
    assert page.has_next is True
    assert page.has_prev is False


def test_page_last_page() -> None:
    page = Page[int](items=[1], total=21, page=3, page_size=10)
    assert page.total_pages == 3
    assert page.has_next is False
    assert page.has_prev is True


def test_page_empty() -> None:
    page = Page[int](items=[], total=0, page=1, page_size=10)
    assert page.total_pages == 0
    assert page.has_next is False
    assert page.has_prev is False


def test_page_single_page() -> None:
    page = Page[int](items=[1, 2], total=2, page=1, page_size=10)
    assert page.total_pages == 1
    assert page.has_next is False
    assert page.has_prev is False
