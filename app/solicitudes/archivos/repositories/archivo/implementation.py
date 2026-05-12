"""ORM-backed implementation of :class:`ArchivoRepository`.

Owns reads and writes of ``ArchivoSolicitud`` only. Per the cross-feature
dependency rule, this module never queries ``Solicitud`` or ``TipoSolicitud``
directly — the service composes solicitud context via ``LifecycleService``.
"""
from __future__ import annotations

from uuid import UUID

from solicitudes.archivos.constants import ArchivoKind
from solicitudes.archivos.exceptions import ArchivoNotFound
from solicitudes.archivos.repositories.archivo.interface import ArchivoRepository
from solicitudes.archivos.schemas import ArchivoDTO, ArchivoRecord
from solicitudes.models import ArchivoSolicitud


def _to_dto(row: ArchivoSolicitud) -> ArchivoDTO:
    return ArchivoDTO(
        id=row.id,
        solicitud_folio=row.solicitud_id,
        field_id=row.field_id,
        kind=ArchivoKind(row.kind),
        original_filename=row.original_filename,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        uploaded_at=row.uploaded_at,
    )


def _to_record(row: ArchivoSolicitud) -> ArchivoRecord:
    return ArchivoRecord(
        id=row.id,
        solicitud_folio=row.solicitud_id,
        field_id=row.field_id,
        kind=ArchivoKind(row.kind),
        original_filename=row.original_filename,
        stored_path=row.stored_path,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        uploaded_at=row.uploaded_at,
    )


class OrmArchivoRepository(ArchivoRepository):
    def create(
        self,
        *,
        solicitud_folio: str,
        field_id: UUID | None,
        kind: ArchivoKind,
        original_filename: str,
        stored_path: str,
        content_type: str,
        size_bytes: int,
        sha256: str,
        uploaded_by_matricula: str,
    ) -> ArchivoDTO:
        row = ArchivoSolicitud.objects.create(
            solicitud_id=solicitud_folio,
            field_id=field_id,
            kind=kind.value,
            original_filename=original_filename,
            stored_path=stored_path,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256=sha256,
            uploaded_by_id=uploaded_by_matricula,
        )
        return _to_dto(row)

    def get_record(self, archivo_id: UUID) -> ArchivoRecord:
        try:
            row = ArchivoSolicitud.objects.get(id=archivo_id)
        except ArchivoSolicitud.DoesNotExist as exc:
            raise ArchivoNotFound() from exc
        return _to_record(row)

    def list_by_folio(self, folio: str) -> list[ArchivoDTO]:
        rows = ArchivoSolicitud.objects.filter(solicitud_id=folio).order_by(
            "uploaded_at"
        )
        return [_to_dto(r) for r in rows]

    def find_form_archivo(
        self, *, folio: str, field_id: UUID
    ) -> ArchivoRecord | None:
        try:
            row = ArchivoSolicitud.objects.get(
                solicitud_id=folio,
                field_id=field_id,
                kind=ArchivoKind.FORM.value,
            )
        except ArchivoSolicitud.DoesNotExist:
            return None
        return _to_record(row)

    def find_comprobante(self, *, folio: str) -> ArchivoRecord | None:
        try:
            row = ArchivoSolicitud.objects.get(
                solicitud_id=folio,
                kind=ArchivoKind.COMPROBANTE.value,
            )
        except ArchivoSolicitud.DoesNotExist:
            return None
        return _to_record(row)

    def delete(self, archivo_id: UUID) -> str:
        try:
            row = ArchivoSolicitud.objects.get(id=archivo_id)
        except ArchivoSolicitud.DoesNotExist as exc:
            raise ArchivoNotFound() from exc
        stored_path = row.stored_path
        row.delete()
        return stored_path


__all__ = ["OrmArchivoRepository"]
