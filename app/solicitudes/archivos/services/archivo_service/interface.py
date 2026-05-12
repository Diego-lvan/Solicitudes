"""Public service interface for archivo operations."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO
from uuid import UUID

from django.core.files.uploadedfile import UploadedFile

from solicitudes.archivos.constants import ArchivoKind
from solicitudes.archivos.schemas import ArchivoDTO
from usuarios.schemas import UserDTO


class ArchivoService(ABC):
    @abstractmethod
    def store_for_solicitud(
        self,
        *,
        folio: str,
        field_id: UUID | None,
        kind: ArchivoKind,
        uploaded_file: UploadedFile,
        uploader: UserDTO,
    ) -> ArchivoDTO:
        """Validate, persist bytes, insert ``ArchivoSolicitud`` row.

        Re-uploads (same folio + field_id, or a new comprobante) replace the
        prior row and delete the prior bytes when the surrounding transaction
        commits.

        Raises ``ArchivoNotFound`` (solicitud), ``FileExtensionNotAllowed``,
        ``FileTooLarge``, or ``DomainValidationError`` on validation failure.
        """

    @abstractmethod
    def list_for_solicitud(self, folio: str) -> list[ArchivoDTO]:
        """Return all archivos for *folio* (oldest first)."""

    @abstractmethod
    def open_for_download(
        self, archivo_id: UUID, requester: UserDTO
    ) -> tuple[ArchivoDTO, BinaryIO]:
        """Return DTO + opened binary stream. ``Unauthorized`` on no access."""

    @abstractmethod
    def delete_archivo(self, archivo_id: UUID, requester: UserDTO) -> None:
        """Delete row + bytes. Allowed only while solicitud is in CREADA."""
