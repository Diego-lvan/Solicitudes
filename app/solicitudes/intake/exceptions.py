"""Intake feature exceptions."""
from __future__ import annotations

from _shared.exceptions import DomainValidationError, Unauthorized


class CreatorRoleNotAllowed(Unauthorized):
    code = "creator_role_not_allowed"
    user_message = "Tu rol no puede crear este tipo de solicitud."


class ComprobanteRequired(DomainValidationError):
    """Reserved for service-level enforcement of the comprobante rule.

    Today the requirement is enforced at the form layer: ``build_intake_form``
    appends a required ``FileField`` named ``comprobante`` when the tipo
    requires payment and the actor is not mentor-exempt. If we later move the
    check into ``IntakeService.create`` (e.g. to validate a server-issued
    receipt rather than an upload), this exception is the right surface.
    """

    code = "comprobante_required"
    user_message = "Este tipo requiere comprobante de pago."


class AutoFillRequiredFieldMissing(DomainValidationError):
    """A required auto-fill field has no resolvable value.

    Raised by :class:`AutoFillResolver.resolve` when SIGA is down + cache is
    empty (or any other path that leaves a required ``USER_*`` field with an
    empty :class:`UserDTO` attribute). The intake view maps it to a 422 and
    re-renders the form with a top-of-page alert pointing the alumno to
    Control Escolar.
    """

    code = "auto_fill_required_missing"
    user_message = (
        "No pudimos cargar tus datos académicos del SIGA y este formulario "
        "los necesita. Intenta de nuevo en unos minutos o contacta a "
        "Control Escolar si el problema persiste."
    )
