"""Public service interface for response-batch operations."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO
from uuid import UUID

from solicitudes.respuesta.schemas import (
    ArchivoRespuestaDTO,
    CreateRespuestaInput,
    RespuestaDTO,
)
from usuarios.schemas import UserDTO


class RespuestaService(ABC):
    @abstractmethod
    def create_batch(self, input_dto: CreateRespuestaInput) -> RespuestaDTO:
        """Validate, persist bytes, insert ``RespuestaSolicitud`` + children
        in a single transaction. Raises :class:`InvalidStateForRespuesta`,
        :class:`TooManyFilesInBatch`, :class:`EmptyRespuestaBatch`,
        :class:`ResponseFileTooLarge`,
        :class:`ResponseFileExtensionNotAllowed`, or ``Unauthorized``.
        """

    @abstractmethod
    def list_for_solicitud(
        self, folio: str, *, requester: UserDTO
    ) -> list[RespuestaDTO]:
        """Return batches the requester is allowed to see.

        - admin: always
        - personal in responsible role: always
        - owner: only when estado == FINALIZADA
        - anyone else: empty list
        """

    @abstractmethod
    def open_for_download(
        self, archivo_id: UUID, *, requester: UserDTO
    ) -> tuple[ArchivoRespuestaDTO, BinaryIO]:
        """Authorise + stream a response archivo. Raises ``Unauthorized`` or
        :class:`ArchivoRespuestaNotFound`."""
