"""Intake service interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from django import forms

from solicitudes.intake.schemas import CreateSolicitudInput
from solicitudes.lifecycle.schemas import SolicitudDetail
from solicitudes.tipos.schemas import TipoSolicitudDTO, TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO


class IntakeService(ABC):
    @abstractmethod
    def list_creatable_tipos(self, role: Role) -> list[TipoSolicitudRow]: ...

    @abstractmethod
    def get_intake_form(
        self, slug: str, *, role: Role, is_mentor: bool
    ) -> tuple[TipoSolicitudDTO, type[forms.Form]]:
        """Return the tipo and a bound-ready dynamic form (with comprobante if needed)."""

    @abstractmethod
    def create(
        self, input_dto: CreateSolicitudInput, *, actor: UserDTO
    ) -> SolicitudDetail: ...

    @abstractmethod
    def cancel_own(
        self, folio: str, *, actor: UserDTO, observaciones: str = ""
    ) -> SolicitudDetail: ...
