"""Structured activity-log writer.

Emits a single INFO-level log line per call so events can be tailed and grep'd
out of the JSON log stream. No DB persistence in v1: if compliance later asks
for a queryable audit trail we replace the implementation here without
touching call sites.

Call sites typically pass an ``event`` name (``solicitud.estado_cambiado``,
``solicitud.creada``, …) and arbitrary structured fields:

    write("solicitud.estado_cambiado", folio=folio, from=prev, to=new, actor=...)
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("audit")


def write(event: str, **fields: Any) -> None:
    """Emit a structured audit line tagged with ``event``."""
    logger.info(event, extra={"audit_event": event, **fields})
