"""Pure-Pydantic schema validation tests.

These do not touch the ORM, so they live outside the ``django_db`` test set
and run very fast. They cover the cross-type validators on
:class:`CreateFieldInput` that protect against data shapes the form layer
should have already normalized — defense in depth.
"""
from __future__ import annotations

import pytest

from solicitudes.tipos.constants import FieldSource, FieldType
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


def test_source_default_is_user_input() -> None:
    inp = CreateFieldInput(label="X", field_type=FieldType.TEXT, order=0)
    assert inp.source is FieldSource.USER_INPUT


def test_source_user_text_variants_accepted_on_text() -> None:
    for src in (
        FieldSource.USER_FULL_NAME,
        FieldSource.USER_PROGRAMA,
        FieldSource.USER_EMAIL,
        FieldSource.USER_MATRICULA,
    ):
        inp = CreateFieldInput(
            label="X", field_type=FieldType.TEXT, order=0, source=src
        )
        assert inp.source is src


def test_source_user_semestre_accepted_on_number() -> None:
    inp = CreateFieldInput(
        label="X",
        field_type=FieldType.NUMBER,
        order=0,
        source=FieldSource.USER_SEMESTRE,
    )
    assert inp.source is FieldSource.USER_SEMESTRE


def test_source_user_text_variant_rejected_on_number() -> None:
    with pytest.raises(ValueError, match="USER_PROGRAMA"):
        CreateFieldInput(
            label="X",
            field_type=FieldType.NUMBER,
            order=0,
            source=FieldSource.USER_PROGRAMA,
        )


def test_source_user_semestre_rejected_on_text() -> None:
    with pytest.raises(ValueError, match="USER_SEMESTRE"):
        CreateFieldInput(
            label="X",
            field_type=FieldType.TEXT,
            order=0,
            source=FieldSource.USER_SEMESTRE,
        )


def test_source_rejected_on_select_file_date_textarea() -> None:
    cases = [
        (FieldType.SELECT, {"options": ["a"]}),
        (FieldType.FILE, {"accepted_extensions": [".pdf"]}),
        (FieldType.DATE, {}),
        (FieldType.TEXTAREA, {}),
    ]
    for ft, extra in cases:
        with pytest.raises(ValueError, match="USER_FULL_NAME"):
            CreateFieldInput(
                label="X",
                field_type=ft,
                order=0,
                source=FieldSource.USER_FULL_NAME,
                **extra,
            )
