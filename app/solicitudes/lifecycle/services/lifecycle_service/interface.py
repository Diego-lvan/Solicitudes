"""Lifecycle service interface — owns the state machine + queries."""
from __future__ import annotations

from abc import ABC, abstractmethod

from _shared.pagination import Page, PageRequest
from solicitudes.lifecycle.schemas import (
    SolicitudDetail,
    SolicitudFilter,
    SolicitudRow,
    TransitionInput,
)
from usuarios.constants import Role
from usuarios.schemas import UserDTO


class LifecycleService(ABC):
    """Reads and transitions; the canonical authority on solicitud state."""

    @abstractmethod
    def get_detail(self, folio: str) -> SolicitudDetail: ...

    @abstractmethod
    def list_for_solicitante(
        self,
        matricula: str,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]: ...

    @abstractmethod
    def list_for_personal(
        self,
        role: Role,
        *,
        page: PageRequest,
        filters: SolicitudFilter,
    ) -> Page[SolicitudRow]: ...

    @abstractmethod
    def transition(
        self,
        *,
        action: str,
        input_dto: TransitionInput,
        actor: UserDTO,
    ) -> SolicitudDetail:
        """Apply ``action`` to the solicitud at ``input_dto.folio``.

        Authorisation is enforced here on top of the TRANSITIONS map; raises
        :class:`InvalidStateTransition` for forbidden state changes and
        :class:`Unauthorized` when the actor's role is not allowed.
        """
