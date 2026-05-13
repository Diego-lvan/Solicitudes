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
def test_render_returns_pdf_bytes_for_finalized_solicitud_owner() -> None:
    tipo = make_tipo(nombre="Constancia de Estudios")
    _attach_plantilla(tipo)
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    requester = _user_dto(sol.solicitante, Role.ALUMNO)

    result = get_pdf_service().render_for_solicitud(sol.folio, requester)

    assert result.bytes_.startswith(b"%PDF")
    assert len(result.bytes_) > 1000
    assert result.suggested_filename.endswith(".pdf")
    assert sol.folio in result.suggested_filename


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
    tipo = make_tipo()
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    requester = _user_dto(sol.solicitante, Role.ALUMNO)
    with pytest.raises(TipoHasNoPlantilla):
        get_pdf_service().render_for_solicitud(sol.folio, requester)


# ---------- determinism ----------


@pytest.mark.django_db
def test_two_renders_under_frozen_clock_are_byte_identical() -> None:
    tipo = make_tipo(nombre="Constancia")
    _attach_plantilla(tipo)
    sol = make_solicitud(tipo=tipo, estado=Estado.FINALIZADA)
    requester = _user_dto(sol.solicitante, Role.ALUMNO)

    with freeze_time("2026-04-25T12:00:00+00:00"):
        first = get_pdf_service().render_for_solicitud(sol.folio, requester)
        second = get_pdf_service().render_for_solicitud(sol.folio, requester)

    assert first.bytes_ == second.bytes_
