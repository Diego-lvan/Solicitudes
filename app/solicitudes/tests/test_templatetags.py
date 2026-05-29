"""Unit tests for solicitudes + shared template filters."""
from __future__ import annotations

from uuid import uuid4

from _shared.templatetags.role_display import role_label
from solicitudes.templatetags.solicitudes_tags import get_valor
from usuarios.constants import Role

# ---- solicitudes_tags.get_valor ----


def test_get_valor_returns_empty_for_missing_or_none() -> None:
    assert get_valor(None, uuid4()) == ""
    assert get_valor({}, uuid4()) == ""


def test_get_valor_looks_up_by_stringified_id() -> None:
    fid = uuid4()
    valores = {str(fid): "respuesta"}
    assert get_valor(valores, fid) == "respuesta"
    # Absent key falls back to "".
    assert get_valor(valores, uuid4()) == ""


# ---- role_display.role_label ----


def test_role_label_none_is_empty() -> None:
    assert role_label(None) == ""


def test_role_label_titlecases_enum_and_string() -> None:
    assert role_label(Role.CONTROL_ESCOLAR) == "Control Escolar"
    assert role_label("RESPONSABLE_PROGRAMA") == "Responsable Programa"
