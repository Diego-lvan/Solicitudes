"""ArchivoService — validation + storage + authorisation.

Cross-feature reads (the parent ``Solicitud``'s estado, payment posture, form
snapshot, and ``responsible_role``) go through :class:`LifecycleService` per
the cross-feature dependency rule. The archivos repository only owns
``ArchivoSolicitud`` rows.
"""
from __future__ import annotations

import os
from hashlib import sha256
from typing import Any, BinaryIO
from uuid import UUID

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from _shared.exceptions import DomainValidationError, Unauthorized
from solicitudes.archivos.constants import (
    COMPROBANTE_EXTENSIONS,
    GLOBAL_MAX_SIZE_BYTES,
    ArchivoKind,
)
from solicitudes.archivos.exceptions import (
    FileExtensionNotAllowed,
    FileTooLarge,
)
from solicitudes.archivos.repositories.archivo.interface import ArchivoRepository
from solicitudes.archivos.schemas import ArchivoDTO, ArchivoRecord
from solicitudes.archivos.services.archivo_service.interface import ArchivoService
from solicitudes.archivos.storage.interface import FileStorage
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.schemas import SolicitudDetail
from solicitudes.lifecycle.services.lifecycle_service.interface import (
    LifecycleService,
)
from usuarios.constants import Role
from usuarios.schemas import UserDTO


class ArchivoServiceImpl(ArchivoService):
    def __init__(
        self,
        *,
        repository: ArchivoRepository,
        storage: FileStorage,
        lifecycle: LifecycleService,
    ) -> None:
        self._repo = repository
        self._storage = storage
        self._lifecycle = lifecycle

    # -- writes ---------------------------------------------------------

    def store_for_solicitud(
        self,
        *,
        folio: str,
        field_id: UUID | None,
        kind: ArchivoKind,
        uploaded_file: UploadedFile,
        uploader: UserDTO,
    ) -> ArchivoDTO:
        detail = self._lifecycle.get_detail(folio)

        if kind is ArchivoKind.FORM:
            self._guard_form_estado(detail)
            field_snapshot = self._lookup_field_in_snapshot(detail, field_id)
            allowed = tuple(
                ext.lower() for ext in field_snapshot.get("accepted_extensions", [])
            )
            field_max_mb = int(field_snapshot.get("max_size_mb", 10))
        else:
            assert kind is ArchivoKind.COMPROBANTE
            self._guard_comprobante_required(detail)
            self._guard_comprobante_estado(detail)
            allowed = tuple(ext.lower() for ext in COMPROBANTE_EXTENSIONS)
            field_max_mb = 10

        original_name = uploaded_file.name or ""
        ext = os.path.splitext(original_name)[1].lower()
        size_bytes = uploaded_file.size or 0
        # Smaller of {field/global cap} wins.
        max_bytes = min(GLOBAL_MAX_SIZE_BYTES, field_max_mb * 1024 * 1024)

        if allowed and ext not in allowed:
            raise FileExtensionNotAllowed(
                extension=ext or "(none)",
                allowed=allowed,
                field=str(field_id) if field_id else "comprobante",
            )
        if size_bytes > max_bytes:
            raise FileTooLarge(
                size_bytes=size_bytes,
                max_bytes=max_bytes,
                field=str(field_id) if field_id else "comprobante",
            )

        # Replace-on-reupload: delete the prior row now (transactional) and
        # schedule the prior bytes' removal for after-commit. Doing the file
        # delete synchronously here would leak the file on rollback (the row
        # restore would then point at a deleted file).
        prior: ArchivoRecord | None
        if kind is ArchivoKind.FORM:
            assert field_id is not None
            prior = self._repo.find_form_archivo(folio=folio, field_id=field_id)
        else:
            prior = self._repo.find_comprobante(folio=folio)
        if prior is not None:
            old_path = self._repo.delete(prior.id)
            storage = self._storage

            def _delete_prior() -> None:
                storage.delete(old_path)

            transaction.on_commit(_delete_prior)

        # Stream-hash and persist. (See Important-4 in the review log: the
        # FileStorage.save signature accepts bytes today; the global 10 MB cap
        # bounds memory. When a cloud backend lands, switch to a chunk
        # iterator.)
        digest = sha256()
        chunks: list[bytes] = []
        for chunk in uploaded_file.chunks():
            digest.update(chunk)
            chunks.append(chunk)
        content = b"".join(chunks)

        stored_path = self._storage.save(
            folio=folio,
            suggested_name=original_name,
            content=content,
        )

        return self._repo.create(
            solicitud_folio=folio,
            field_id=field_id if kind is ArchivoKind.FORM else None,
            kind=kind,
            original_filename=original_name,
            stored_path=stored_path,
            content_type=uploaded_file.content_type or "application/octet-stream",
            size_bytes=size_bytes,
            sha256=digest.hexdigest(),
            uploaded_by_matricula=uploader.matricula,
        )

    def delete_archivo(self, archivo_id: UUID, requester: UserDTO) -> None:
        record = self._repo.get_record(archivo_id)
        detail = self._lifecycle.get_detail(record.solicitud_folio)
        self._authorise_mutate(detail, requester)
        if detail.estado is not Estado.CREADA:
            raise DomainValidationError(
                "Files become immutable once review starts.",
            )
        stored_path = self._repo.delete(archivo_id)
        storage = self._storage

        def _delete_on_commit() -> None:
            storage.delete(stored_path)

        transaction.on_commit(_delete_on_commit)

    # -- reads ----------------------------------------------------------

    def list_for_solicitud(self, folio: str) -> list[ArchivoDTO]:
        return self._repo.list_by_folio(folio)

    def open_for_download(
        self, archivo_id: UUID, requester: UserDTO
    ) -> tuple[ArchivoDTO, BinaryIO]:
        record = self._repo.get_record(archivo_id)
        detail = self._lifecycle.get_detail(record.solicitud_folio)
        self._authorise_read(detail, requester)
        stream = self._storage.open(record.stored_path)
        return record.to_dto(), stream

    # -- guards ---------------------------------------------------------

    @staticmethod
    def _guard_form_estado(detail: SolicitudDetail) -> None:
        if detail.estado is not Estado.CREADA:
            raise DomainValidationError(
                "FORM uploads are only allowed while the solicitud is in CREADA.",
            )

    @staticmethod
    def _guard_comprobante_required(detail: SolicitudDetail) -> None:
        if not (detail.requiere_pago and not detail.pago_exento):
            raise DomainValidationError(
                "This solicitud does not require a comprobante de pago.",
            )

    @staticmethod
    def _guard_comprobante_estado(detail: SolicitudDetail) -> None:
        if detail.estado is not Estado.CREADA:
            raise DomainValidationError(
                "Comprobante uploads are only allowed while the solicitud is in CREADA.",
            )

    @staticmethod
    def _lookup_field_in_snapshot(
        detail: SolicitudDetail, field_id: UUID | None
    ) -> dict[str, Any]:
        if field_id is None:
            raise DomainValidationError("FORM uploads require a field_id.")
        target = str(field_id)
        # ``form_snapshot`` is a frozen Pydantic FormSnapshot with `.fields`.
        for f in detail.form_snapshot.fields:
            if str(f.field_id) == target:
                return f.model_dump(mode="json")
        raise DomainValidationError(
            "field_id is not part of this solicitud's form snapshot.",
        )

    @staticmethod
    def _authorise_read(detail: SolicitudDetail, requester: UserDTO) -> None:
        if requester.matricula == detail.solicitante.matricula:
            return
        if requester.role == detail.tipo.responsible_role:
            return
        if requester.role is Role.ADMIN:
            return
        raise Unauthorized()

    @staticmethod
    def _authorise_mutate(
        detail: SolicitudDetail, requester: UserDTO
    ) -> None:
        if requester.matricula == detail.solicitante.matricula:
            return
        if requester.role is Role.ADMIN:
            return
        raise Unauthorized()
