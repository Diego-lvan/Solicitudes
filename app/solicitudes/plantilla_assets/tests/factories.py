"""Test factories for the plantilla_assets feature."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from django.core.files.base import ContentFile

from solicitudes.models import PlantillaAsset, PlantillaSolicitud
from usuarios.constants import Role
from usuarios.models import User

# Smallest valid 1x1 PNG (transparent).
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````\x00\x00\x00\x05\x00"
    b"\x01\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _ensure_admin() -> User:
    token = uuid4().hex[:8].upper()
    return User.objects.create(
        matricula=f"ADM-{token}",
        email=f"adm-{token.lower()}@uaz.edu.mx",
        role=Role.ADMIN.value,
    )


def make_global_asset(**overrides: Any) -> PlantillaAsset:
    """Persisted ``PlantillaAsset`` with scope=global and a real 1x1 PNG file."""
    slug = overrides.pop("slug", f"asset_{uuid4().hex[:8]}")
    nombre = overrides.pop("nombre", f"Asset {slug}")
    created_by = overrides.pop("created_by", None) or _ensure_admin()
    mime_type = overrides.pop("mime_type", "image/png")
    file_bytes = overrides.pop("file_bytes", PNG_1X1)
    filename = overrides.pop("original_filename", f"{slug}.png")

    asset = PlantillaAsset(
        slug=slug,
        nombre=nombre,
        scope=PlantillaAsset.SCOPE_GLOBAL,
        plantilla=None,
        mime_type=mime_type,
        size_bytes=len(file_bytes),
        created_by=created_by,
    )
    asset.imagen.save(filename, ContentFile(file_bytes), save=False)
    for k, v in overrides.items():
        setattr(asset, k, v)
    asset.save()
    return asset


def make_plantilla_asset(plantilla: PlantillaSolicitud, **overrides: Any) -> PlantillaAsset:
    """Persisted ``PlantillaAsset`` with scope=plantilla bound to ``plantilla``."""
    slug = overrides.pop("slug", f"passet_{uuid4().hex[:8]}")
    nombre = overrides.pop("nombre", f"PAsset {slug}")
    created_by = overrides.pop("created_by", None) or _ensure_admin()
    mime_type = overrides.pop("mime_type", "image/png")
    file_bytes = overrides.pop("file_bytes", PNG_1X1)
    filename = overrides.pop("original_filename", f"{slug}.png")

    asset = PlantillaAsset(
        slug=slug,
        nombre=nombre,
        scope=PlantillaAsset.SCOPE_PLANTILLA,
        plantilla=plantilla,
        mime_type=mime_type,
        size_bytes=len(file_bytes),
        created_by=created_by,
    )
    asset.imagen.save(filename, ContentFile(file_bytes), save=False)
    for k, v in overrides.items():
        setattr(asset, k, v)
    asset.save()
    return asset
