"""Tests for the PdfService — authorisation matrix + deterministic re-render.

These exercise the WeasyPrint path (real bytes start with %PDF). They run
against the in-process Django test DB.
"""
from __future__ import annotations

from typing import Any

import pytest
from freezegun import freeze_time

from _shared.exceptions import Unauthorized
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.models import TipoSolicitud
from solicitudes.pdf.dependencies import (
    get_pdf_service,
)
from solicitudes.pdf.exceptions import TipoHasNoPlantilla
from solicitudes.pdf.tests.factories import make_plantilla
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import Role
from usuarios.schemas import UserDTO
from usuarios.tests.factories import make_user


def _user_dto(orm_user: Any, role: Role) -> UserDTO:
    return UserDTO(
        matricula=orm_user.matricula,
        email=orm_user.email,
        role=role,
        full_name=orm_user.full_name or "",
        programa=orm_user.programa or "",
        semestre=orm_user.semestre,
    )


def _attach_plantilla(tipo: TipoSolicitud, **plantilla_kwargs: Any) -> TipoSolicitud:
    plantilla = make_plantilla(**plantilla_kwargs)
    tipo.plantilla = plantilla
    tipo.save()
    return tipo


# ---------- happy path ----------


@pytest.mark.django_db
def test_render_returns_pdf_bytes_for_personal() -> None:
    """Replaces the pre-016 owner-FINALIZADA happy path.

    From initiative 016 onwards the PDF is a draft for personal/admin only;
    the solicitante never downloads it (they receive the handler's uploaded
    response files via ``solicitudes.respuesta`` instead).
    """
    tipo = make_tipo(
        nombre="Constancia de Estudios",
        responsible_role=Role.CONTROL_ESCOLAR.value,
    )
    _attach_plantilla(tipo)
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    personal = make_user(
        matricula="P-PDF", email="p-pdf@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    requester = _user_dto(personal, Role.CONTROL_ESCOLAR)

    result = get_pdf_service().render_for_solicitud(sol.folio, requester)

    assert result.bytes_.startswith(b"%PDF")
    assert len(result.bytes_) > 1000
    assert result.suggested_filename.endswith(".pdf")
    assert sol.folio in result.suggested_filename


@pytest.mark.django_db
def test_owner_can_no_longer_render_pdf_after_initiative_016() -> None:
    """The solicitante (owner) loses access to the auto-rendered PDF in any
    estado. Pins the post-016 authorisation matrix."""
    tipo = make_tipo()
    _attach_plantilla(tipo)
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    requester = _user_dto(sol.solicitante, Role.ALUMNO)
    with pytest.raises(Unauthorized):
        get_pdf_service().render_for_solicitud(sol.folio, requester)


@pytest.mark.django_db
def test_personal_can_render_at_any_estado() -> None:
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    _attach_plantilla(tipo)
    sol = make_solicitud(tipo=tipo, estado=Estado.CREADA)
    personal = make_user(matricula="P1", email="p1@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value)
    result = get_pdf_service().render_for_solicitud(
        sol.folio, _user_dto(personal, Role.CONTROL_ESCOLAR)
    )
    assert result.bytes_.startswith(b"%PDF")


@pytest.mark.django_db
def test_admin_can_render_at_any_estado() -> None:
    tipo = make_tipo()
    _attach_plantilla(tipo)
    sol = make_solicitud(tipo=tipo, estado=Estado.EN_PROCESO)
    admin = make_user(matricula="ADM1", email="adm@uaz.edu.mx", role=Role.ADMIN.value)
    result = get_pdf_service().render_for_solicitud(
        sol.folio, _user_dto(admin, Role.ADMIN)
    )
    assert result.bytes_.startswith(b"%PDF")


# ---------- authorisation ----------


@pytest.mark.django_db
def test_owner_pre_finalizada_cannot_render() -> None:
    tipo = make_tipo()
    _attach_plantilla(tipo)
    sol = make_solicitud(tipo=tipo, estado=Estado.CREADA)
    requester = _user_dto(sol.solicitante, Role.ALUMNO)
    with pytest.raises(Unauthorized):
        get_pdf_service().render_for_solicitud(sol.folio, requester)


@pytest.mark.django_db
def test_docente_non_owner_cannot_render_finalizada() -> None:
    """A DOCENTE who is not the solicitante must not be able to render
    another student's PDF, even when the solicitud is FINALIZADA. Pins the
    authz matrix so a future refactor that broadens the personal set is
    forced to update this test."""
    tipo = make_tipo()
    _attach_plantilla(tipo)
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    docente = make_user(matricula="D1", email="d1@uaz.edu.mx", role=Role.DOCENTE.value)
    with pytest.raises(Unauthorized):
        get_pdf_service().render_for_solicitud(
            sol.folio, _user_dto(docente, Role.DOCENTE)
        )


@pytest.mark.django_db
def test_other_alumno_cannot_render() -> None:
    tipo = make_tipo()
    _attach_plantilla(tipo)
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    other = make_user(matricula="A99", email="a99@uaz.edu.mx", role=Role.ALUMNO.value)
    with pytest.raises(Unauthorized):
        get_pdf_service().render_for_solicitud(
            sol.folio, _user_dto(other, Role.ALUMNO)
        )


# ---------- no plantilla ----------


@pytest.mark.django_db
def test_no_plantilla_raises_tipo_has_no_plantilla() -> None:
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    personal = make_user(
        matricula="P-NOPL", email="p-nopl@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    requester = _user_dto(personal, Role.CONTROL_ESCOLAR)
    with pytest.raises(TipoHasNoPlantilla):
        get_pdf_service().render_for_solicitud(sol.folio, requester)


# ---------- determinism ----------


@pytest.mark.django_db
def test_two_renders_under_frozen_clock_are_byte_identical() -> None:
    tipo = make_tipo(
        nombre="Constancia", responsible_role=Role.CONTROL_ESCOLAR.value
    )
    _attach_plantilla(tipo)
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    personal = make_user(
        matricula="P-DET", email="p-det@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    requester = _user_dto(personal, Role.CONTROL_ESCOLAR)

    with freeze_time("2026-04-25T12:00:00+00:00"):
        first = get_pdf_service().render_for_solicitud(sol.folio, requester)
        second = get_pdf_service().render_for_solicitud(sol.folio, requester)

    assert first.bytes_ == second.bytes_


# ---------- assets ----------


@pytest.mark.django_db
def test_render_injects_assets_into_context() -> None:
    """A global asset's slug becomes a `data:image/png;base64,...` URI in the
    rendered HTML. The rendered PDF includes the embedded image bytes."""
    from solicitudes.plantilla_assets.tests.factories import make_global_asset

    make_global_asset(nombre="Logo UAZ", slug="logo_uaz")

    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    _attach_plantilla(
        tipo,
        html='<p><img src="{{ assets.logo_uaz }}" alt="logo"></p>',
    )
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    personal = make_user(
        matricula="P-AS", email="p-as@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    requester = _user_dto(personal, Role.CONTROL_ESCOLAR)

    result = get_pdf_service().render_for_solicitud(sol.folio, requester)
    assert result.bytes_.startswith(b"%PDF")
    # The base64-encoded PNG signature appears in the PDF (deflate/raw text).
    # We can't easily inspect the embedded image without parsing the PDF, but
    # We verify slug resolution end-to-end by re-running the service's asset
    # lookup against the same plantilla and asserting the slug is reachable.
    from solicitudes.plantilla_assets.dependencies import get_asset_service

    detail = get_pdf_service()._lifecycle.get_detail(sol.folio)  # type: ignore[attr-defined]
    plantilla_id = detail.tipo.plantilla_id
    slugs = {dto.slug for dto in get_asset_service().list_for_render(plantilla_id)}
    assert "logo_uaz" in slugs


@pytest.mark.django_db
def test_render_with_missing_asset_slug_in_template_does_not_crash() -> None:
    """A plantilla referencing `assets.nonexistent` renders with an empty src
    rather than crashing (Django template rendering treats missing keys as ''
    via setting TEMPLATE_STRING_IF_INVALID = '' by default)."""
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    _attach_plantilla(
        tipo, html='<p><img src="{{ assets.missing_slug }}"></p>'
    )
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    personal = make_user(
        matricula="P-MS", email="p-ms@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    requester = _user_dto(personal, Role.CONTROL_ESCOLAR)

    result = get_pdf_service().render_for_solicitud(sol.folio, requester)
    assert result.bytes_.startswith(b"%PDF")


@pytest.mark.django_db
def testasset_to_data_uri_returns_empty_when_file_missing() -> None:
    from datetime import UTC
    from datetime import datetime as _dt
    from uuid import uuid4

    from solicitudes.pdf.services.pdf_service.implementation import (
        asset_to_data_uri,
    )
    from solicitudes.plantilla_assets.schemas import (
        AssetScope,
        PlantillaAssetDTO,
    )

    dto = PlantillaAssetDTO(
        id=uuid4(),
        slug="missing",
        nombre="Missing",
        scope=AssetScope.GLOBAL,
        plantilla_id=None,
        file_path="plantilla_assets/9999/99/does-not-exist.png",
        mime_type="image/png",
        size_bytes=10,
        created_at=_dt.now(UTC),
        created_by_id="ADM1",
    )
    assert asset_to_data_uri(dto) == ""


@pytest.mark.django_db
def test_two_renders_with_same_asset_under_frozen_clock_are_byte_identical() -> None:
    from solicitudes.plantilla_assets.tests.factories import make_global_asset

    make_global_asset(nombre="Logo Det", slug="logo_det")
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    _attach_plantilla(
        tipo,
        html='<p>X <img src="{{ assets.logo_det }}"> Y</p>',
    )
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    personal = make_user(
        matricula="P-DAS", email="p-das@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    requester = _user_dto(personal, Role.CONTROL_ESCOLAR)

    with freeze_time("2026-04-25T12:00:00+00:00"):
        first = get_pdf_service().render_for_solicitud(sol.folio, requester)
        second = get_pdf_service().render_for_solicitud(sol.folio, requester)
    assert first.bytes_ == second.bytes_


# ---------- template syntax errors at render time ----------


@pytest.mark.django_db
def test_render_for_solicitud_raises_on_bad_template_syntax() -> None:
    from solicitudes.pdf.exceptions import PlantillaTemplateError

    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    # The factory persists html verbatim without the service's parse check,
    # simulating a plantilla saved before a regression or via raw ORM.
    _attach_plantilla(tipo, html="<p>{% if x %}</p>")
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    personal = make_user(
        matricula="P-BAD", email="p-bad@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    requester = _user_dto(personal, Role.CONTROL_ESCOLAR)
    with pytest.raises(PlantillaTemplateError):
        get_pdf_service().render_for_solicitud(sol.folio, requester)


@pytest.mark.django_db
def test_render_sample_returns_pdf_bytes() -> None:
    plantilla = make_plantilla(nombre="Sample")
    result = get_pdf_service().render_sample(plantilla.id)
    assert result.bytes_.startswith(b"%PDF")
    assert result.folio == "PREVIEW"
    assert result.suggested_filename.endswith(".pdf")


@pytest.mark.django_db
def test_render_sample_raises_on_bad_template_syntax() -> None:
    from solicitudes.pdf.exceptions import PlantillaTemplateError

    plantilla = make_plantilla(html="<p>{% for x %}</p>")
    with pytest.raises(PlantillaTemplateError):
        get_pdf_service().render_sample(plantilla.id)


@pytest.mark.django_db
def test_resolve_assets_swallows_app_error_and_returns_empty() -> None:
    from _shared.exceptions import Conflict
    from solicitudes.pdf.dependencies import (
        get_plantilla_repository,
    )
    from solicitudes.pdf.services.pdf_service.implementation import (
        DefaultPdfService,
    )

    class _FailingAssets:
        def list_for_render(self, _pid: Any) -> Any:
            raise Conflict("asset table borked")

    service = DefaultPdfService(
        lifecycle_service=get_pdf_service()._lifecycle,  # type: ignore[attr-defined]
        plantilla_repository=get_plantilla_repository(),
        user_service=get_pdf_service()._users,  # type: ignore[attr-defined]
        asset_service=_FailingAssets(),  # type: ignore[arg-type]
    )
    # The plantilla references an asset slug; the failing service degrades to
    # an empty map and the PDF still renders.
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    _attach_plantilla(tipo, html='<p><img src="{{ assets.x }}"></p>')
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    personal = make_user(
        matricula="P-AE", email="p-ae@uaz.edu.mx", role=Role.CONTROL_ESCOLAR.value
    )
    requester = _user_dto(personal, Role.CONTROL_ESCOLAR)
    result = service.render_for_solicitud(sol.folio, requester)
    assert result.bytes_.startswith(b"%PDF")
