"""BDD scenarios para descarga de archivos adjuntos.

Cubre happy path (dueño descarga su archivo) y alterno (usuario sin
relación recibe 403). Reusa ``make_client``, ``make_archivo`` y la fixture
``MEDIA_ROOT=tmp_path`` definidas en ``conftest.py`` para no romper el disco
real al escribir el archivo.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from pytest_bdd import given, parsers, scenarios, then, when

from solicitudes.archivos.tests.conftest import make_client
from solicitudes.archivos.tests.factories import make_archivo
from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.models import ArchivoSolicitud
from solicitudes.tipos.tests.factories import make_tipo
from usuarios.constants import Role
from usuarios.tests.factories import make_user

pytestmark = pytest.mark.django_db

scenarios("features/archivos.feature")


def _materialize(archivo: ArchivoSolicitud) -> None:
    abs_path = Path(settings.MEDIA_ROOT) / archivo.stored_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(b"contenido-del-archivo")


@pytest.fixture
def ctx() -> dict[str, object]:
    return {}


# --- Given --------------------------------------------------------------


@given(
    parsers.parse(
        'un alumno dueño "{matricula}" con un archivo subido a su solicitud'
    )
)
def _alumno_dueno_archivo(ctx: dict[str, object], matricula: str) -> None:
    user = make_user(
        matricula=matricula,
        email=f"{matricula.lower()}@uaz.edu.mx",
        role=Role.ALUMNO.value,
    )
    tipo = make_tipo(responsible_role=Role.CONTROL_ESCOLAR.value)
    solicitud = make_solicitud(solicitante=user, tipo=tipo)
    archivo = make_archivo(solicitud=solicitud)
    _materialize(archivo)
    ctx["dueno_matricula"] = matricula
    ctx["archivo_id"] = archivo.id


@given("un docente sin relación con esa solicitud")
def _docente_externo(ctx: dict[str, object]) -> None:
    ctx["intruso_matricula"] = "DOC-EXT"
    ctx["intruso_role"] = Role.DOCENTE


# --- When ---------------------------------------------------------------


@when("el alumno solicita descargar su archivo")
def _alumno_descarga(ctx: dict[str, object]) -> None:
    client = make_client(ctx["dueno_matricula"], Role.ALUMNO)  # type: ignore[arg-type]
    url = reverse(
        "solicitudes:archivos:download", kwargs={"archivo_id": ctx["archivo_id"]}
    )
    ctx["resp"] = client.get(url)


@when("el docente intenta descargar el archivo del alumno")
def _docente_intenta(ctx: dict[str, object]) -> None:
    client = make_client(
        ctx["intruso_matricula"], ctx["intruso_role"]  # type: ignore[arg-type]
    )
    url = reverse(
        "solicitudes:archivos:download", kwargs={"archivo_id": ctx["archivo_id"]}
    )
    ctx["resp"] = client.get(url)


# --- Then ---------------------------------------------------------------


@then(parsers.parse("la respuesta tiene código {code:d}"))
def _then_code(ctx: dict[str, object], code: int) -> None:
    assert ctx["resp"].status_code == code  # type: ignore[attr-defined,index]


@then("la respuesta incluye un header Content-Disposition de attachment")
def _then_attachment(ctx: dict[str, object]) -> None:
    resp = ctx["resp"]
    assert resp["Content-Disposition"].startswith("attachment;")  # type: ignore[index]
