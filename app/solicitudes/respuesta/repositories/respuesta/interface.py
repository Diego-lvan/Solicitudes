"""Persistence interface for ``RespuestaSolicitud`` + ``ArchivoRespuesta`` rows."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from solicitudes.respuesta.schemas import ArchivoRespuestaRecord, RespuestaDTO


class RespuestaRepository(ABC):
    @abstractmethod
    def create(
        self,
        *,
        folio: str,
        actor_matricula: str,
        actor_role: str,
        comentario: str,
        archivos: list[ArchivoRespuestaRecord],
    ) -> RespuestaDTO:
        """Insert the batch row and its file rows in a single transaction.

        Returns the hydrated DTO. The caller is responsible for already having
        persisted the bytes through :class:`FileStorage`; this repo only owns
        the DB rows.
        """

    @abstractmethod
    def list_for_solicitud(self, folio: str) -> list[RespuestaDTO]:
        """All batches for ``folio``, oldest first, with their files."""

    @abstractmethod
    def get_archivo_record(self, archivo_id: UUID) -> ArchivoRespuestaRecord:
        """Internal record (incl. ``stored_path``) for the download path.

        Raises :class:`ArchivoRespuestaNotFound`.
        """
