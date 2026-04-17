# Feature Package — Full Code Example

This is the canonical layout and code shape for a feature in this project. Pattern: View → Service → Repository, with Pydantic DTOs at every boundary and Django ORM contained inside the repository.

The example below is the `intake` feature inside the `solicitudes` app — the user creates a draft solicitud and submits it.

```
solicitudes/intake/
├── __init__.py
├── apps.py                              # only at app root, not per-feature
├── urls.py
├── dependencies.py
├── schemas.py
├── exceptions.py
├── constants.py
├── permissions.py
├── forms/
│   ├── __init__.py
│   └── create_solicitud_form.py
├── views/
│   ├── __init__.py
│   ├── base.py
│   └── solicitante.py
├── services/
│   └── solicitud/
│       ├── __init__.py
│       ├── interface.py
│       └── implementation.py
├── repositories/
│   └── solicitud/
│       ├── __init__.py
│       ├── interface.py
│       └── implementation.py
└── tests/
    ├── __init__.py
    ├── factories.py
    ├── fakes.py
    ├── test_views.py
    ├── test_services.py
    ├── test_repositories.py
    └── test_forms.py
```

---

## `schemas.py` — Pydantic DTOs

```python
"""Pydantic DTOs for the solicitudes intake feature."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator

from solicitudes.intake.constants import EstadoSolicitud


class CreateSolicitudInput(BaseModel):
    """Input to SolicitudService.create."""
    user_id: UUID
    tipo_solicitud_id: UUID
    titulo: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(min_length=10, max_length=5000)

    @field_validator("titulo", "descripcion")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class TransitionSolicitudInput(BaseModel):
    """Input to SolicitudService.transition."""
    folio: str
    actor_user_id: UUID
    target_estado: EstadoSolicitud
    observacion: Optional[str] = None


class SolicitudRow(BaseModel):
    """Lightweight row for list views."""
    model_config = {"frozen": True}

    id: UUID
    folio: str
    titulo: str
    estado: EstadoSolicitud
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class SolicitudDetail(BaseModel):
    """Hydrated detail for the detail view."""
    model_config = {"frozen": True}

    id: UUID
    folio: str
    titulo: str
    descripcion: str
    estado: EstadoSolicitud
    user_id: UUID
    user_full_name: str
    tipo_solicitud_id: UUID
    tipo_solicitud_nombre: str
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None

    @computed_field
    @property
    def is_editable(self) -> bool:
        return self.estado == EstadoSolicitud.BORRADOR
```

---

## `exceptions.py` — Feature-specific exceptions

```python
"""Exceptions raised by the solicitudes intake feature."""
from __future__ import annotations

from _shared.exceptions import Conflict, DomainValidationError, NotFound


class SolicitudNotFound(NotFound):
    code = "solicitud_not_found"
    user_message = "La solicitud no existe o fue eliminada."


class SolicitudAlreadySubmitted(Conflict):
    code = "solicitud_already_submitted"
    user_message = "Esta solicitud ya fue enviada y no puede modificarse."


class InvalidStateTransition(Conflict):
    code = "invalid_state_transition"

    def __init__(self, current: str, requested: str) -> None:
        super().__init__(f"Cannot transition from {current} to {requested}")
        self.current = current
        self.requested = requested
        self.user_message = f"No se puede pasar de {current} a {requested}."


class FolioCollision(DomainValidationError):
    code = "folio_collision"
    user_message = "El folio ya está en uso. Genera uno nuevo."
```

---

## `repositories/solicitud/interface.py`

```python
"""Abstract interface for solicitud persistence."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from solicitudes.intake.schemas import (
    CreateSolicitudInput,
    SolicitudDetail,
    SolicitudRow,
)


class SolicitudRepository(ABC):
    """Abstract interface for solicitud data operations."""

    @abstractmethod
    def create(self, data: CreateSolicitudInput, folio: str) -> SolicitudDetail:
        """Insert a new solicitud and return its hydrated detail.

        Raises:
            FolioCollision: if the folio already exists.
        """

    @abstractmethod
    def get_by_folio(self, folio: str) -> SolicitudDetail:
        """Return the solicitud with this folio.

        Raises:
            SolicitudNotFound: if no solicitud has this folio.
        """

    @abstractmethod
    def list_by_user(self, user_id: UUID) -> list[SolicitudRow]:
        """List solicitudes for a user, newest first."""

    @abstractmethod
    def update_estado(
        self, folio: str, new_estado: str, submitted_at: Optional[str]
    ) -> SolicitudDetail:
        """Update the estado field, optionally setting submitted_at.

        Raises:
            SolicitudNotFound: if no solicitud has this folio.
        """
```

---

## `repositories/solicitud/implementation.py`

```python
"""ORM-backed implementation of SolicitudRepository."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from django.db import IntegrityError, transaction

from solicitudes.intake.exceptions import FolioCollision, SolicitudNotFound
from solicitudes.intake.repositories.solicitud.interface import SolicitudRepository
from solicitudes.intake.schemas import (
    CreateSolicitudInput,
    SolicitudDetail,
    SolicitudRow,
)
from solicitudes.models import Solicitud  # ORM model lives at app level

logger = logging.getLogger(__name__)


class OrmSolicitudRepository(SolicitudRepository):
    """Django ORM implementation of SolicitudRepository."""

    def create(self, data: CreateSolicitudInput, folio: str) -> SolicitudDetail:
        try:
            with transaction.atomic():
                row = Solicitud.objects.create(
                    folio=folio,
                    titulo=data.titulo,
                    descripcion=data.descripcion,
                    user_id=data.user_id,
                    tipo_solicitud_id=data.tipo_solicitud_id,
                )
        except IntegrityError as e:
            if "folio" in str(e).lower():
                raise FolioCollision(f"folio={folio}")
            raise

        return self._to_detail(row)

    def get_by_folio(self, folio: str) -> SolicitudDetail:
        try:
            row = (
                Solicitud.objects
                .select_related("user", "tipo_solicitud")
                .get(folio=folio)
            )
        except Solicitud.DoesNotExist:
            raise SolicitudNotFound(folio)
        return self._to_detail(row)

    def list_by_user(self, user_id: UUID) -> list[SolicitudRow]:
        rows = (
            Solicitud.objects
            .filter(user_id=user_id)
            .order_by("-created_at")
            .values("id", "folio", "titulo", "estado", "user_id", "created_at", "updated_at")
        )
        return [SolicitudRow(**r) for r in rows]

    def update_estado(
        self, folio: str, new_estado: str, submitted_at: Optional[str]
    ) -> SolicitudDetail:
        try:
            with transaction.atomic():
                row = Solicitud.objects.select_for_update().get(folio=folio)
                row.estado = new_estado
                if submitted_at:
                    row.submitted_at = submitted_at
                row.save(update_fields=["estado", "submitted_at", "updated_at"])
        except Solicitud.DoesNotExist:
            raise SolicitudNotFound(folio)

        # Re-read with relations for the detail
        return self.get_by_folio(folio)

    def _to_detail(self, row: Solicitud) -> SolicitudDetail:
        """Map an ORM row to the SolicitudDetail DTO. Internal."""
        return SolicitudDetail(
            id=row.id,
            folio=row.folio,
            titulo=row.titulo,
            descripcion=row.descripcion,
            estado=row.estado,
            user_id=row.user_id,
            user_full_name=row.user.get_full_name(),
            tipo_solicitud_id=row.tipo_solicitud_id,
            tipo_solicitud_nombre=row.tipo_solicitud.nombre,
            created_at=row.created_at,
            updated_at=row.updated_at,
            submitted_at=row.submitted_at,
        )
```

---

## `services/solicitud/interface.py`

```python
"""Abstract interface for the solicitud service."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from solicitudes.intake.schemas import (
    CreateSolicitudInput,
    SolicitudDetail,
    SolicitudRow,
    TransitionSolicitudInput,
)


class SolicitudService(ABC):
    """Business logic for solicitud lifecycle."""

    @abstractmethod
    def create(self, data: CreateSolicitudInput) -> SolicitudDetail: ...

    @abstractmethod
    def get_detail(self, folio: str, requesting_user_id: UUID) -> SolicitudDetail: ...

    @abstractmethod
    def list_for_user(self, user_id: UUID) -> list[SolicitudRow]: ...

    @abstractmethod
    def transition(self, data: TransitionSolicitudInput) -> SolicitudDetail: ...
```

---

## `services/solicitud/implementation.py`

```python
"""Default solicitud service."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

from solicitudes.intake.constants import (
    ALLOWED_TRANSITIONS,
    EstadoSolicitud,
)
from solicitudes.intake.exceptions import (
    InvalidStateTransition,
    SolicitudAlreadySubmitted,
)
from solicitudes.intake.repositories.solicitud.interface import SolicitudRepository
from solicitudes.intake.schemas import (
    CreateSolicitudInput,
    SolicitudDetail,
    SolicitudRow,
    TransitionSolicitudInput,
)
from solicitudes.intake.services.solicitud.interface import SolicitudService
from _shared.exceptions import Unauthorized

logger = logging.getLogger(__name__)


class DefaultSolicitudService(SolicitudService):
    def __init__(
        self,
        solicitud_repository: SolicitudRepository,
    ) -> None:
        self._repo = solicitud_repository

    def create(self, data: CreateSolicitudInput) -> SolicitudDetail:
        folio = self._generate_folio()
        logger.info("Creating solicitud", extra={"user_id": str(data.user_id), "folio": folio})
        return self._repo.create(data, folio=folio)

    def get_detail(self, folio: str, requesting_user_id: UUID) -> SolicitudDetail:
        detail = self._repo.get_by_folio(folio)
        if detail.user_id != requesting_user_id:
            # Domain-level authorization: owner-only read
            raise Unauthorized("Not the owner of this solicitud")
        return detail

    def list_for_user(self, user_id: UUID) -> list[SolicitudRow]:
        return self._repo.list_by_user(user_id)

    def transition(self, data: TransitionSolicitudInput) -> SolicitudDetail:
        current = self._repo.get_by_folio(data.folio)

        if current.user_id != data.actor_user_id:
            raise Unauthorized("Not the owner of this solicitud")

        if data.target_estado not in ALLOWED_TRANSITIONS.get(current.estado, set()):
            raise InvalidStateTransition(current.estado, data.target_estado)

        if current.estado != EstadoSolicitud.BORRADOR and data.target_estado == EstadoSolicitud.PENDIENTE:
            raise SolicitudAlreadySubmitted(data.folio)

        submitted_at = (
            datetime.now(timezone.utc).isoformat()
            if data.target_estado == EstadoSolicitud.PENDIENTE
            else None
        )
        return self._repo.update_estado(
            folio=data.folio,
            new_estado=data.target_estado,
            submitted_at=submitted_at,
        )

    def _generate_folio(self) -> str:
        return f"SOL-{datetime.now(timezone.utc).year}-{secrets.token_hex(4).upper()}"
```

---

## `forms/create_solicitud_form.py`

```python
"""Form for creating a new solicitud (boundary parser)."""
from __future__ import annotations

from django import forms

from solicitudes.models import TipoSolicitud


class CreateSolicitudForm(forms.Form):
    """Validates user input from the create-solicitud HTML form."""

    tipo_solicitud_id = forms.ModelChoiceField(
        queryset=TipoSolicitud.objects.filter(activo=True),
        label="Tipo de solicitud",
        empty_label="Selecciona un tipo",
    )
    titulo = forms.CharField(
        label="Título",
        min_length=3,
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    descripcion = forms.CharField(
        label="Descripción",
        min_length=10,
        max_length=5000,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 6}),
    )

    def clean_titulo(self) -> str:
        return self.cleaned_data["titulo"].strip()

    def clean_descripcion(self) -> str:
        return self.cleaned_data["descripcion"].strip()
```

---

## `views/solicitante.py`

```python
"""Views for the 'solicitante' actor (the requesting user)."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from _shared.exceptions import AppError
from solicitudes.intake.dependencies import get_solicitud_service
from solicitudes.intake.forms.create_solicitud_form import CreateSolicitudForm
from solicitudes.intake.schemas import CreateSolicitudInput


class CreateSolicitudView(LoginRequiredMixin, View):
    template_name = "solicitudes/intake/create.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"form": CreateSolicitudForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = CreateSolicitudForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form}, status=400)

        # Convert validated cleaned_data into a typed Pydantic DTO before crossing the boundary
        input_dto = CreateSolicitudInput(
            user_id=request.user.id,
            tipo_solicitud_id=form.cleaned_data["tipo_solicitud_id"].id,
            titulo=form.cleaned_data["titulo"],
            descripcion=form.cleaned_data["descripcion"],
        )

        service = get_solicitud_service()
        try:
            detail = service.create(input_dto)
        except AppError as e:
            messages.error(request, e.user_message)
            return render(request, self.template_name, {"form": form}, status=e.http_status)

        messages.success(request, f"Solicitud {detail.folio} creada correctamente.")
        return redirect(reverse("solicitudes:detail", kwargs={"folio": detail.folio}))


class MisSolicitudesView(LoginRequiredMixin, View):
    template_name = "solicitudes/intake/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        service = get_solicitud_service()
        rows = service.list_for_user(request.user.id)
        return render(request, self.template_name, {"solicitudes": rows})
```

---

## `dependencies.py`

```python
"""Dependency injection wiring for the solicitudes intake feature."""
from __future__ import annotations

from solicitudes.intake.repositories.solicitud.implementation import OrmSolicitudRepository
from solicitudes.intake.repositories.solicitud.interface import SolicitudRepository
from solicitudes.intake.services.solicitud.implementation import DefaultSolicitudService
from solicitudes.intake.services.solicitud.interface import SolicitudService


def get_solicitud_repository() -> SolicitudRepository:
    return OrmSolicitudRepository()


def get_solicitud_service() -> SolicitudService:
    return DefaultSolicitudService(
        solicitud_repository=get_solicitud_repository(),
    )
```

---

## `urls.py`

```python
from django.urls import path

from solicitudes.intake.views import solicitante

app_name = "intake"

urlpatterns = [
    path("nueva/", solicitante.CreateSolicitudView.as_view(), name="create"),
    path("mis-solicitudes/", solicitante.MisSolicitudesView.as_view(), name="list"),
]
```

---

## `constants.py`

```python
"""Constants for the solicitudes intake feature."""
from __future__ import annotations

from django.db.models import TextChoices


class EstadoSolicitud(TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    PENDIENTE = "PENDIENTE", "Pendiente"
    APROBADA = "APROBADA", "Aprobada"
    RECHAZADA = "RECHAZADA", "Rechazada"
    CANCELADA = "CANCELADA", "Cancelada"


# Allowed state transitions: from -> set of allowed targets
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    EstadoSolicitud.BORRADOR: {EstadoSolicitud.PENDIENTE, EstadoSolicitud.CANCELADA},
    EstadoSolicitud.PENDIENTE: {EstadoSolicitud.APROBADA, EstadoSolicitud.RECHAZADA, EstadoSolicitud.CANCELADA},
    EstadoSolicitud.APROBADA: set(),  # terminal
    EstadoSolicitud.RECHAZADA: set(),  # terminal
    EstadoSolicitud.CANCELADA: set(),  # terminal
}
```

---

## Key reminders

- The repository is the **only** layer that imports from `solicitudes.models` (the ORM models).
- The service depends on `SolicitudRepository` (ABC), never on `OrmSolicitudRepository`.
- The view turns `cleaned_data` into a `CreateSolicitudInput` Pydantic DTO **before** calling the service.
- Templates receive `SolicitudDetail` / `SolicitudRow` Pydantic objects in context — never querysets, never model instances.
- Domain authorization (owner-only read, state-transition rules) lives in the service. View-level `LoginRequiredMixin` is just the auth gate.
- All exception classes inherit from `_shared.exceptions.AppError` so middleware can map them uniformly.
