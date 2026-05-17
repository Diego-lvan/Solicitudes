"""In-memory fakes for RespuestaService unit tests."""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from io import BytesIO
from typing import BinaryIO
from uuid import UUID, uuid4

from _shared.pagination import Page, PageRequest
from solicitudes.archivos.storage.interface import FileStorage
from solicitudes.lifecycle.exceptions import SolicitudNotFound
from solicitudes.lifecycle.schemas import (
    AggregateByEstado,
    AggregateByMonth,
    AggregateByTipo,
    SolicitudDetail,
    SolicitudFilter,
    SolicitudRow,
    TransitionInput,
)
from solicitudes.lifecycle.services.lifecycle_service.interface import (
    LifecycleService,
)
from solicitudes.respuesta.exceptions import ArchivoRespuestaNotFound
from solicitudes.respuesta.repositories.respuesta.interface import (
    RespuestaRepository,
)
from solicitudes.respuesta.schemas import (
    ArchivoRespuestaDTO,
    ArchivoRespuestaRecord,
    RespuestaDTO,
)
from usuarios.constants import Role
from usuarios.schemas import UserDTO


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryRespuestaRepository(RespuestaRepository):
    def __init__(self) -> None:
        self._batches: dict[UUID, RespuestaDTO] = {}
        self._archivos: dict[UUID, ArchivoRespuestaRecord] = {}

    def create(
        self,
        *,
        folio: str,
        actor_matricula: str,
        actor_role: str,
        comentario: str,
        archivos: list[ArchivoRespuestaRecord],
    ) -> RespuestaDTO:
        batch_id = uuid4()
        created = _now()
        dto_archivos: list[ArchivoRespuestaDTO] = []
        for a in archivos:
            rec = ArchivoRespuestaRecord(
                id=a.id,
                respuesta_id=batch_id,
                folio=folio,
                nombre_original=a.nombre_original,
                stored_path=a.stored_path,
                content_type=a.content_type,
                size_bytes=a.size_bytes,
                sha256=a.sha256,
                created_at=created,
            )
            self._archivos[rec.id] = rec
            dto_archivos.append(rec.to_dto())
        dto = RespuestaDTO(
            id=batch_id,
            folio=folio,
            actor_matricula=actor_matricula,
            actor_nombre=actor_matricula,
            actor_role=actor_role,
            comentario=comentario,
            created_at=created,
            archivos=dto_archivos,
        )
        self._batches[batch_id] = dto
        return dto

    def list_for_solicitud(self, folio: str) -> list[RespuestaDTO]:
        return sorted(
            (b for b in self._batches.values() if b.folio == folio),
            key=lambda b: b.created_at,
        )

    def get_archivo_record(self, archivo_id: UUID) -> ArchivoRespuestaRecord:
        try:
            return self._archivos[archivo_id]
        except KeyError as exc:
            raise ArchivoRespuestaNotFound() from exc


class RecordingFileStorage(FileStorage):
    def __init__(self, *, fail_after: int | None = None) -> None:
        self.files: dict[str, bytes] = {}
        self.deleted: list[str] = []
        self.cleanup_calls = 0
        self._counter = 0
        self._fail_after = fail_after

    def save(self, *, folio: str, suggested_name: str, content: bytes) -> str:
        self._counter += 1
        if self._fail_after is not None and self._counter > self._fail_after:
            raise OSError("simulated storage failure")
        ext = "." + suggested_name.rsplit(".", 1)[-1].lower() if "." in suggested_name else ""
        rel = f"solicitudes/{folio}/file-{self._counter:03d}{ext}"
        self.files[rel] = content
        return rel

    def open(self, stored_path: str) -> BinaryIO:
        return BytesIO(self.files[stored_path])

    def delete(self, stored_path: str) -> None:
        self.deleted.append(stored_path)
        self.files.pop(stored_path, None)

    def cleanup_pending(self) -> None:
        self.cleanup_calls += 1


class InMemoryLifecycleService(LifecycleService):
    def __init__(self) -> None:
        self._details: dict[str, SolicitudDetail] = {}

    def register(self, detail: SolicitudDetail) -> None:
        self._details[detail.folio] = detail

    def get_detail(self, folio: str) -> SolicitudDetail:
        try:
            return self._details[folio]
        except KeyError as exc:
            raise SolicitudNotFound() from exc

    # Unused for respuesta tests, but the ABC requires them.
    def list_for_solicitante(
        self, matricula: str, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:
        raise NotImplementedError

    def list_for_personal(
        self, role: Role, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:
        raise NotImplementedError

    def list_for_admin(
        self, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:
        raise NotImplementedError

    def iter_for_admin(
        self, *, filters: SolicitudFilter, chunk_size: int = 500
    ) -> Iterator[SolicitudRow]:
        raise NotImplementedError

    def aggregate_by_estado(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByEstado]:
        raise NotImplementedError

    def aggregate_by_tipo(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByTipo]:
        raise NotImplementedError

    def aggregate_by_month(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByMonth]:
        raise NotImplementedError

    def transition(
        self,
        *,
        action: str,
        input_dto: TransitionInput,
        actor: UserDTO,
    ) -> SolicitudDetail:
        raise NotImplementedError
