"""AutoFillResolver — abstract interface.

The resolver translates a :class:`FormSnapshot` plus an actor matricula into
``{field_id_str: value}`` for every snapshot field whose ``source`` is not
``USER_INPUT``. The intake service merges that dict into the persisted
``valores`` after the dynamic form has validated the alumno-supplied inputs.

Two entry points share the same SIGA hydration round-trip:

* :meth:`resolve` — **strict**. Used at submit time. Raises
  :class:`AutoFillRequiredFieldMissing` if any required auto-fill field has an
  empty resolved value, so a malformed submission cannot persist.
* :meth:`preview` — **lenient**. Used at GET time to render the
  "Datos del solicitante" panel. Never raises; returns a structured outcome
  with labeled ``(label, value)`` pairs and a ``has_missing_required`` flag
  the view uses to disable submit.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from solicitudes.formularios.schemas import FormSnapshot


@dataclass(frozen=True)
class AutoFillPreview:
    """Read-only view of what the resolver *would* attach.

    ``items`` is rendered into the alumno-facing "Datos del solicitante"
    panel, even when ``has_missing_required`` is true (the alumno can still
    see which value the system tried to fetch).

    Deliberately a ``dataclass`` rather than a Pydantic ``BaseModel``: this
    is an internal service-to-service value (resolver → intake service →
    view) that never crosses an external boundary, never validates user
    input, and never serializes to JSON. The architecture rule's "Pydantic
    at every boundary" applies to layer ingress/egress; here a frozen
    dataclass is lighter and equally type-safe.
    """

    items: list[tuple[str, str]] = field(default_factory=list)
    has_missing_required: bool = False


class AutoFillResolver(ABC):
    """Resolve auto-fill values for a snapshot at intake time."""

    @abstractmethod
    def resolve(
        self,
        snapshot: FormSnapshot,
        *,
        actor_matricula: str,
    ) -> dict[str, Any]:
        """Return ``{str(field_id): value}`` for every non-USER_INPUT field.

        Raises
        ------
        AutoFillRequiredFieldMissing
            If any auto-fill field with ``required=True`` resolves to an
            empty value (``""`` or ``None``).
        """

    @abstractmethod
    def preview(
        self,
        snapshot: FormSnapshot,
        *,
        actor_matricula: str,
    ) -> AutoFillPreview:
        """Return labeled ``(label, value)`` pairs for the read-only panel.

        Never raises. Optional auto-fill fields with empty values render as
        an em-dash placeholder; required missing fields flip
        ``has_missing_required`` to ``True`` so the view can disable submit.
        """
