"""Pure-Pydantic schema validation tests.

These do not touch the ORM, so they live outside the ``django_db`` test set
and run very fast. They cover the cross-type validators on
:class:`CreateFieldInput` that protect against data shapes the form layer
should have already normalized — defense in depth.
"""
from __future__ import annotations

import pytest

from solicitudes.tipos.constants import FieldType
from solicitudes.tipos.schemas import CreateFieldInput


def test_max_chars_rejected_on_non_text_types() -> None:
    for ft in (FieldType.NUMBER, FieldType.DATE, FieldType.SELECT, FieldType.FILE):
        with pytest.raises(ValueError, match="max_chars"):
            CreateFieldInput(
                label="X",
                field_type=ft,
                order=0,
                max_chars=10,
                # Provide the per-type required values so the validator that
                # *would* trip first (e.g. SELECT options) doesn't pre-empt.
                options=["a"] if ft is FieldType.SELECT else [],
                accepted_extensions=[".pdf"] if ft is FieldType.FILE else [],
            )


def test_max_chars_accepted_on_text_and_textarea() -> None:
    for ft in (FieldType.TEXT, FieldType.TEXTAREA):
        inp = CreateFieldInput(
            label="X",
            field_type=ft,
            order=0,
            max_chars=120,
        )
        assert inp.max_chars == 120


def test_max_chars_none_is_always_valid() -> None:
    for ft in FieldType:
        inp = CreateFieldInput(
            label="X",
            field_type=ft,
            order=0,
            max_chars=None,
            options=["a"] if ft is FieldType.SELECT else [],
            accepted_extensions=[".pdf"] if ft is FieldType.FILE else [],
        )
        assert inp.max_chars is None


def test_options_check_runs_before_max_chars_check() -> None:
    # Reviewer Important #3: shape-of-value errors should surface first so
    # the admin only sees the actionable fix, not the noisy stale-flag error.
    with pytest.raises(ValueError, match="SELECT fields must define"):
        CreateFieldInput(
            label="X",
            field_type=FieldType.SELECT,
            order=0,
            options=[],
            max_chars=120,  # would also trip _check_max_chars_scope
        )
