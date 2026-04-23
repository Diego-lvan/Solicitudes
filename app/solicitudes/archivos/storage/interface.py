"""Abstract file-storage interface for solicitud attachments.

The storage layer owns *where the bytes live*. Implementations may write to
the local filesystem, S3, Azure Blob, etc. The repository owns the index
row in the database; the service composes the two inside a transaction.

Transactional contract
----------------------
- ``save`` writes the bytes immediately but does NOT make them permanent
  until the surrounding ``transaction.atomic()`` block commits. Implementations
  are expected to register a ``transaction.on_commit`` hook that finalises the
  write (e.g. rename of a ``.partial`` file to its destination).
- ``cleanup_pending`` must be called by the caller from an ``except`` branch
  inside the same outermost atomic block so any half-written files left over
  from a rolled-back transaction are deleted. Calling it on the success path
  is a no-op.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class FileStorage(ABC):
    @abstractmethod
    def save(self, *, folio: str, suggested_name: str, content: bytes) -> str:
        """Write *content* and return the ``stored_path`` (relative).

        The path becomes durable when the surrounding transaction commits.
        On rollback, the caller must invoke :meth:`cleanup_pending`.
        """

    @abstractmethod
    def open(self, stored_path: str) -> BinaryIO:
        """Open an existing stored file for binary reading."""

    @abstractmethod
    def delete(self, stored_path: str) -> None:
        """Remove a stored file. Idempotent: missing files are not an error."""

    @abstractmethod
    def cleanup_pending(self) -> None:
        """Discard any partial writes scheduled by this thread/connection.

        Idempotent. Intended for ``except`` branches in the service or view.
        """
