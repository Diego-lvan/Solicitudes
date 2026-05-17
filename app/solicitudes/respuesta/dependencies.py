"""DI wiring for the respuesta feature."""
from __future__ import annotations

from solicitudes.archivos.dependencies import get_file_storage
from solicitudes.lifecycle.dependencies import get_lifecycle_service
from solicitudes.respuesta.repositories.respuesta.implementation import (
    OrmRespuestaRepository,
)
from solicitudes.respuesta.repositories.respuesta.interface import (
    RespuestaRepository,
)
from solicitudes.respuesta.services.respuesta_service.implementation import (
    DefaultRespuestaService,
)
from solicitudes.respuesta.services.respuesta_service.interface import (
    RespuestaService,
)


def get_respuesta_repository() -> RespuestaRepository:
    return OrmRespuestaRepository()


def get_respuesta_service() -> RespuestaService:
    return DefaultRespuestaService(
        respuesta_repository=get_respuesta_repository(),
        file_storage=get_file_storage(),
        lifecycle_service=get_lifecycle_service(),
    )
