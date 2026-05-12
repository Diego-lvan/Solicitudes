"""DI wiring for the archivos feature."""
from __future__ import annotations

from solicitudes.archivos.repositories.archivo.implementation import (
    OrmArchivoRepository,
)
from solicitudes.archivos.repositories.archivo.interface import ArchivoRepository
from solicitudes.archivos.services.archivo_service.implementation import (
    ArchivoServiceImpl,
)
from solicitudes.archivos.services.archivo_service.interface import ArchivoService
from solicitudes.archivos.storage.interface import FileStorage
from solicitudes.archivos.storage.local import LocalFileStorage
from solicitudes.lifecycle.dependencies import get_lifecycle_service


def get_file_storage() -> FileStorage:
    return LocalFileStorage()


def get_archivo_repository() -> ArchivoRepository:
    return OrmArchivoRepository()


def get_archivo_service() -> ArchivoService:
    return ArchivoServiceImpl(
        repository=get_archivo_repository(),
        storage=get_file_storage(),
        lifecycle=get_lifecycle_service(),
    )
