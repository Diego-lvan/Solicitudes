"""Exceptions raised by the pdf feature."""
from __future__ import annotations

from _shared.exceptions import Conflict, DomainValidationError, NotFound


class PlantillaNotFound(NotFound):
    code = "plantilla_not_found"
    user_message = "La plantilla no existe."


class PlantillaTemplateError(DomainValidationError):
    code = "plantilla_template_error"
    user_message = "La plantilla tiene un error de sintaxis."


class TipoHasNoPlantilla(Conflict):
    code = "tipo_has_no_plantilla"
    user_message = "Este tipo de solicitud no tiene plantilla configurada."
