"""Test factories for the respuesta feature."""
from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

from model_bakery import baker

from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.models import ArchivoRespuesta, RespuestaSolicitud, Solicitud
from usuarios.constants import Role
from usuarios.models import User
from usuarios.tests.factories import make_user


def make_respuesta(
    *,
    solicitud: Solicitud | None = None,
    actor: User | None = None,
    actor_role: Role = Role.CONTROL_ESCOLAR,
    comentario: str = "",
) -> RespuestaSolicitud:
    solicitud = solicitud or make_solicitud()
    if actor is None:
        suffix = uuid4().hex[:8]
        actor = make_user(
            matricula=f"P-{suffix}",
            email=f"p-{suffix}@uaz.edu.mx",
            role=actor_role.value,
        )
    return baker.make(
        RespuestaSolicitud,
        solicitud=solicitud,
        actor=actor,
        actor_role=actor_role.value,
        comentario=comentario,
    )


def make_archivo_respuesta(
    *,
    respuesta: RespuestaSolicitud | None = None,
    nombre_original: str = "respuesta.pdf",
    content_type: str = "application/pdf",
    size_bytes: int = 256,
    stored_path: str | None = None,
    sha256_hex: str | None = None,
) -> ArchivoRespuesta:
    respuesta = respuesta or make_respuesta()
    folio = respuesta.solicitud_id
    stored_path = stored_path or f"solicitudes/{folio}/{uuid4().hex}.pdf"
    sha256_hex = sha256_hex or sha256(b"x").hexdigest()
    return baker.make(
        ArchivoRespuesta,
        respuesta=respuesta,
        nombre_original=nombre_original,
        stored_path=stored_path,
        content_type=content_type,
        size_bytes=size_bytes,
        sha256=sha256_hex,
    )
