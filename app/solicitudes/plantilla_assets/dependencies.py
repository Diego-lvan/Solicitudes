"""DI wiring for the plantilla_assets feature."""
from __future__ import annotations

from solicitudes.plantilla_assets.repositories.asset_repository import (
    AssetRepository,
    OrmAssetRepository,
)
from solicitudes.plantilla_assets.services.asset_service import (
    AssetService,
    DefaultAssetService,
)


def get_asset_repository() -> AssetRepository:
    return OrmAssetRepository()


def get_asset_service() -> AssetService:
    return DefaultAssetService(asset_repository=get_asset_repository())
