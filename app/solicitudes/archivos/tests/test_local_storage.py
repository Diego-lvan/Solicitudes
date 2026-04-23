"""Tests for LocalFileStorage — bytes on disk + transactional semantics."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from django.db import transaction

from solicitudes.archivos.storage.local import LocalFileStorage


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(media_root=tmp_path)


@pytest.mark.django_db(transaction=True)
def test_save_writes_partial_then_renames_on_commit(
    storage: LocalFileStorage, tmp_path: Path
) -> None:
    rel = ""
    with transaction.atomic():
        rel = storage.save(
            folio="SOL-2026-00001",
            suggested_name="my doc.PDF",
            content=b"hello-bytes",
        )
        # Mid-transaction, the .partial sibling exists but the final does not.
        partial = (tmp_path / rel).with_name((tmp_path / rel).name + ".partial")
        assert partial.exists(), "partial file should be on disk during txn"
        assert not (tmp_path / rel).exists()

    # After commit, final file exists, partial is gone.
    assert (tmp_path / rel).exists()
    assert (tmp_path / rel).read_bytes() == b"hello-bytes"
    assert not partial.exists()
    assert rel.startswith("solicitudes/SOL-2026-00001/")
    assert rel.endswith(".pdf"), "extension lower-cased"


@pytest.mark.django_db(transaction=True)
def test_rollback_then_cleanup_pending_removes_partial(
    storage: LocalFileStorage, tmp_path: Path
) -> None:
    partial_path: str | None = None
    try:
        with transaction.atomic():
            rel = storage.save(
                folio="SOL-2026-00099",
                suggested_name="a.txt",
                content=b"x",
            )
            partial_path = str(
                (tmp_path / rel).with_name((tmp_path / rel).name + ".partial")
            )
            assert os.path.exists(partial_path)
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass

    # On_commit hook never fires; partial is still on disk until cleanup.
    assert partial_path is not None
    assert os.path.exists(partial_path)
    storage.cleanup_pending()
    assert not os.path.exists(partial_path)


@pytest.mark.django_db(transaction=True)
def test_open_reads_committed_bytes(
    storage: LocalFileStorage, tmp_path: Path
) -> None:
    with transaction.atomic():
        rel = storage.save(
            folio="SOL-2026-00100",
            suggested_name="r.bin",
            content=b"\x00\x01\x02 commit me",
        )
    with storage.open(rel) as f:
        assert f.read() == b"\x00\x01\x02 commit me"


@pytest.mark.django_db(transaction=True)
def test_delete_is_idempotent(
    storage: LocalFileStorage, tmp_path: Path
) -> None:
    with transaction.atomic():
        rel = storage.save(
            folio="SOL-2026-00200",
            suggested_name="x.zip",
            content=b"zip-bytes",
        )
    assert (tmp_path / rel).exists()
    storage.delete(rel)
    assert not (tmp_path / rel).exists()
    # Second call doesn't raise.
    storage.delete(rel)


def test_open_rejects_path_traversal(
    storage: LocalFileStorage, tmp_path: Path
) -> None:
    with pytest.raises(ValueError):
        storage.open("../etc/passwd")


@pytest.mark.django_db(transaction=True)
def test_cleanup_pending_when_empty_is_noop(storage: LocalFileStorage) -> None:
    storage.cleanup_pending()  # should not raise
