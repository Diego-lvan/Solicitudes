"""Default RespuestaService — state guards, validation, transactional persistence."""
from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from hashlib import sha256
from typing import BinaryIO
from uuid import UUID, uuid4

from django.db import transaction

from _shared.exceptions import Unauthorized
from solicitudes.archivos.storage.interface import FileStorage
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.schemas import SolicitudDetail
from solicitudes.lifecycle.services.lifecycle_service.interface import (
    LifecycleService,
)
from solicitudes.respuesta.constants import (
    ALLOWED_EXTENSIONS,
    GLOBAL_MAX_SIZE_BYTES,
    MAX_FILES_PER_BATCH,
)
from solicitudes.respuesta.exceptions import (
    EmptyRespuestaBatch,
    InvalidStateForRespuesta,
    ResponseFileExtensionNotAllowed,
    ResponseFileTooLarge,
    TooManyFilesInBatch,
)
from solicitudes.respuesta.repositories.respuesta.interface import (
    RespuestaRepository,
)
from solicitudes.respuesta.schemas import (
    ArchivoRespuestaDTO,
    ArchivoRespuestaRecord,
    CreateRespuestaInput,
    RespuestaDTO,
)
from solicitudes.respuesta.services.respuesta_service.interface import (
    RespuestaService,
)
from usuarios.constants import Role
from usuarios.schemas import UserDTO

logger = logging.getLogger(__name__)


class DefaultRespuestaService(RespuestaService):
    def __init__(
        self,
        *,
        respuesta_repository: RespuestaRepository,
        file_storage: FileStorage,
        lifecycle_service: LifecycleService,
    ) -> None:
        self._repo = respuesta_repository
        self._storage = file_storage
        self._lifecycle = lifecycle_service

    # -- writes --------------------------------------------------------

    def create_batch(self, input_dto: CreateRespuestaInput) -> RespuestaDTO:
        self._assert_payload_invariants(input_dto)

        detail = self._lifecycle.get_detail(input_dto.folio)

        # State guard.
        if detail.estado is not Estado.EN_PROCESO:
            raise InvalidStateForRespuesta(
                f"estado={detail.estado.value}, expected EN_PROCESO"
            )

        # Authz guard: only admin or personal in the row's responsible_role.
        # The view layer's ReviewerRequiredMixin already gates the URL, but
        # the service must independently enforce the cross-cut so unit tests
        # of the service exercise authz directly.
        self._authorise_create(detail, input_dto.actor_role)

        self._validate_files(input_dto)

        # Persist transactionally. On any exception inside the block, the DB
        # is rolled back and the storage layer's on_commit rename hooks do
        # not fire — leaving .partial files that ``cleanup_pending`` removes
        # in the outer try/finally.
        try:
            with transaction.atomic():
                records: list[ArchivoRespuestaRecord] = []
                for uf in input_dto.archivos:
                    digest = sha256(uf.content).hexdigest()
                    stored_path = self._storage.save(
                        folio=input_dto.folio,
                        suggested_name=uf.nombre_original,
                        content=uf.content,
                    )
                    records.append(
                        ArchivoRespuestaRecord(
                            id=uuid4(),
                            respuesta_id=uuid4(),  # overwritten by repo.create
                            folio=input_dto.folio,
                            nombre_original=uf.nombre_original,
                            stored_path=stored_path,
                            content_type=uf.content_type,
                            size_bytes=uf.size_bytes,
                            sha256=digest,
                            # placeholder; ORM sets created_at via auto_now_add
                            created_at=_aware_now(),
                        )
                    )
                dto = self._repo.create(
                    folio=input_dto.folio,
                    actor_matricula=input_dto.actor_matricula,
                    actor_role=input_dto.actor_role,
                    comentario=input_dto.comentario,
                    archivos=records,
                )
        except Exception:
            # Storage may have queued partials before the DB error; the
            # on_commit hooks won't fire on rollback, so drain them.
            self._storage.cleanup_pending()
            raise

        logger.info(
            "respuesta.created",
            extra={
                "folio": input_dto.folio,
                "actor": input_dto.actor_matricula,
                "archivos": len(dto.archivos),
                "has_comentario": bool(dto.comentario.strip()),
            },
        )
        return dto

    @staticmethod
    def _assert_payload_invariants(input_dto: CreateRespuestaInput) -> None:
        # Re-assert payload invariants in case the caller bypassed the DTO
        # validator (defensive: the DTO validator already enforces these).
        if not input_dto.archivos and not input_dto.comentario.strip():
            raise EmptyRespuestaBatch()
        if len(input_dto.archivos) > MAX_FILES_PER_BATCH:
            raise TooManyFilesInBatch(
                count=len(input_dto.archivos), max_count=MAX_FILES_PER_BATCH
            )

    @staticmethod
    def _validate_files(input_dto: CreateRespuestaInput) -> None:
        for uf in input_dto.archivos:
            ext = os.path.splitext(uf.nombre_original)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise ResponseFileExtensionNotAllowed(
                    extension=ext or "(none)", allowed=ALLOWED_EXTENSIONS
                )
            if uf.size_bytes > GLOBAL_MAX_SIZE_BYTES:
                raise ResponseFileTooLarge(
                    size_bytes=uf.size_bytes, max_bytes=GLOBAL_MAX_SIZE_BYTES
                )

    # -- reads ---------------------------------------------------------

    def list_for_solicitud(
        self, folio: str, *, requester: UserDTO
    ) -> list[RespuestaDTO]:
        detail = self._lifecycle.get_detail(folio)
        if not self._can_read(detail, requester):
            return []
        return self._repo.list_for_solicitud(folio)

    def open_for_download(
        self, archivo_id: UUID, *, requester: UserDTO
    ) -> tuple[ArchivoRespuestaDTO, BinaryIO]:
        record = self._repo.get_archivo_record(archivo_id)
        detail = self._lifecycle.get_detail(record.folio)
        if not self._can_read(detail, requester):
            raise Unauthorized("No puedes descargar este archivo de respuesta.")
        stream = self._storage.open(record.stored_path)
        return record.to_dto(), stream

    # -- guards --------------------------------------------------------

    @staticmethod
    def _authorise_create(detail: SolicitudDetail, actor_role: str) -> None:
        if actor_role == Role.ADMIN.value:
            return
        if actor_role == detail.tipo.responsible_role:
            return
        raise Unauthorized(
            "Solo el rol responsable o un administrador pueden adjuntar respuesta."
        )

    @staticmethod
    def _can_read(detail: SolicitudDetail, requester: UserDTO) -> bool:
        if requester.role is Role.ADMIN:
            return True
        if requester.role == detail.tipo.responsible_role:
            return True
        return (
            requester.matricula == detail.solicitante.matricula
            and detail.estado is Estado.FINALIZADA
        )


def _aware_now() -> datetime:
    return datetime.now(UTC)
