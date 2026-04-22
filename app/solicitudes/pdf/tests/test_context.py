"""Tests for the variable-resolution helper."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from solicitudes.formularios.schemas import FieldSnapshot, FormSnapshot
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.schemas import SolicitudDetail
from solicitudes.pdf.context import (
    assemble_html,
    build_render_context,
    slug_for_label,
)
from solicitudes.tipos.constants import FieldType
from solicitudes.tipos.schemas import TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO


def _detail(values: dict[str, object], fields: list[FieldSnapshot]) -> SolicitudDetail:
    tipo = TipoSolicitudRow(
        id=uuid4(),
        slug="t",
        nombre="Constancia",
        responsible_role=Role.CONTROL_ESCOLAR,
        creator_roles={Role.ALUMNO},
        requires_payment=False,
        activo=True,
    )
    user = UserDTO(
        matricula="A1",
        email="a1@uaz.edu.mx",
        role=Role.ALUMNO,
        full_name="Ana A.",
        programa="ISW",
        semestre=4,
    )
    return SolicitudDetail(
        folio="SOL-2026-00001",
        tipo=tipo,
        solicitante=user,
        estado=Estado.FINALIZADA,
        form_snapshot=FormSnapshot(
            tipo_id=tipo.id,
            tipo_slug=tipo.slug,
            tipo_nombre=tipo.nombre,
            captured_at=datetime(2026, 4, 25, tzinfo=UTC),
            fields=fields,
        ),
        valores=values,
        requiere_pago=False,
        pago_exento=False,
        created_at=datetime(2026, 4, 25, tzinfo=UTC),
        updated_at=datetime(2026, 4, 25, tzinfo=UTC),
        historial=[],
    )


def test_slug_for_label_normalizes_to_underscores() -> None:
    assert slug_for_label("Programa Actual") == "programa_actual"
    assert slug_for_label("¿Cuál programa?") == "cual_programa"
    assert slug_for_label("") == "campo"


def test_build_render_context_populates_solicitante_and_solicitud() -> None:
    detail = _detail({}, [])
    user = UserDTO(
        matricula="A1",
        email="a1@uaz.edu.mx",
        role=Role.ALUMNO,
        full_name="Ana A.",
        programa="ISW",
        semestre=4,
    )
    ctx = build_render_context(
        solicitud=detail,
        solicitante=user,
        now=datetime(2026, 4, 25, 12, tzinfo=UTC),
    )
    assert ctx["solicitante"] == {
        "matricula": "A1",
        "nombre": "Ana A.",
        "email": "a1@uaz.edu.mx",
        "programa": "ISW",
        "semestre": 4,
    }
    assert ctx["solicitud"]["folio"] == "SOL-2026-00001"
    assert ctx["solicitud"]["tipo_nombre"] == "Constancia"
    assert ctx["solicitud"]["estado"] == "FINALIZADA"
    assert "Zacatecas" in ctx["firma_lugar_fecha"]
    # April → "abril"
    assert "abril" in ctx["firma_lugar_fecha"]


def test_build_render_context_resolves_valores_by_label_slug() -> None:
    fid = uuid4()
    fields = [
        FieldSnapshot(
            field_id=fid,
            label="Programa Actual",
            field_type=FieldType.TEXT,
            required=True,
            order=0,
        )
    ]
    detail = _detail({str(fid): "ISW"}, fields)
    user = UserDTO(
        matricula="A1", email="a1@uaz.edu.mx", role=Role.ALUMNO, full_name=""
    )
    ctx = build_render_context(
        solicitud=detail, solicitante=user, now=datetime(2026, 4, 25, tzinfo=UTC)
    )
    assert ctx["valores"]["programa_actual"] == "ISW"


def test_file_value_renders_only_filename() -> None:
    fid = uuid4()
    fields = [
        FieldSnapshot(
            field_id=fid,
            label="Comprobante",
            field_type=FieldType.FILE,
            required=False,
            order=0,
        )
    ]
    detail = _detail(
        {str(fid): {"filename": "pago.pdf", "size": 12345}}, fields
    )
    user = UserDTO(matricula="A1", email="a1@uaz.edu.mx", role=Role.ALUMNO)
    ctx = build_render_context(
        solicitud=detail, solicitante=user, now=datetime(2026, 4, 25, tzinfo=UTC)
    )
    assert ctx["valores"]["comprobante"] == "pago.pdf"


def test_assemble_html_wraps_body_with_style() -> None:
    out = assemble_html("<h1>X</h1>", "h1 { color: red }")
    assert "<style>h1 { color: red }</style>" in out
    assert "<h1>X</h1>" in out


def test_assemble_html_omits_empty_style_tag() -> None:
    out = assemble_html("<p/>", "")
    assert "<style>" not in out
