"""DefaultReportService tests using in-memory lifecycle fakes."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from _shared.pagination import PageRequest
from reportes.schemas import ReportFilter
from reportes.services.report_service.implementation import (
    DefaultReportService,
    _default_month_window,
)
from reportes.tests.fakes import make_in_memory_lifecycle
from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.schemas import SolicitudDetail
from solicitudes.tipos.schemas import TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO


def _seed(repo, *, count: int, tipo_id, tipo_nombre, estado: Estado) -> None:
    for i in range(count):
        repo.seed(
            SolicitudDetail(
                folio=f"SOL-2026-{uuid4().int % 100_000:05d}",
                tipo=TipoSolicitudRow(
                    id=tipo_id,
                    slug=f"slug-{tipo_id}",
                    nombre=tipo_nombre,
                    responsible_role=Role.CONTROL_ESCOLAR,
                    creator_roles={Role.ALUMNO},
                    requires_payment=False,
                    activo=True,
                ),
                solicitante=UserDTO(
                    matricula=f"ALU-{i}",
                    email=f"alu-{i}@uaz.edu.mx",
                    role=Role.ALUMNO,
                ),
                estado=estado,
                form_snapshot=FormSnapshot(
                    tipo_id=tipo_id,
                    tipo_slug="slug",
                    tipo_nombre=tipo_nombre,
                    captured_at=datetime.now(tz=UTC),
                    fields=[],
                ),
                valores={},
                requiere_pago=False,
                pago_exento=False,
                created_at=datetime(2026, 4, 15, 12, tzinfo=UTC),
                updated_at=datetime(2026, 4, 15, 12, tzinfo=UTC),
                historial=[],
            )
        )


@pytest.fixture
def report_service():
    lifecycle, repo = make_in_memory_lifecycle()
    return DefaultReportService(lifecycle_service=lifecycle), repo


def test_dashboard_total_equals_sum_of_estado_counts(report_service) -> None:
    service, repo = report_service
    tipo_id = uuid4()
    _seed(repo, count=3, tipo_id=tipo_id, tipo_nombre="A", estado=Estado.CREADA)
    _seed(repo, count=2, tipo_id=tipo_id, tipo_nombre="A", estado=Estado.FINALIZADA)

    data = service.dashboard(filter=ReportFilter())
    assert data.total == 5
    counts_by_estado = {r.estado: r.count for r in data.by_estado}
    assert counts_by_estado == {Estado.CREADA: 3, Estado.FINALIZADA: 2}


def test_dashboard_by_tipo_groups_by_tipo_id_name(report_service) -> None:
    service, repo = report_service
    tipo_a = uuid4()
    tipo_b = uuid4()
    _seed(repo, count=2, tipo_id=tipo_a, tipo_nombre="Constancia", estado=Estado.CREADA)
    _seed(repo, count=1, tipo_id=tipo_b, tipo_nombre="Beca", estado=Estado.CREADA)

    data = service.dashboard(filter=ReportFilter())
    by_id = {r.tipo_id: (r.tipo_nombre, r.count) for r in data.by_tipo}
    assert by_id[tipo_a] == ("Constancia", 2)
    assert by_id[tipo_b] == ("Beca", 1)


def test_default_month_window_spans_12_months_inclusive() -> None:
    from datetime import date

    start, end = _default_month_window(date(2026, 4, 25))
    assert end == date(2026, 4, 25)
    assert start == date(2025, 5, 1)


def test_default_month_window_handles_year_rollover() -> None:
    from datetime import date

    start, _end = _default_month_window(date(2026, 2, 10))
    assert start == date(2025, 3, 1)


def test_list_paginated_returns_admin_scoped_rows(report_service) -> None:
    service, repo = report_service
    tipo_id = uuid4()
    _seed(repo, count=4, tipo_id=tipo_id, tipo_nombre="X", estado=Estado.CREADA)

    page = service.list_paginated(
        filter=ReportFilter(), page=PageRequest(page=1, page_size=10)
    )
    assert page.total == 4
    assert len(page.items) == 4
