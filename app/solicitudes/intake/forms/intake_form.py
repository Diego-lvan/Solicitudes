"""Intake form factory.

Wraps the dynamic form produced by ``build_django_form`` and conditionally
appends a required ``comprobante`` :class:`FileField` when the tipo requires
payment and the actor is not mentor-exempt.

Why a function and not a class: ``build_django_form`` already returns a Form
class; we just need a thin variant on top. Producing it as a callable keeps
the intake view's wiring uniform with the formularios builder.
"""
from __future__ import annotations

from django import forms

from solicitudes.formularios.builder import build_django_form
from solicitudes.formularios.schemas import FormSnapshot

COMPROBANTE_FIELD = "comprobante"

# Comprobante always allows the same payment-receipt extensions; we keep this
# narrow and centralized so legal updates land in one place.
COMPROBANTE_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")
COMPROBANTE_MAX_SIZE_MB = 5


def build_intake_form(
    snapshot: FormSnapshot, *, with_comprobante: bool
) -> type[forms.Form]:
    base = build_django_form(snapshot)
    if not with_comprobante:
        return base

    accepted = ",".join(COMPROBANTE_EXTENSIONS)
    extra_attrs: dict[str, object] = {
        COMPROBANTE_FIELD: forms.FileField(
            label="Comprobante de pago",
            required=True,
            help_text=(
                "Adjunta el comprobante en formato PDF o imagen "
                f"(máx. {COMPROBANTE_MAX_SIZE_MB} MB)."
            ),
            widget=forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": accepted}
            ),
        ),
    }
    # Append comprobante after the dynamic fields.
    field_order = [*list(getattr(base, "field_order", [])), COMPROBANTE_FIELD]
    extra_attrs["field_order"] = field_order
    return type("IntakeForm", (base,), extra_attrs)
