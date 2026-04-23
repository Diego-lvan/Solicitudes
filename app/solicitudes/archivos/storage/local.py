"""Local-filesystem implementation of :class:`FileStorage`.

Layout
------
Files for solicitud ``SOL-2026-00042`` live under
``MEDIA_ROOT / "solicitudes" / "SOL-2026-00042" / "<uuid>.<ext>"``.

Transactional behaviour
-----------------------
``save`` writes the bytes to a ``.partial`` sibling file and registers a
``transaction.on_commit`` hook that atomically renames it to the final name.
If the surrounding transaction rolls back, the on_commit hook never fires; the
caller must invoke :meth:`cleanup_pending` from its ``except`` branch to
remove the leftover ``.partial`` files.

The pending list is stored on a thread-local so concurrent requests do not
see each other's partial writes, and ``cleanup_pending`` is a per-thread
operation. Note: ``_pending`` is module-level shared state, not per-instance
— ``LocalFileStorage().cleanup_pending()`` drains every pending partial for
the current thread regardless of which instance queued it. This is fine
today (one storage backend) but should move to per-instance state if a
second concrete ``FileStorage`` is ever wired alongside.
"""
from __future__ import annotations

import contextlib
import logging
import os
import threading
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from django.conf import settings
from django.db import transaction

from solicitudes.archivos.storage.interface import FileStorage

logger = logging.getLogger(__name__)

# Suffix used while a file is "in flight" — replaced by `os.replace` on commit.
_PARTIAL_SUFFIX = ".partial"


class _Pending(threading.local):
    paths: list[str]

    def __init__(self) -> None:
        super().__init__()
        self.paths = []


_pending = _Pending()


def _safe_extension(name: str) -> str:
    """Return the lowercased extension of *name* (including the dot), or "".
    Uses :func:`os.path.splitext` so multi-dot filenames behave intuitively
    (``foo.tar.gz`` → ``.gz``)."""
    return os.path.splitext(name)[1].lower()


class LocalFileStorage(FileStorage):
    def __init__(self, media_root: Path | None = None) -> None:
        self._media_root = Path(media_root or settings.MEDIA_ROOT)

    # -- public API -----------------------------------------------------

    def save(self, *, folio: str, suggested_name: str, content: bytes) -> str:
        """Write ``content`` to a ``.partial`` sibling and schedule the rename
        on commit.

        Known limitation: if ``os.replace`` raises *inside* the
        ``transaction.on_commit`` callback (e.g. ENOSPC, EACCES at rename
        time), the DB transaction has already committed — the row points at a
        path that does not exist. We log the failure with ``folio`` and the
        partial/final paths so ops can reconcile, and re-raise so Django marks
        the request as errored. Eventual hardening (write the row inside
        ``on_commit`` after the rename, or move to a content-addressed
        backend) is out of scope for v1.
        """
        ext = _safe_extension(suggested_name)
        rel = f"solicitudes/{folio}/{uuid4().hex}{ext}"
        abs_final = self._media_root / rel
        abs_partial = abs_final.with_name(abs_final.name + _PARTIAL_SUFFIX)
        abs_final.parent.mkdir(parents=True, exist_ok=True)

        with open(abs_partial, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        _pending.paths.append(str(abs_partial))

        partial_str = str(abs_partial)
        final_str = str(abs_final)

        def _commit() -> None:
            try:
                os.replace(partial_str, final_str)
            except FileNotFoundError:
                logger.error(
                    "archivos.commit_missing_partial",
                    extra={
                        "folio": folio,
                        "partial": partial_str,
                        "final": final_str,
                    },
                )
                raise
            except OSError:
                logger.exception(
                    "archivos.commit_rename_failed",
                    extra={
                        "folio": folio,
                        "partial": partial_str,
                        "final": final_str,
                    },
                )
                raise
            finally:
                with contextlib.suppress(ValueError):
                    _pending.paths.remove(partial_str)

        transaction.on_commit(_commit)
        return rel

    def open(self, stored_path: str) -> BinaryIO:
        abs_path = self._abs(stored_path)
        return open(abs_path, "rb")

    def delete(self, stored_path: str) -> None:
        abs_path = self._abs(stored_path)
        try:
            os.remove(abs_path)
        except FileNotFoundError:
            return

    def cleanup_pending(self) -> None:
        leftover = list(_pending.paths)
        _pending.paths.clear()
        for p in leftover:
            try:
                os.remove(p)
            except FileNotFoundError:
                continue
            except OSError:
                logger.exception("archivos.cleanup_failed path=%s", p)

    # -- helpers --------------------------------------------------------

    def _abs(self, stored_path: str) -> Path:
        # Defensive: never let a path escape MEDIA_ROOT.
        candidate = (self._media_root / stored_path).resolve()
        root = self._media_root.resolve()
        if root not in candidate.parents and candidate != root:
            raise ValueError(f"stored_path escapes MEDIA_ROOT: {stored_path!r}")
        return candidate
