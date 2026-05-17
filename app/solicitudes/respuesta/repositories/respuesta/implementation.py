"""ORM-backed implementation of :class:`RespuestaRepository`."""
from __future__ import annotations

from uuid import UUID, uuid4

from django.db import transaction

from solicitudes.models import ArchivoRespuesta, RespuestaSolicitud
from solicitudes.respuesta.exceptions import ArchivoRespuestaNotFound
from solicitudes.respuesta.repositories.respuesta.interface import (
    RespuestaRepository,
)
from solicitudes.respuesta.schemas import (
    ArchivoRespuestaDTO,
    ArchivoRespuestaRecord,
    RespuestaDTO,
)


def _batch_to_dto(row: RespuestaSolicitud) -> RespuestaDTO:
    archivos = [
        ArchivoRespuestaDTO(
            id=a.id,
            respuesta_id=row.id,
            nombre_original=a.nombre_original,
            content_type=a.content_type,
            size_bytes=a.size_bytes,
            created_at=a.created_at,
        )
        for a in row.archivos.all()
    ]
    return RespuestaDTO(
        id=row.id,
        folio=row.solicitud_id,
        actor_matricula=row.actor.matricula,
        actor_nombre=row.actor.full_name or row.actor.matricula,
        actor_role=row.actor_role,
        comentario=row.comentario,
        created_at=row.created_at,
        archivos=archivos,
    )


def _archivo_to_record(row: ArchivoRespuesta) -> ArchivoRespuestaRecord:
    return ArchivoRespuestaRecord(
        id=row.id,
        respuesta_id=row.respuesta_id,
        folio=row.respuesta.solicitud_id,
        nombre_original=row.nombre_original,
        stored_path=row.stored_path,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        created_at=row.created_at,
    )


class OrmRespuestaRepository(RespuestaRepository):
    def create(
        self,
        *,
        folio: str,
        actor_matricula: str,
        actor_role: str,
        comentario: str,
        archivos: list[ArchivoRespuestaRecord],
    ) -> RespuestaDTO:
        with transaction.atomic():
            batch = RespuestaSolicitud.objects.create(
                id=uuid4(),
                solicitud_id=folio,
                actor_id=actor_matricula,
                actor_role=actor_role,
                comentario=comentario,
            )
            ArchivoRespuesta.objects.bulk_create(
                [
                    ArchivoRespuesta(
                        id=a.id,
                        respuesta_id=batch.id,
                        nombre_original=a.nombre_original,
                        stored_path=a.stored_path,
                        content_type=a.content_type,
                        size_bytes=a.size_bytes,
                        sha256=a.sha256,
                    )
                    for a in archivos
                ]
            )
        # Re-fetch with related actor + archivos for a hydrated DTO.
        return self._get_by_id_hydrated(batch.id)

    def _get_by_id_hydrated(self, batch_id: UUID) -> RespuestaDTO:
        row = (
            RespuestaSolicitud.objects.select_related("actor")
            .prefetch_related("archivos")
            .get(id=batch_id)
        )
        return _batch_to_dto(row)

    def list_for_solicitud(self, folio: str) -> list[RespuestaDTO]:
        rows = (
            RespuestaSolicitud.objects.filter(solicitud_id=folio)
            .select_related("actor")
            .prefetch_related("archivos")
            .order_by("created_at")
        )
        return [_batch_to_dto(r) for r in rows]

    def get_archivo_record(self, archivo_id: UUID) -> ArchivoRespuestaRecord:
        try:
            row = ArchivoRespuesta.objects.select_related("respuesta").get(
                id=archivo_id
            )
        except ArchivoRespuesta.DoesNotExist as exc:
            raise ArchivoRespuestaNotFound() from exc
        return _archivo_to_record(row)


__all__ = ["OrmRespuestaRepository"]
