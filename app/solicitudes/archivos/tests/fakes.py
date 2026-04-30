"""In-memory fakes for ArchivoService unit tests."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import BinaryIO
from uuid import UUID, uuid4

from _shared.pagination import Page, PageRequest
from solicitudes.archivos.constants import ArchivoKind
from solicitudes.archivos.exceptions import ArchivoNotFound
from solicitudes.archivos.repositories.archivo.interface import ArchivoRepository
from solicitudes.archivos.schemas import ArchivoDTO, ArchivoRecord
from solicitudes.archivos.storage.interface import FileStorage
from solicitudes.lifecycle.exceptions import SolicitudNotFound
from solicitudes.lifecycle.schemas import (
    SolicitudDetail,
    SolicitudFilter,
    SolicitudRow,
    TransitionInput,
)
from solicitudes.lifecycle.services.lifecycle_service.interface import (
    LifecycleService,
)
from usuarios.constants import Role
from usuarios.schemas import UserDTO


class InMemoryArchivoRepository(ArchivoRepository):
    def __init__(self) -> None:
        self._records: dict[UUID, ArchivoRecord] = {}

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
        rec = ArchivoRecord(
            id=uuid4(),
            solicitud_folio=solicitud_folio,
            field_id=field_id,
            kind=kind,
            original_filename=original_filename,
            stored_path=stored_path,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256=sha256,
            uploaded_at=datetime.now(UTC),
        )
        self._records[rec.id] = rec
        return rec.to_dto()

    def get_record(self, archivo_id: UUID) -> ArchivoRecord:
        try:
            return self._records[archivo_id]
        except KeyError as exc:
            raise ArchivoNotFound() from exc

    def list_by_folio(self, folio: str) -> list[ArchivoDTO]:
        return [
            r.to_dto()
            for r in sorted(
                self._records.values(), key=lambda x: x.uploaded_at
            )
            if r.solicitud_folio == folio
        ]

    def find_form_archivo(
        self, *, folio: str, field_id: UUID
    ) -> ArchivoRecord | None:
        for r in self._records.values():
            if (
                r.solicitud_folio == folio
                and r.kind is ArchivoKind.FORM
                and r.field_id == field_id
            ):
                return r
        return None

    def find_comprobante(self, *, folio: str) -> ArchivoRecord | None:
        for r in self._records.values():
            if (
                r.solicitud_folio == folio
                and r.kind is ArchivoKind.COMPROBANTE
            ):
                return r
        return None

    def delete(self, archivo_id: UUID) -> str:
        try:
            rec = self._records.pop(archivo_id)
        except KeyError as exc:
            raise ArchivoNotFound() from exc
        return rec.stored_path


class InMemoryFileStorage(FileStorage):
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.deleted: list[str] = []
        self._counter = 0
        self.cleanup_calls = 0

    def save(self, *, folio: str, suggested_name: str, content: bytes) -> str:
        self._counter += 1
        ext = "." + suggested_name.rsplit(".", 1)[-1].lower() if "." in suggested_name else ""
        rel = f"solicitudes/{folio}/file-{self._counter:03d}{ext}"
        self.files[rel] = content
        return rel

    def open(self, stored_path: str) -> BinaryIO:
        from io import BytesIO

        return BytesIO(self.files[stored_path])

    def delete(self, stored_path: str) -> None:
        self.deleted.append(stored_path)
        self.files.pop(stored_path, None)

    def cleanup_pending(self) -> None:
        self.cleanup_calls += 1


class InMemoryLifecycleService(LifecycleService):
    """Lookup-only fake. Tests register a :class:`SolicitudDetail` per folio
    via :meth:`register`."""

    def __init__(self) -> None:
        self._details: dict[str, SolicitudDetail] = {}

    def register(self, detail: SolicitudDetail) -> None:
        self._details[detail.folio] = detail

    def get_detail(self, folio: str) -> SolicitudDetail:
        try:
            return self._details[folio]
        except KeyError as exc:
            raise SolicitudNotFound() from exc

    def list_for_solicitante(
        self,
        matricula: str,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]:
        raise NotImplementedError

    def list_for_personal(
        self,
        role: Role,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]:
        raise NotImplementedError

    def transition(
        self,
        *,
        action: str,
        input_dto: TransitionInput,
        actor: UserDTO,
    ) -> SolicitudDetail:
        raise NotImplementedError

    # ---- aggregations: archivos never invokes these; raise to surface misuse. ----

    def list_for_admin(
        self, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:  # pragma: no cover
        raise NotImplementedError

    def iter_for_admin(  # pragma: no cover
        self, *, filters: SolicitudFilter, chunk_size: int = 500
    ):
        raise NotImplementedError

    def aggregate_by_estado(self, *, filters: SolicitudFilter):  # pragma: no cover
        raise NotImplementedError

    def aggregate_by_tipo(self, *, filters: SolicitudFilter):  # pragma: no cover
        raise NotImplementedError

    def aggregate_by_month(self, *, filters: SolicitudFilter):  # pragma: no cover
        raise NotImplementedError
