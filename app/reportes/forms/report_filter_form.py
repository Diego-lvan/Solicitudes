"""GET-style filter form for the reportes views.

Translates the request's ``GET`` querystring into a clean
:class:`reportes.schemas.ReportFilter`. Invalid params are silently ignored
(empty filter wins) so a malformed querystring never blocks an admin.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from django.http import QueryDict

from reportes.schemas import ReportFilter
from solicitudes.lifecycle.constants import Estado
from usuarios.constants import Role


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _parse_uuid(raw: str | None) -> UUID | None:
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None


def _parse_estado(raw: str | None) -> Estado | None:
    if not raw:
        return None
    try:
        return Estado(raw)
    except ValueError:
        return None


def _parse_role(raw: str | None) -> Role | None:
    if not raw:
        return None
    try:
        return Role(raw)
    except ValueError:
        return None


def parse_report_filter(query: QueryDict) -> ReportFilter:
    """Build a ReportFilter from a request's GET dict."""
    created_from = _parse_date(query.get("created_from"))
    created_to = _parse_date(query.get("created_to"))
    # Pydantic validator rejects from > to; swallow that here so a stale
    # bookmark renders an empty result instead of a 400.
    if (
        created_from is not None
        and created_to is not None
        and created_from > created_to
    ):
        created_from = None
        created_to = None

    return ReportFilter(
        estado=_parse_estado(query.get("estado")),
        tipo_id=_parse_uuid(query.get("tipo_id")),
        responsible_role=_parse_role(query.get("responsible_role")),
        created_from=created_from,
        created_to=created_to,
    )
