"""Intake service interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from django import forms

from solicitudes.intake.schemas import CreateSolicitudInput
from solicitudes.intake.services.auto_fill_resolver.interface import (
    AutoFillPreview,
)
from solicitudes.lifecycle.schemas import SolicitudDetail
from solicitudes.tipos.schemas import TipoSolicitudDTO, TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO


@dataclass(frozen=True)
class IntakeFormBundle:
    """Everything the create view needs to render the intake page.

    Bundling the tipo, the dynamic form class, and the auto-fill preview
    keeps the view from reaching into the resolver directly (which would
    skip the cross-feature service boundary). On POST, ``create`` re-hydrates
    the snapshot independently — that second round-trip is intentional: the
    snapshot must be captured at submit-time so any admin edit between GET
    and POST is reflected in the persisted row.
    """

    tipo: TipoSolicitudDTO
    form_cls: type[forms.Form]
    auto_fill: AutoFillPreview


class IntakeService(ABC):
    @abstractmethod
    def list_creatable_tipos(self, role: Role) -> list[TipoSolicitudRow]: ...

    @abstractmethod
    def get_intake_form(
        self,
        slug: str,
        *,
        role: Role,
        is_mentor: bool,
        actor_matricula: str,
    ) -> IntakeFormBundle:
        """Return the tipo, the dynamic form class, and the auto-fill preview.

        The preview is computed from the actor's hydrated ``UserDTO``; the
        view renders it as a read-only "Datos del solicitante" panel above
        the form. ``preview.has_missing_required`` is the view's signal to
        disable the submit button.
        """

    @abstractmethod
    def create(
        self, input_dto: CreateSolicitudInput, *, actor: UserDTO
    ) -> SolicitudDetail: ...

    @abstractmethod
    def cancel_own(
        self, folio: str, *, actor: UserDTO, observaciones: str = ""
    ) -> SolicitudDetail: ...
