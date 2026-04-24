"""Tests for tipos forms."""
from __future__ import annotations

from solicitudes.tipos.forms import FieldForm, TipoForm


def _tipo_data(**overrides: object) -> dict[str, object]:
    base = {
        "nombre": "Constancia de Estudios",
        "descripcion": "  un texto  ",
        "responsible_role": "CONTROL_ESCOLAR",
        "creator_roles": ["ALUMNO"],
        "requires_payment": False,
        "mentor_exempt": False,
    }
    base.update(overrides)
    return base


def test_tipo_form_strips_whitespace_in_text_fields() -> None:
    form = TipoForm(data=_tipo_data())
    assert form.is_valid()
    assert form.cleaned_data["descripcion"] == "un texto"


def test_tipo_form_rejects_short_nombre() -> None:
    form = TipoForm(data=_tipo_data(nombre="ab"))
    assert not form.is_valid()
    assert "nombre" in form.errors


def test_tipo_form_rejects_unknown_responsible_role() -> None:
    form = TipoForm(data=_tipo_data(responsible_role="ADMIN"))
    assert not form.is_valid()
    assert "responsible_role" in form.errors


def test_tipo_form_requires_at_least_one_creator_role() -> None:
    form = TipoForm(data=_tipo_data(creator_roles=[]))
    assert not form.is_valid()
    assert "creator_roles" in form.errors


# ---- FieldForm ----


def _field_data(**overrides: object) -> dict[str, object]:
    base = {
        "label": "Nombre",
        "field_type": "TEXT",
        "required": True,
        "order": 0,
        "options_csv": "",
        "accepted_extensions_csv": "",
    }
    base.update(overrides)
    return base


def test_field_form_select_requires_options() -> None:
    form = FieldForm(data=_field_data(field_type="SELECT", options_csv=""))
    assert not form.is_valid()
    assert "options_csv" in form.errors


def test_field_form_select_parses_options_csv() -> None:
    form = FieldForm(
        data=_field_data(field_type="SELECT", options_csv="ISW, ISC ,IST")
    )
    assert form.is_valid()
    assert form.cleaned_data["options"] == ["ISW", "ISC", "IST"]


def test_field_form_text_rejects_options() -> None:
    form = FieldForm(data=_field_data(field_type="TEXT", options_csv="A,B"))
    assert not form.is_valid()
    assert "options_csv" in form.errors


def test_field_form_file_requires_extensions() -> None:
    form = FieldForm(data=_field_data(field_type="FILE", accepted_extensions_csv=""))
    assert not form.is_valid()
    assert "accepted_extensions_csv" in form.errors


def test_field_form_file_extensions_must_start_with_dot() -> None:
    form = FieldForm(
        data=_field_data(field_type="FILE", accepted_extensions_csv="pdf,zip")
    )
    assert not form.is_valid()
    assert "accepted_extensions_csv" in form.errors


def test_field_form_file_normalizes_extensions_lowercase() -> None:
    form = FieldForm(
        data=_field_data(field_type="FILE", accepted_extensions_csv=".PDF, .Zip")
    )
    assert form.is_valid()
    assert form.cleaned_data["accepted_extensions"] == [".pdf", ".zip"]


def test_field_form_text_rejects_extensions() -> None:
    form = FieldForm(
        data=_field_data(field_type="TEXT", accepted_extensions_csv=".pdf")
    )
    assert not form.is_valid()
    assert "accepted_extensions_csv" in form.errors


def test_field_form_text_keeps_max_chars() -> None:
    form = FieldForm(data=_field_data(field_type="TEXT", max_chars=120))
    assert form.is_valid()
    assert form.cleaned_data["max_chars"] == 120


def test_field_form_textarea_keeps_max_chars() -> None:
    form = FieldForm(data=_field_data(field_type="TEXTAREA", max_chars=500))
    assert form.is_valid()
    assert form.cleaned_data["max_chars"] == 500


def test_field_form_clears_max_chars_for_non_text_types() -> None:
    # Stale max_chars (e.g., admin started TEXT then switched to NUMBER without
    # the JS hiding/clearing the value) must be normalized to None.
    form = FieldForm(data=_field_data(field_type="NUMBER", max_chars=50))
    assert form.is_valid()
    assert form.cleaned_data["max_chars"] is None


def test_field_form_clears_max_size_for_non_file_types() -> None:
    form = FieldForm(data=_field_data(field_type="TEXT", max_size_mb=20))
    assert form.is_valid()
    assert form.cleaned_data["max_size_mb"] == 10  # default


def test_field_form_file_keeps_max_size() -> None:
    form = FieldForm(
        data=_field_data(
            field_type="FILE",
            accepted_extensions_csv=".pdf",
            max_size_mb=20,
        )
    )
    assert form.is_valid()
    assert form.cleaned_data["max_size_mb"] == 20


# ---- source ----


def test_field_form_source_defaults_to_user_input() -> None:
    form = FieldForm(data=_field_data())
    assert form.is_valid()
    assert form.cleaned_data["source"] == "USER_INPUT"


def test_field_form_source_user_programa_round_trips_on_text() -> None:
    form = FieldForm(data=_field_data(field_type="TEXT", source="USER_PROGRAMA"))
    assert form.is_valid()
    assert form.cleaned_data["source"] == "USER_PROGRAMA"


def test_field_form_source_user_semestre_round_trips_on_number() -> None:
    form = FieldForm(data=_field_data(field_type="NUMBER", source="USER_SEMESTRE"))
    assert form.is_valid()
    assert form.cleaned_data["source"] == "USER_SEMESTRE"


def test_field_form_source_normalized_to_user_input_on_select() -> None:
    # Stale USER_PROGRAMA after admin switched type to SELECT must be reset
    # silently — defense in depth on top of the schema validator.
    form = FieldForm(
        data=_field_data(
            field_type="SELECT",
            options_csv="A,B",
            source="USER_PROGRAMA",
        )
    )
    assert form.is_valid()
    assert form.cleaned_data["source"] == "USER_INPUT"


def test_field_form_source_normalized_to_user_input_on_textarea() -> None:
    form = FieldForm(
        data=_field_data(field_type="TEXTAREA", source="USER_PROGRAMA")
    )
    assert form.is_valid()
    assert form.cleaned_data["source"] == "USER_INPUT"


def test_field_form_source_normalized_when_text_meets_user_semestre() -> None:
    # USER_SEMESTRE is NUMBER-only; a TEXT row must reset rather than reject.
    form = FieldForm(data=_field_data(field_type="TEXT", source="USER_SEMESTRE"))
    assert form.is_valid()
    assert form.cleaned_data["source"] == "USER_INPUT"
