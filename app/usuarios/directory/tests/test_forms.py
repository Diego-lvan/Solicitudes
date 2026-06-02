"""Tests for :class:`DirectoryFilterForm.to_filters`."""
from __future__ import annotations

from usuarios.constants import Role
from usuarios.directory.forms.filter_form import DirectoryFilterForm


def _filters_from(qs: dict[str, str]):
    form = DirectoryFilterForm(qs)
    form.is_valid()
    return form.to_filters()


def test_blank_querystring_returns_defaults() -> None:
    f = _filters_from({})
    assert f.role is None
    assert f.q == ""
    assert f.page == 1


def test_valid_role_and_q_and_page() -> None:
    f = _filters_from({"role": "ALUMNO", "q": "  ana ", "page": "3"})
    assert f.role is Role.ALUMNO
    assert f.q == "ana"
    assert f.page == 3


def test_unknown_role_degrades_to_none() -> None:
    f = _filters_from({"role": "BOGUS"})
    assert f.role is None


def test_lowercase_role_degrades_to_none() -> None:
    # Choices are uppercase only.
    f = _filters_from({"role": "alumno"})
    assert f.role is None


def test_blank_q_after_strip_is_empty_string() -> None:
    f = _filters_from({"q": "   "})
    assert f.q == ""


def test_invalid_page_falls_back_to_one() -> None:
    f = _filters_from({"page": "abc"})
    assert f.page == 1


def test_zero_page_falls_back_to_one() -> None:
    f = _filters_from({"page": "0"})
    assert f.page == 1


def test_negative_page_falls_back_to_one() -> None:
    f = _filters_from({"page": "-3"})
    assert f.page == 1


def test_to_filters_degrades_invalid_cleaned_role_to_none() -> None:
    # The ChoiceField normally blocks bad roles, but ``to_filters`` defends
    # against a ``cleaned_data`` that carries a value outside the Role enum
    # (e.g. a future caller that injects cleaned_data directly).
    form = DirectoryFilterForm({})
    form.cleaned_data = {"role": "NOT_A_ROLE"}
    assert form.to_filters().role is None


def test_to_filters_clamps_sub_one_cleaned_page() -> None:
    # IntegerField(min_value=1) blocks page<1 at validation, so ``to_filters``
    # clamps defensively when a cleaned_data smuggles a non-positive page.
    form = DirectoryFilterForm({})
    form.cleaned_data = {"page": -5}
    assert form.to_filters().page == 1
