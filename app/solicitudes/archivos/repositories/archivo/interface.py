"""Persistence interface for ``ArchivoSolicitud`` rows."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from solicitudes.archivos.constants import ArchivoKind
from solicitudes.archivos.schemas import ArchivoDTO, ArchivoRecord


class ArchivoRepository(ABC):
    @abstractmethod
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
        """Insert a new archivo row and return its public DTO."""

    @abstractmethod
    def get_record(self, archivo_id: UUID) -> ArchivoRecord:
        """Return the internal record (incl. ``stored_path``).

        Raises :class:`solicitudes.archivos.exceptions.ArchivoNotFound`.
        """

    @abstractmethod
    def list_by_folio(self, folio: str) -> list[ArchivoDTO]:
        """All archivos attached to *folio*, oldest first."""

    @abstractmethod
    def find_form_archivo(
        self, *, folio: str, field_id: UUID
    ) -> ArchivoRecord | None:
        """The (unique) FORM archivo for ``(folio, field_id)`` if any."""

    @abstractmethod
    def find_comprobante(self, *, folio: str) -> ArchivoRecord | None:
        """The (unique) COMPROBANTE archivo for ``folio`` if any."""

    @abstractmethod
    def delete(self, archivo_id: UUID) -> str:
        """Delete the row and return its prior ``stored_path`` so the storage
        layer can remove the bytes. Raises ``ArchivoNotFound`` if absent."""
