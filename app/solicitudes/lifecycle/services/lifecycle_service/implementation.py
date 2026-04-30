"""DefaultLifecycleService — state machine, transitions, audit."""
from __future__ import annotations

import logging
from collections.abc import Iterator

from django.db import transaction

from _shared import audit
from _shared.exceptions import Unauthorized
from _shared.pagination import Page, PageRequest
from solicitudes.lifecycle.constants import (
    ACTION_ATENDER,
    ACTION_CANCELAR,
    ACTION_FINALIZAR,
    TRANSITIONS,
    Estado,
)
from solicitudes.lifecycle.exceptions import InvalidStateTransition
from solicitudes.lifecycle.notification_port import NotificationService
from solicitudes.lifecycle.repositories.historial.interface import (
    HistorialRepository,
)
from solicitudes.lifecycle.repositories.solicitud.interface import (
    SolicitudRepository,
)
from solicitudes.lifecycle.schemas import (
    AggregateByEstado,
    AggregateByMonth,
    AggregateByTipo,
    SolicitudDetail,
    SolicitudFilter,
    SolicitudRow,
    TransitionInput,
)
from solicitudes.lifecycle.services.lifecycle_service.interface import (
    LifecycleService,
)
from usuarios.constants import Role
from usuarios.schemas import UserDTO

logger = logging.getLogger(__name__)


class DefaultLifecycleService(LifecycleService):
    """Owns reads, transitions, and the per-transition audit + notification fan-out."""

    def __init__(
        self,
        *,
        solicitud_repository: SolicitudRepository,
        historial_repository: HistorialRepository,
        notification_service: NotificationService,
    ) -> None:
        self._solicitudes = solicitud_repository
        self._historial = historial_repository
        self._notifier = notification_service

    # ---- reads ----

    def get_detail(self, folio: str) -> SolicitudDetail:
        return self._solicitudes.get_by_folio(folio)

    def list_for_solicitante(
        self,
        matricula: str,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]:
        return self._solicitudes.list_for_solicitante(
            matricula, page=page, filters=filters
        )

    def list_for_personal(
        self,
        role: Role,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]:
        # Admin sees every solicitud; everyone else sees only their role's queue.
        if role is Role.ADMIN:
            return self._solicitudes.list_all(page=page, filters=filters)
        return self._solicitudes.list_for_responsible_role(
            role.value, page=page, filters=filters
        )

    # ---- aggregations ----

    def list_for_admin(
        self,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]:
        return self._solicitudes.list_all(page=page, filters=filters)

    def iter_for_admin(
        self, *, filters: SolicitudFilter, chunk_size: int = 500
    ) -> Iterator[SolicitudRow]:
        return self._solicitudes.iter_for_admin(
            filters=filters, chunk_size=chunk_size
        )

    def aggregate_by_estado(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByEstado]:
        return self._solicitudes.aggregate_by_estado(filters=filters)

    def aggregate_by_tipo(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByTipo]:
        return self._solicitudes.aggregate_by_tipo(filters=filters)

    def aggregate_by_month(
        self, *, filters: SolicitudFilter
    ) -> list[AggregateByMonth]:
        return self._solicitudes.aggregate_by_month(filters=filters)

    # ---- transitions ----

    def transition(
        self,
        *,
        action: str,
        input_dto: TransitionInput,
        actor: UserDTO,
    ) -> SolicitudDetail:
        detail = self._solicitudes.get_by_folio(input_dto.folio)

        self._authorize(action=action, detail=detail, actor=actor)

        try:
            estado_destino = TRANSITIONS[(detail.estado, action)]
        except KeyError as exc:
            raise InvalidStateTransition(detail.estado, action) from exc

        with transaction.atomic():
            self._solicitudes.update_estado(
                input_dto.folio, new_estado=estado_destino
            )
            self._historial.append(
                folio=input_dto.folio,
                estado_anterior=detail.estado,
                estado_nuevo=estado_destino,
                actor_matricula=actor.matricula,
                actor_role=actor.role,
                observaciones=input_dto.observaciones,
            )

        self._notifier.notify_state_change(
            folio=input_dto.folio,
            estado_destino=estado_destino,
            observaciones=input_dto.observaciones,
        )
        audit.write(
            "solicitud.estado_cambiado",
            folio=input_dto.folio,
            from_estado=detail.estado.value,
            to_estado=estado_destino.value,
            action=action,
            actor=actor.matricula,
            actor_role=actor.role.value,
        )

        return self._solicitudes.get_by_folio(input_dto.folio)

    # ---- authorization ----

    @staticmethod
    def _authorize(
        *, action: str, detail: SolicitudDetail, actor: UserDTO
    ) -> None:
        """Permission rules layered on top of TRANSITIONS.

        - atender:    responsible role or admin.
        - finalizar:  responsible role or admin.
        - cancelar:   solicitante (only when CREADA), responsible role
                      (CREADA or EN_PROCESO), or admin.

        Estado-vs-action legality is checked separately by the TRANSITIONS map
        in ``transition``; this function is solely about *who* may invoke
        ``action``.
        """
        if actor.role is Role.ADMIN:
            return

        responsible_role = detail.tipo.responsible_role

        if action in (ACTION_ATENDER, ACTION_FINALIZAR):
            if actor.role != responsible_role:
                raise Unauthorized(
                    f"Tu rol no puede {action} esta solicitud."
                )
            return

        if action == ACTION_CANCELAR:
            is_owner = actor.matricula == detail.solicitante.matricula
            is_responsible = actor.role == responsible_role
            if is_owner and detail.estado is Estado.CREADA:
                return
            if is_responsible:
                return
            raise Unauthorized("No puedes cancelar esta solicitud.")

        # Unknown action — programming error, not a state-machine violation.
        # Views only dispatch the three documented actions, so this branch is
        # unreachable from HTTP. Surfacing as ValueError makes the source of
        # the bug clear if it ever fires.
        raise ValueError(f"Unknown action: {action!r}")
