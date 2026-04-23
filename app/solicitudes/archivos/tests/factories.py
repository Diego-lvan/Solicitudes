"""Test factories for archivos."""
from __future__ import annotations

from hashlib import sha256
from typing import Any
from uuid import uuid4

from model_bakery import baker

from solicitudes.archivos.constants import ArchivoKind
from solicitudes.lifecycle.tests.factories import make_solicitud
from solicitudes.models import ArchivoSolicitud, Solicitud
from usuarios.models import User
from usuarios.tests.factories import make_user


def make_archivo(
    *,
    solicitud: Solicitud | None = None,
    kind: ArchivoKind = ArchivoKind.FORM,
    field_id: Any | None = None,
    original_filename: str = "doc.pdf",
    stored_path: str | None = None,
    content_type: str = "application/pdf",
    size_bytes: int = 1024,
    sha256_hex: str | None = None,
    uploaded_by: User | None = None,
) -> ArchivoSolicitud:
    solicitud = solicitud or make_solicitud()
    if kind is ArchivoKind.FORM and field_id is None:
        field_id = uuid4()
    if kind is ArchivoKind.COMPROBANTE:
        field_id = None
    stored_path = stored_path or f"solicitudes/{solicitud.folio}/{uuid4().hex}.pdf"
    sha256_hex = sha256_hex or sha256(b"x").hexdigest()
    uploaded_by = uploaded_by or make_user(
        matricula=f"U-{uuid4().hex[:8]}",
        email=f"u-{uuid4().hex[:6]}@uaz.edu.mx",
    )
    return baker.make(
        ArchivoSolicitud,
        solicitud=solicitud,
        kind=kind.value,
        field_id=field_id,
        original_filename=original_filename,
        stored_path=stored_path,
        content_type=content_type,
        size_bytes=size_bytes,
        sha256=sha256_hex,
        uploaded_by=uploaded_by,
    )
