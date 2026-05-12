"""Default review service — thin wrapper on the lifecycle service."""
from __future__ import annotations

from _shared.exceptions import Unauthorized
from _shared.pagination import Page, PageRequest
from solicitudes.lifecycle.constants import (
    ACTION_ATENDER,
    ACTION_CANCELAR,
    ACTION_FINALIZAR,
)
from solicitudes.lifecycle.schemas import (
    SolicitudDetail,
    SolicitudFilter,
    SolicitudRow,
    TransitionInput,
)
from solicitudes.lifecycle.services.lifecycle_service.interface import (
    LifecycleService,
)
from solicitudes.revision.services.review_service.interface import ReviewService
from usuarios.constants import Role
from usuarios.schemas import UserDTO


class DefaultReviewService(ReviewService):
    """Owns role-scoped views of the queue and delegates transitions to lifecycle."""

    def __init__(self, *, lifecycle_service: LifecycleService) -> None:
        self._lifecycle = lifecycle_service

    def list_assigned(
        self, role: Role, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:
        return self._lifecycle.list_for_personal(role, page=page, filters=filters)

    def get_detail_for_personal(self, folio: str, role: Role) -> SolicitudDetail:
        detail = self._lifecycle.get_detail(folio)
        if role is Role.ADMIN:
            return detail
        if role != detail.tipo.responsible_role:
            raise Unauthorized("No puedes ver esta solicitud.")
        return detail

    def take(
        self, folio: str, *, actor: UserDTO, observaciones: str = ""
    ) -> SolicitudDetail:
        return self._lifecycle.transition(
            action=ACTION_ATENDER,
            input_dto=TransitionInput(
                folio=folio,
                actor_matricula=actor.matricula,
                observaciones=observaciones,
            ),
            actor=actor,
        )

    def finalize(
        self, folio: str, *, actor: UserDTO, observaciones: str = ""
    ) -> SolicitudDetail:
        return self._lifecycle.transition(
            action=ACTION_FINALIZAR,
            input_dto=TransitionInput(
                folio=folio,
                actor_matricula=actor.matricula,
                observaciones=observaciones,
            ),
            actor=actor,
        )

    def cancel(
        self, folio: str, *, actor: UserDTO, observaciones: str = ""
    ) -> SolicitudDetail:
        return self._lifecycle.transition(
            action=ACTION_CANCELAR,
            input_dto=TransitionInput(
                folio=folio,
                actor_matricula=actor.matricula,
                observaciones=observaciones,
            ),
            actor=actor,
        )
