"""Repository-layer tests for OrmAssetRepository."""
from __future__ import annotations

import pytest
from django.db import IntegrityError

from solicitudes.models import PlantillaAsset
from solicitudes.pdf.tests.factories import make_plantilla
from solicitudes.plantilla_assets.exceptions import (
    AssetNotFound,
    DuplicateAssetSlug,
)
from solicitudes.plantilla_assets.repositories.asset_repository import (
    OrmAssetRepository,
)
from solicitudes.plantilla_assets.schemas import AssetScope
from solicitudes.plantilla_assets.tests.factories import (
    PNG_1X1,
    _ensure_admin,
    make_global_asset,
    make_plantilla_asset,
)


@pytest.mark.django_db
def test_create_persists_and_returns_dto() -> None:
    admin = _ensure_admin()
    repo = OrmAssetRepository()

    dto = repo.create(
        slug="logo_uaz",
        nombre="Logo UAZ",
        scope=AssetScope.GLOBAL.value,
        plantilla_id=None,
        file_bytes=PNG_1X1,
        original_filename="logo.png",
        mime_type="image/png",
        created_by_id=admin.pk,
    )

    assert dto.slug == "logo_uaz"
    assert dto.scope == AssetScope.GLOBAL
    assert dto.plantilla_id is None
    assert dto.mime_type == "image/png"
    assert dto.size_bytes == len(PNG_1X1)
    assert dto.file_path.endswith(".png")
    assert PlantillaAsset.objects.filter(pk=dto.id).exists()


@pytest.mark.django_db
def test_create_duplicate_slug_raises() -> None:
    admin = _ensure_admin()
    repo = OrmAssetRepository()
    repo.create(
        slug="logo",
        nombre="Logo",
        scope=AssetScope.GLOBAL.value,
        plantilla_id=None,
        file_bytes=PNG_1X1,
        original_filename="logo.png",
        mime_type="image/png",
        created_by_id=admin.pk,
    )
    with pytest.raises(DuplicateAssetSlug):
        repo.create(
            slug="logo",
            nombre="Logo 2",
            scope=AssetScope.GLOBAL.value,
            plantilla_id=None,
            file_bytes=PNG_1X1,
            original_filename="logo2.png",
            mime_type="image/png",
            created_by_id=admin.pk,
        )


@pytest.mark.django_db
def test_list_global_returns_only_global() -> None:
    plantilla = make_plantilla()
    g1 = make_global_asset(nombre="A global", slug="a_glob")
    make_plantilla_asset(plantilla, nombre="P", slug="p_one")
    repo = OrmAssetRepository()

    rows = repo.list_global()
    ids = {r.id for r in rows}
    assert g1.id in ids
    assert all(r.scope == AssetScope.GLOBAL for r in rows)


@pytest.mark.django_db
def test_list_for_plantilla_returns_only_that_plantilla() -> None:
    p1 = make_plantilla(nombre="P1")
    p2 = make_plantilla(nombre="P2")
    a1 = make_plantilla_asset(p1, slug="s1")
    make_plantilla_asset(p2, slug="s2")
    make_global_asset(slug="g_only")
    repo = OrmAssetRepository()

    rows = repo.list_for_plantilla(p1.id)
    assert [r.id for r in rows] == [a1.id]


@pytest.mark.django_db
def test_list_for_render_none_returns_globals_only() -> None:
    p1 = make_plantilla()
    g = make_global_asset(slug="glob1")
    make_plantilla_asset(p1, slug="ps1")
    repo = OrmAssetRepository()

    rows = repo.list_for_render(None)
    ids = {r.id for r in rows}
    assert g.id in ids
    assert all(r.scope == AssetScope.GLOBAL for r in rows)


@pytest.mark.django_db
def test_list_for_render_plantilla_returns_globals_and_plantilla_scoped() -> None:
    p1 = make_plantilla()
    g = make_global_asset(slug="glob1")
    pa = make_plantilla_asset(p1, slug="ps1")
    repo = OrmAssetRepository()

    rows = repo.list_for_render(p1.id)
    ids = {r.id for r in rows}
    assert {g.id, pa.id}.issubset(ids)


@pytest.mark.django_db
def test_get_missing_raises_asset_not_found() -> None:
    from uuid import uuid4

    repo = OrmAssetRepository()
    with pytest.raises(AssetNotFound):
        repo.get(uuid4())


@pytest.mark.django_db
def test_delete_removes_row() -> None:
    asset = make_global_asset()
    repo = OrmAssetRepository()
    repo.delete(asset.id)
    assert not PlantillaAsset.objects.filter(pk=asset.id).exists()


@pytest.mark.django_db
def test_delete_missing_raises_asset_not_found() -> None:
    from uuid import uuid4

    repo = OrmAssetRepository()
    with pytest.raises(AssetNotFound):
        repo.delete(uuid4())


@pytest.mark.django_db
def test_scope_consistency_constraint_global_with_plantilla_raises() -> None:
    """scope=global with a plantilla FK violates the check constraint."""
    plantilla = make_plantilla()
    admin = _ensure_admin()
    asset = PlantillaAsset(
        slug="bad_global",
        nombre="Bad Global",
        scope=PlantillaAsset.SCOPE_GLOBAL,
        plantilla=plantilla,  # inconsistent
        mime_type="image/png",
        size_bytes=len(PNG_1X1),
        created_by=admin,
    )
    from django.core.files.base import ContentFile

    asset.imagen.save("x.png", ContentFile(PNG_1X1), save=False)
    with pytest.raises(IntegrityError):
        asset.save()


@pytest.mark.django_db
def test_scope_consistency_constraint_plantilla_without_plantilla_raises() -> None:
    """scope=plantilla without a plantilla FK violates the check constraint."""
    admin = _ensure_admin()
    asset = PlantillaAsset(
        slug="bad_plantilla",
        nombre="Bad Plantilla",
        scope=PlantillaAsset.SCOPE_PLANTILLA,
        plantilla=None,  # inconsistent
        mime_type="image/png",
        size_bytes=len(PNG_1X1),
        created_by=admin,
    )
    from django.core.files.base import ContentFile

    asset.imagen.save("x.png", ContentFile(PNG_1X1), save=False)
    with pytest.raises(IntegrityError):
        asset.save()


@pytest.mark.django_db
def test_delete_tolerates_already_missing_file() -> None:
    """If the underlying image file vanished, ``delete`` still removes the row
    instead of crashing on the storage cleanup."""
    import os

    asset = make_global_asset()
    repo = OrmAssetRepository()
    # Remove the backing file out from under the ORM.
    path = asset.imagen.path
    if os.path.exists(path):
        os.remove(path)
    repo.delete(asset.id)
    assert not PlantillaAsset.objects.filter(pk=asset.id).exists()
