"""Direct unit tests for ``DefaultIntakeService``.

Covers the domain invariants that aren't directly visible from the view tests:

- the snapshot stored on the row is the one ``TipoService.snapshot`` returns
  *at create time*, not a snapshot the view captured earlier;
- ``pago_exento`` is True only when ``requires_payment AND mentor_exempt AND
  is_mentor_at_creation`` (full truth table);
- the initial historial row has ``estado_anterior=None`` and the actor's role
  is snapshotted alongside;
- a notification is fired with the tipo's ``responsible_role`` so 007 can
  route the message to the right inbox.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from _shared.pagination import Page, PageRequest
from solicitudes.formularios.schemas import FormSnapshot
from solicitudes.intake.exceptions import CreatorRoleNotAllowed
from solicitudes.intake.schemas import CreateSolicitudInput
from solicitudes.intake.services.auto_fill_resolver.interface import (
    AutoFillPreview,
    AutoFillResolver,
)
from solicitudes.intake.services.intake_service.implementation import (
    DefaultIntakeService,
)
from solicitudes.lifecycle.constants import Estado
from solicitudes.lifecycle.repositories.solicitud.interface import (
    SolicitudRepository,
)
from solicitudes.lifecycle.schemas import (
    SolicitudDetail,
    SolicitudFilter,
    SolicitudRow,
    TransitionInput,
)
from solicitudes.lifecycle.services.folio_service.interface import FolioService
from solicitudes.lifecycle.services.lifecycle_service.interface import (
    LifecycleService,
)
from solicitudes.lifecycle.tests.fakes import (
    InMemoryHistorialRepository,
    InMemorySolicitudRepository,
    RecordingNotificationService,
)
from solicitudes.tipos.schemas import (
    FieldDefinitionDTO,
    TipoSolicitudDTO,
    TipoSolicitudRow,
)
from solicitudes.tipos.services.tipo_service.interface import TipoService
from usuarios.constants import Role
from usuarios.schemas import UserDTO

# ``transaction.atomic()`` in the service requires a connection.
pytestmark = pytest.mark.django_db


# ---- Test doubles --------------------------------------------------------


class StubTipoService(TipoService):
    """Returns a fixed tipo and tracks how often ``snapshot`` was called."""

    def __init__(self, tipo: TipoSolicitudDTO) -> None:
        self._tipo = tipo
        self.snapshot_calls = 0
        self._snapshot_label: str = "live-label"

    def set_snapshot_label(self, label: str) -> None:
        self._snapshot_label = label

    def list_for_admin(self, **_: Any) -> list[TipoSolicitudRow]:
        return []

    def list_for_creator(self, role: Role) -> list[TipoSolicitudRow]:
        return []

    def get_for_admin(self, tipo_id: UUID) -> TipoSolicitudDTO:
        return self._tipo

    def get_for_creator(self, slug: str, role: Role) -> TipoSolicitudDTO:
        return self._tipo

    def create(self, *_: Any, **__: Any) -> TipoSolicitudDTO:  # pragma: no cover
        raise NotImplementedError

    def update(self, *_: Any, **__: Any) -> TipoSolicitudDTO:  # pragma: no cover
        raise NotImplementedError

    def deactivate(self, tipo_id: UUID) -> None:  # pragma: no cover
        raise NotImplementedError

    def snapshot(self, tipo_id: UUID) -> FormSnapshot:
        self.snapshot_calls += 1
        # Each call returns the *current* snapshot — used to prove the service
        # captures the snapshot at create-time, not earlier.
        return FormSnapshot(
            tipo_id=self._tipo.id,
            tipo_slug=self._tipo.slug,
            tipo_nombre=self._tipo.nombre,
            captured_at=datetime.now(tz=UTC),
            fields=[
                {
                    "field_id": uuid4(),
                    "label": self._snapshot_label,
                    "field_type": "TEXT",
                    "required": True,
                    "order": 0,
                }
            ],
        )


class _StubFolioService(FolioService):
    def __init__(self) -> None:
        self.calls = 0

    def next_folio(self, *, year: int) -> str:
        self.calls += 1
        return f"SOL-{year}-{self.calls:05d}"


class _NoopAutoFillResolver(AutoFillResolver):
    """Default test fake — no auto-fill fields, never raises."""

    def resolve(self, snapshot: Any, *, actor_matricula: str) -> dict[str, Any]:
        return {}

    def preview(self, snapshot: Any, *, actor_matricula: str) -> AutoFillPreview:
        return AutoFillPreview()


class _StubLifecycleService(LifecycleService):
    """Records ``transition`` calls; intake only uses this in ``cancel_own``."""

    def __init__(self, repo: SolicitudRepository) -> None:
        self._repo = repo
        self.transition_calls: list[tuple[str, TransitionInput, UserDTO]] = []

    def get_detail(self, folio: str) -> SolicitudDetail:
        return self._repo.get_by_folio(folio)

    def list_for_solicitante(
        self, matricula: str, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:  # pragma: no cover
        raise NotImplementedError

    def list_for_personal(
        self, role: Role, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:  # pragma: no cover
        raise NotImplementedError

    def transition(
        self, *, action: str, input_dto: TransitionInput, actor: UserDTO
    ) -> SolicitudDetail:
        self.transition_calls.append((action, input_dto, actor))
        # Return current detail so the view contract holds; the in-memory repo
        # was already mutated externally if the test wanted to.
        return self._repo.get_by_folio(input_dto.folio)

    # ---- aggregations: intake never invokes these; raise to surface misuse. ----

    def list_for_admin(
        self, *, page: PageRequest, filters: SolicitudFilter
    ) -> Page[SolicitudRow]:  # pragma: no cover
        raise NotImplementedError

    def iter_for_admin(  # pragma: no cover
        self, *, filters: SolicitudFilter, chunk_size: int = 500
    ):
        raise NotImplementedError

    def aggregate_by_estado(self, *, filters: SolicitudFilter):  # pragma: no cover
        raise NotImplementedError

    def aggregate_by_tipo(self, *, filters: SolicitudFilter):  # pragma: no cover
        raise NotImplementedError

    def aggregate_by_month(self, *, filters: SolicitudFilter):  # pragma: no cover
        raise NotImplementedError


# ---- Helpers -------------------------------------------------------------


def _tipo(
    *,
    requires_payment: bool = False,
    mentor_exempt: bool = False,
    activo: bool = True,
    creator_roles: set[Role] | None = None,
) -> TipoSolicitudDTO:
    return TipoSolicitudDTO(
        id=uuid4(),
        slug="constancia",
        nombre="Constancia",
        descripcion="",
        responsible_role=Role.CONTROL_ESCOLAR,
        creator_roles=creator_roles or {Role.ALUMNO},
        requires_payment=requires_payment,
        mentor_exempt=mentor_exempt,
        plantilla_id=None,
        activo=activo,
        fields=[
            FieldDefinitionDTO(
                id=uuid4(),
                label="Motivo",
                field_type="TEXT",
                required=True,
                order=0,
            ),
        ],
    )


def _service(
    tipo: TipoSolicitudDTO,
    *,
    auto_fill: AutoFillResolver | None = None,
) -> tuple[
    DefaultIntakeService,
    StubTipoService,
    InMemorySolicitudRepository,
    InMemoryHistorialRepository,
    RecordingNotificationService,
    _StubLifecycleService,
]:
    historial = InMemoryHistorialRepository()
    solicitudes = InMemorySolicitudRepository(historial=historial)
    tipos = StubTipoService(tipo)
    notifier = RecordingNotificationService()
    folios = _StubFolioService()
    lifecycle = _StubLifecycleService(solicitudes)
    svc = DefaultIntakeService(
        tipo_service=tipos,
        solicitud_repository=solicitudes,
        historial_repository=historial,
        folio_service=folios,
        lifecycle_service=lifecycle,
        notification_service=notifier,
        auto_fill_resolver=auto_fill or _NoopAutoFillResolver(),
    )
    return svc, tipos, solicitudes, historial, notifier, lifecycle


def _actor(matricula: str = "ALU-1", role: Role = Role.ALUMNO) -> UserDTO:
    return UserDTO(
        matricula=matricula, email=f"{matricula}@uaz.edu.mx", role=role
    )


# ---- create flow ---------------------------------------------------------


def test_create_persists_solicitud_with_creada_estado_and_folio() -> None:
    tipo = _tipo()
    svc, _, repo, _, _ , _ = _service(tipo)
    detail = svc.create(
        CreateSolicitudInput(
            tipo_id=tipo.id,
            solicitante_matricula="ALU-1",
            valores={"a": "b"},
            is_mentor_at_creation=False,
        ),
        actor=_actor(),
    )
    assert detail.estado is Estado.CREADA
    assert detail.folio.startswith("SOL-")
    # Round-trip through the repo proves persistence.
    assert repo.get_by_folio(detail.folio).valores == {"a": "b"}


def test_create_captures_snapshot_at_create_time_not_earlier() -> None:
    """If the admin edits the tipo between form-render and submit, the
    persisted snapshot reflects the *submit-time* state of the tipo."""
    tipo = _tipo()
    svc, tipos, repo, _, _, _ = _service(tipo)

    # GET phase: view calls get_intake_form, which captures a snapshot under
    # the *original* label.
    svc.get_intake_form(
        tipo.slug, role=Role.ALUMNO, is_mentor=False, actor_matricula="ALU-1"
    )
    assert tipos.snapshot_calls == 1

    # Admin renames the field between GET and POST.
    tipos.set_snapshot_label("submit-time")

    # POST phase: create must capture a fresh snapshot, not reuse the GET one.
    detail = svc.create(
        CreateSolicitudInput(
            tipo_id=tipo.id,
            solicitante_matricula="ALU-1",
            valores={},
            is_mentor_at_creation=False,
        ),
        actor=_actor(),
    )

    assert tipos.snapshot_calls == 2, (
        "create() must call snapshot fresh, not reuse the GET-time snapshot"
    )
    assert detail.form_snapshot.fields[0].label == "submit-time"
    # And the persisted row carries the same submit-time label.
    persisted = repo.get_by_folio(detail.folio)
    assert persisted.form_snapshot.fields[0].label == "submit-time"


# ---- pago_exento truth table --------------------------------------------


@pytest.mark.parametrize(
    ("requires_payment", "mentor_exempt", "is_mentor", "expected_exento"),
    [
        # Only the all-true row exempts.
        (True, True, True, True),
        # Any one false → not exempt.
        (True, True, False, False),
        (True, False, True, False),
        (False, True, True, False),
        # Combinations with multiple falses.
        (True, False, False, False),
        (False, True, False, False),
        (False, False, True, False),
        (False, False, False, False),
    ],
)
def test_pago_exento_truth_table(
    requires_payment: bool,
    mentor_exempt: bool,
    is_mentor: bool,
    expected_exento: bool,
) -> None:
    tipo = _tipo(requires_payment=requires_payment, mentor_exempt=mentor_exempt)
    svc, _, _, _, _ , _ = _service(tipo)
    detail = svc.create(
        CreateSolicitudInput(
            tipo_id=tipo.id,
            solicitante_matricula="ALU-1",
            valores={},
            is_mentor_at_creation=is_mentor,
        ),
        actor=_actor(),
    )
    assert detail.pago_exento is expected_exento
    # ``requiere_pago`` is always the tipo's flag, regardless of exemption.
    assert detail.requiere_pago is requires_payment


# ---- historial -----------------------------------------------------------


def test_create_writes_initial_historial_with_null_anterior() -> None:
    tipo = _tipo()
    svc, _, _, historial, _ , _ = _service(tipo)
    detail = svc.create(
        CreateSolicitudInput(
            tipo_id=tipo.id,
            solicitante_matricula="ALU-1",
            valores={},
            is_mentor_at_creation=False,
        ),
        actor=_actor(),
    )
    entries = historial.list_for_folio(detail.folio)
    assert len(entries) == 1
    assert entries[0].estado_anterior is None
    assert entries[0].estado_nuevo is Estado.CREADA
    # Actor's role is snapshotted on the row — used by reporting later.
    assert entries[0].actor_role is Role.ALUMNO


# ---- notifications ------------------------------------------------------


def test_create_notifies_with_tipos_responsible_role() -> None:
    tipo = _tipo()  # responsible_role=CONTROL_ESCOLAR by default
    svc, _, _, _, notifier , _ = _service(tipo)
    detail = svc.create(
        CreateSolicitudInput(
            tipo_id=tipo.id,
            solicitante_matricula="ALU-1",
            valores={},
            is_mentor_at_creation=False,
        ),
        actor=_actor(),
    )
    assert notifier.creations == [(detail.folio, Role.CONTROL_ESCOLAR)]


# ---- authorisation -------------------------------------------------------


def test_create_rejects_actor_role_outside_creator_roles() -> None:
    tipo = _tipo(creator_roles={Role.DOCENTE})  # ALUMNO not allowed
    svc, _, _, _, _ , _ = _service(tipo)
    with pytest.raises(CreatorRoleNotAllowed):
        svc.create(
            CreateSolicitudInput(
                tipo_id=tipo.id,
                solicitante_matricula="ALU-1",
                valores={},
                is_mentor_at_creation=False,
            ),
            actor=_actor(role=Role.ALUMNO),
        )


def test_create_rejects_inactive_tipo() -> None:
    tipo = _tipo(activo=False)
    svc, _, _, _, _ , _ = _service(tipo)
    with pytest.raises(CreatorRoleNotAllowed):
        svc.create(
            CreateSolicitudInput(
                tipo_id=tipo.id,
                solicitante_matricula="ALU-1",
                valores={},
                is_mentor_at_creation=False,
            ),
            actor=_actor(),
        )


# ---- cancel_own ----------------------------------------------------------


def test_cancel_own_delegates_to_lifecycle_with_cancelar_action() -> None:
    tipo = _tipo()
    svc, _, _, _, _, lifecycle = _service(tipo)
    detail = svc.create(
        CreateSolicitudInput(
            tipo_id=tipo.id,
            solicitante_matricula="ALU-1",
            valores={},
            is_mentor_at_creation=False,
        ),
        actor=_actor(),
    )

    svc.cancel_own(detail.folio, actor=_actor(), observaciones="ya no")
    assert len(lifecycle.transition_calls) == 1
    action, input_dto, actor = lifecycle.transition_calls[0]
    assert action == "cancelar"
    assert input_dto.folio == detail.folio
    assert input_dto.observaciones == "ya no"
    assert actor.matricula == "ALU-1"
