"""Default intake service — orchestrates tipo lookup, snapshot, persistence."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from django import forms
from django.db import transaction

from _shared import audit
from solicitudes.intake.exceptions import CreatorRoleNotAllowed
from solicitudes.intake.forms.intake_form import build_intake_form
from solicitudes.intake.schemas import CreateSolicitudInput
from solicitudes.intake.services.intake_service.interface import IntakeService
from solicitudes.lifecycle.constants import ACTION_CANCELAR, Estado
from solicitudes.lifecycle.notification_port import NotificationService
from solicitudes.lifecycle.repositories.historial.interface import (
    HistorialRepository,
)
from solicitudes.lifecycle.repositories.solicitud.interface import (
    SolicitudRepository,
)
from solicitudes.lifecycle.schemas import SolicitudDetail, TransitionInput
from solicitudes.lifecycle.services.folio_service.interface import FolioService
from solicitudes.lifecycle.services.lifecycle_service.interface import (
    LifecycleService,
)
from solicitudes.tipos.schemas import TipoSolicitudDTO, TipoSolicitudRow
from solicitudes.tipos.services.tipo_service.interface import TipoService
from usuarios.constants import Role
from usuarios.schemas import UserDTO

logger = logging.getLogger(__name__)


class DefaultIntakeService(IntakeService):
    """Owns the create-solicitud flow, including snapshot capture and folio allocation."""

    def __init__(
        self,
        *,
        tipo_service: TipoService,
        solicitud_repository: SolicitudRepository,
        historial_repository: HistorialRepository,
        folio_service: FolioService,
        lifecycle_service: LifecycleService,
        notification_service: NotificationService,
    ) -> None:
        self._tipos = tipo_service
        self._solicitudes = solicitud_repository
        self._historial = historial_repository
        self._folios = folio_service
        self._lifecycle = lifecycle_service
        self._notifier = notification_service

    # ---- catalogue / form ----

    def list_creatable_tipos(self, role: Role) -> list[TipoSolicitudRow]:
        return self._tipos.list_for_creator(role)

    def get_intake_form(
        self, slug: str, *, role: Role, is_mentor: bool
    ) -> tuple[TipoSolicitudDTO, type[forms.Form]]:
        tipo = self._tipos.get_for_creator(slug, role)
        with_comprobante = self._needs_comprobante(tipo, is_mentor=is_mentor)
        snapshot = self._tipos.snapshot(tipo.id)
        form_cls = build_intake_form(snapshot, with_comprobante=with_comprobante)
        return tipo, form_cls

    # ---- create ----

    def create(
        self, input_dto: CreateSolicitudInput, *, actor: UserDTO
    ) -> SolicitudDetail:
        tipo = self._tipos.get_for_admin(input_dto.tipo_id)
        if actor.role not in tipo.creator_roles or not tipo.activo:
            raise CreatorRoleNotAllowed()

        # The view has already run the dynamic form; we trust valores were
        # validated against the snapshot. Snapshot is captured *now* so any
        # admin edit between form render and submit is irrelevant — the row
        # records what the user actually saw.
        snapshot = self._tipos.snapshot(tipo.id)

        pago_exento = bool(
            tipo.requires_payment and tipo.mentor_exempt and input_dto.is_mentor_at_creation
        )

        year = datetime.now(tz=UTC).year

        with transaction.atomic():
            folio = self._folios.next_folio(year=year)
            self._solicitudes.create(
                folio=folio,
                tipo_id=tipo.id,
                solicitante_matricula=input_dto.solicitante_matricula,
                estado=Estado.CREADA,
                form_snapshot=snapshot.model_dump(mode="json"),
                valores=input_dto.valores,
                requiere_pago=tipo.requires_payment,
                pago_exento=pago_exento,
            )
            self._historial.append(
                folio=folio,
                estado_anterior=None,
                estado_nuevo=Estado.CREADA,
                actor_matricula=actor.matricula,
                actor_role=actor.role,
                observaciones="",
            )

        self._notifier.notify_creation(
            folio=folio, responsible_role=tipo.responsible_role
        )
        audit.write(
            "solicitud.creada",
            folio=folio,
            tipo_id=str(tipo.id),
            actor=actor.matricula,
            actor_role=actor.role.value,
        )
        logger.info(
            "Solicitud created", extra={"folio": folio, "tipo": tipo.slug}
        )
        return self._solicitudes.get_by_folio(folio)

    # ---- own cancellation ----

    def cancel_own(
        self, folio: str, *, actor: UserDTO, observaciones: str = ""
    ) -> SolicitudDetail:
        # Authorization (owner-only, only when CREADA) is enforced by the
        # lifecycle service. Keeping cancel here as an explicit "solicitante's
        # verb" makes the view boundary cleaner.
        return self._lifecycle.transition(
            action=ACTION_CANCELAR,
            input_dto=TransitionInput(
                folio=folio,
                actor_matricula=actor.matricula,
                observaciones=observaciones,
            ),
            actor=actor,
        )

    # ---- helpers ----

    @staticmethod
    def _needs_comprobante(tipo: TipoSolicitudDTO, *, is_mentor: bool) -> bool:
        if not tipo.requires_payment:
            return False
        return not (tipo.mentor_exempt and is_mentor)
