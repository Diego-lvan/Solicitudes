"""Dependency-injection wiring for the tipos feature."""
from __future__ import annotations

from solicitudes.tipos.repositories.tipo import OrmTipoRepository, TipoRepository
from solicitudes.tipos.services.tipo_service import DefaultTipoService, TipoService


def get_tipo_repository() -> TipoRepository:
    return OrmTipoRepository()


def get_tipo_service() -> TipoService:
    return DefaultTipoService(tipo_repository=get_tipo_repository())
