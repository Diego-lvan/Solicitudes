"""Pydantic DTOs for the intake feature."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CreateSolicitudInput(BaseModel):
    """Input to ``IntakeService.create``.

    ``valores`` is the JSON-safe dict produced by ``DynamicTipoForm.to_values_dict``
    (form-builder helper). ``is_mentor_at_creation`` is resolved by the view
    via the mentor service before this DTO is built; the intake service trusts
    the boolean and stores it in ``Solicitud.pago_exento`` if applicable.
    """

    tipo_id: UUID
    solicitante_matricula: str
    valores: dict[str, Any]
    is_mentor_at_creation: bool
