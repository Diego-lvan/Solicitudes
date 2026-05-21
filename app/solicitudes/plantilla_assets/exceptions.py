"""Exceptions for the plantilla_assets feature."""
from __future__ import annotations

from _shared.exceptions import Conflict, DomainValidationError, NotFound


class AssetNotFound(NotFound):
    code = "asset_not_found"
    user_message = "La imagen no existe o fue eliminada."


class InvalidImageType(DomainValidationError):
    code = "invalid_image_type"
    user_message = "El archivo no es una imagen válida (solo PNG/JPG/WEBP)."


class ImageTooLarge(DomainValidationError):
    code = "image_too_large"
    user_message = "La imagen excede el tamaño máximo de 2 MB."


class DuplicateAssetSlug(Conflict):
    code = "duplicate_asset_slug"
    user_message = "Ya existe una imagen con ese nombre en este alcance."
