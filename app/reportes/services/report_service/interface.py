"""ReportService interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from _shared.pagination import Page, PageRequest
from reportes.schemas import DashboardData, ReportFilter
from solicitudes.lifecycle.schemas import SolicitudRow


class ReportService(ABC):
    """Aggregates dashboard data and the admin-wide solicitud list."""

    @abstractmethod
    def dashboard(self, *, filter: ReportFilter) -> DashboardData: ...

    @abstractmethod
    def list_paginated(
        self, *, filter: ReportFilter, page: PageRequest
    ) -> Page[SolicitudRow]: ...

    @abstractmethod
    def iter_for_admin(
        self, *, filter: ReportFilter, chunk_size: int = 500
    ) -> Iterator[SolicitudRow]: ...
