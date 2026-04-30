"""Direct unit tests for ``parse_report_filter``.

The parser deliberately swallows malformed input so a stale bookmark or a
hand-edited URL never blocks an admin with a 400. These tests pin that
behavior so future "fail loudly on bad input" refactors are deliberate.
"""
from __future__ import annotations

from datetime import date
from uuid import uuid4

from django.http import QueryDict

from reportes.forms.report_filter_form import parse_report_filter
from reportes.schemas import ReportFilter
from solicitudes.lifecycle.constants import Estado
from usuarios.constants import Role


def _qd(**params: str) -> QueryDict:
    qd = QueryDict(mutable=True)
    for k, v in params.items():
        qd[k] = v
    return qd


def test_empty_querydict_returns_default_filter() -> None:
    f = parse_report_filter(_qd())
    assert f == ReportFilter()


def test_valid_estado_role_dates_parse() -> None:
    tipo_id = uuid4()
    f = parse_report_filter(
        _qd(
            estado="CREADA",
            tipo_id=str(tipo_id),
            responsible_role="CONTROL_ESCOLAR",
            created_from="2026-01-01",
            created_to="2026-12-31",
        )
    )
    assert f.estado is Estado.CREADA
    assert f.tipo_id == tipo_id
    assert f.responsible_role is Role.CONTROL_ESCOLAR
    assert f.created_from == date(2026, 1, 1)
    assert f.created_to == date(2026, 12, 31)


def test_invalid_estado_silently_dropped() -> None:
    f = parse_report_filter(_qd(estado="NO_ES_UN_ESTADO"))
    assert f.estado is None


def test_invalid_role_silently_dropped() -> None:
    f = parse_report_filter(_qd(responsible_role="not_a_role"))
    assert f.responsible_role is None


def test_invalid_uuid_silently_dropped() -> None:
    f = parse_report_filter(_qd(tipo_id="not-a-uuid"))
    assert f.tipo_id is None


def test_invalid_date_silently_dropped() -> None:
    f = parse_report_filter(
        _qd(created_from="2026-99-99", created_to="not-a-date")
    )
    assert f.created_from is None
    assert f.created_to is None


def test_inverted_date_range_silently_dropped() -> None:
    """Stale bookmark protection: ``from > to`` is dropped, not 400."""
    f = parse_report_filter(
        _qd(created_from="2026-12-31", created_to="2026-01-01")
    )
    assert f.created_from is None
    assert f.created_to is None


def test_partial_date_range_only_one_bound_is_kept() -> None:
    f = parse_report_filter(_qd(created_from="2026-06-01"))
    assert f.created_from == date(2026, 6, 1)
    assert f.created_to is None
