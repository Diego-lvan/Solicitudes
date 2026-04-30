"""ExportService interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from reportes.schemas import ReportFilter


class ExportService(ABC):
    """Streams a filtered solicitud list as CSV or PDF bytes."""

    @abstractmethod
    def export(self, *, filter: ReportFilter) -> bytes: ...

    @property
    @abstractmethod
    def content_type(self) -> str: ...

    @property
    @abstractmethod
    def filename(self) -> str: ...
