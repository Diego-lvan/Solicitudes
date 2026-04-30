"""CsvExportImpl tests."""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from reportes.schemas import ReportFilter
from reportes.services.export_service.csv_implementation import CsvExportImpl
from reportes.services.report_service.implementation import DefaultReportService
from reportes.tests.fakes import make_in_memory_lifecycle
from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.schemas import SolicitudDetail
from solicitudes.tipos.schemas import TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO


def _seed_one(repo, *, folio: str, nombre: str, solicitante_nombre: str) -> None:
    tipo_id = uuid4()
    repo.seed(
        SolicitudDetail(
            folio=folio,
            tipo=TipoSolicitudRow(
                id=tipo_id,
                slug="s",
                nombre=nombre,
                responsible_role=Role.CONTROL_ESCOLAR,
                creator_roles={Role.ALUMNO},
                requires_payment=False,
                activo=True,
            ),
            solicitante=UserDTO(
                matricula="ALU-1",
                email="alu-1@uaz.edu.mx",
                role=Role.ALUMNO,
                full_name=solicitante_nombre,
            ),
            estado=Estado.CREADA,
            form_snapshot=FormSnapshot(
                tipo_id=tipo_id,
                tipo_slug="s",
                tipo_nombre=nombre,
                captured_at=datetime.now(tz=UTC),
                fields=[],
            ),
            valores={},
            requiere_pago=True,
            pago_exento=True,
            created_at=datetime(2026, 4, 15, 12, tzinfo=UTC),
            updated_at=datetime(2026, 4, 15, 12, tzinfo=UTC),
            historial=[],
        )
    )


@pytest.fixture
def exporter():
    lifecycle, repo = make_in_memory_lifecycle()
    return CsvExportImpl(report_service=DefaultReportService(lifecycle_service=lifecycle)), repo


def test_csv_starts_with_utf8_bom(exporter) -> None:
    impl, repo = exporter
    _seed_one(repo, folio="SOL-2026-00001", nombre="Constancia", solicitante_nombre="Juan")

    raw = impl.export(filter=ReportFilter())
    assert raw.startswith(b"\xef\xbb\xbf")


def test_csv_preserves_accents_and_columns(exporter) -> None:
    impl, repo = exporter
    _seed_one(
        repo,
        folio="SOL-2026-00002",
        nombre="Constancia académica",
        solicitante_nombre="José Ñoño",
    )

    raw = impl.export(filter=ReportFilter())
    text = raw.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    assert header == [
        "folio",
        "tipo",
        "solicitante_matricula",
        "solicitante_nombre",
        "estado",
        "requiere_pago",
        "pago_exento",
        "created_at",
        "updated_at",
    ]
    body = next(reader)
    assert body[0] == "SOL-2026-00002"
    assert body[1] == "Constancia académica"
    assert body[3] == "José Ñoño"
    assert body[5] == "1"  # requiere_pago
    assert body[6] == "1"  # pago_exento


def test_csv_content_type_and_filename(exporter) -> None:
    impl, _ = exporter
    assert impl.content_type == "text/csv; charset=utf-8"
    assert impl.filename == "solicitudes.csv"
