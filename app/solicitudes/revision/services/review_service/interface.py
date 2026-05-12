"""Review service interface — personal-side wrapper around the lifecycle service."""
from __future__ import annotations

from abc import ABC, abstractmethod

from _shared.pagination import Page, PageRequest
from solicitudes.lifecycle.schemas import SolicitudDetail, SolicitudFilter, SolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO


class ReviewService(ABC):
    @abstractmethod
    def list_assigned(
        self, role: Role, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]: ...

    @abstractmethod
    def get_detail_for_personal(self, folio: str, role: Role) -> SolicitudDetail: ...

    @abstractmethod
    def take(
        self, folio: str, *, actor: UserDTO, observaciones: str = ""
    ) -> SolicitudDetail: ...

    @abstractmethod
    def finalize(
        self, folio: str, *, actor: UserDTO, observaciones: str = ""
    ) -> SolicitudDetail: ...

    @abstractmethod
    def cancel(
        self, folio: str, *, actor: UserDTO, observaciones: str = ""
    ) -> SolicitudDetail: ...
