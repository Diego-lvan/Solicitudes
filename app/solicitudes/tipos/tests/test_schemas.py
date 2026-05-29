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


# ---- options / extensions cross-type rules ----


def test_options_rejected_on_non_select_field() -> None:
    with pytest.raises(ValueError, match="only SELECT fields may use options"):
        CreateFieldInput(
            label="X",
            field_type=FieldType.TEXT,
            order=0,
            options=["a", "b"],
        )


def test_file_field_requires_accepted_extensions() -> None:
    with pytest.raises(ValueError, match="FILE fields must declare"):
        CreateFieldInput(
            label="X",
            field_type=FieldType.FILE,
            order=0,
            accepted_extensions=[],
        )


def test_accepted_extensions_rejected_on_non_file_field() -> None:
    with pytest.raises(ValueError, match="only FILE fields may declare"):
        CreateFieldInput(
            label="X",
            field_type=FieldType.TEXT,
            order=0,
            accepted_extensions=[".pdf"],
        )


# ---- CreateTipoInput validators ----


def _base_tipo_kwargs() -> dict:
    from usuarios.constants import Role

    return {
        "nombre": "Constancia",
        "responsible_role": Role.CONTROL_ESCOLAR,
        "creator_roles": {Role.ALUMNO},
    }


def test_creator_roles_must_be_alumno_or_docente() -> None:
    from solicitudes.tipos.schemas import CreateTipoInput
    from usuarios.constants import Role

    kwargs = _base_tipo_kwargs()
    kwargs["creator_roles"] = {Role.ADMIN}
    with pytest.raises(ValueError, match="creator_roles only supports"):
        CreateTipoInput(**kwargs)


def test_responsible_role_must_be_in_allowed_set() -> None:
    from solicitudes.tipos.schemas import CreateTipoInput
    from usuarios.constants import Role

    kwargs = _base_tipo_kwargs()
    kwargs["responsible_role"] = Role.ALUMNO
    with pytest.raises(ValueError, match="responsible_role must be"):
        CreateTipoInput(**kwargs)


def test_mentor_exempt_auto_cleared_without_payment() -> None:
    from solicitudes.tipos.schemas import CreateTipoInput

    kwargs = _base_tipo_kwargs()
    kwargs["requires_payment"] = False
    kwargs["mentor_exempt"] = True
    dto = CreateTipoInput(**kwargs)
    assert dto.mentor_exempt is False


def test_field_count_capped() -> None:
    from solicitudes.tipos.constants import MAX_FIELDS_PER_TIPO
    from solicitudes.tipos.schemas import CreateTipoInput

    kwargs = _base_tipo_kwargs()
    kwargs["fields"] = [
        CreateFieldInput(label=f"F{i}", field_type=FieldType.TEXT, order=i)
        for i in range(MAX_FIELDS_PER_TIPO + 1)
    ]
    with pytest.raises(ValueError, match="cannot have more than"):
        CreateTipoInput(**kwargs)


def test_field_orders_must_be_unique() -> None:
    from solicitudes.tipos.schemas import CreateTipoInput

    kwargs = _base_tipo_kwargs()
    kwargs["fields"] = [
        CreateFieldInput(label="A", field_type=FieldType.TEXT, order=0),
        CreateFieldInput(label="B", field_type=FieldType.TEXT, order=0),
    ]
    with pytest.raises(ValueError, match="`order` values must be unique"):
        CreateTipoInput(**kwargs)
