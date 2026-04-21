"""Tests for DefaultLifecycleService — state machine + authorization."""
from __future__ import annotations

from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from _shared.exceptions import Unauthorized
from solicitudes.lifecycle.constants import (
    ACTION_ATENDER,
    ACTION_CANCELAR,
    ACTION_FINALIZAR,
    TRANSITIONS,
    Estado,
)
from solicitudes.lifecycle.exceptions import (
    InvalidStateTransition,
    SolicitudNotFound,
)
from solicitudes.lifecycle.schemas import TransitionInput
from solicitudes.lifecycle.services.lifecycle_service.implementation import (
    DefaultLifecycleService,
)
from solicitudes.lifecycle.tests.fakes import (
    InMemoryHistorialRepository,
    InMemorySolicitudRepository,
    RecordingNotificationService,
    empty_form_snapshot,
)
from solicitudes.tipos.schemas import TipoSolicitudRow
from usuarios.constants import Role
from usuarios.schemas import UserDTO

# `transaction.atomic()` in the service requires a connection, even when the
# repositories are in-memory. Mark the whole module with django_db so pytest
# sets one up.
pytestmark = pytest.mark.django_db


def _service(
    *,
    notifier: RecordingNotificationService | None = None,
) -> tuple[
    DefaultLifecycleService,
    InMemorySolicitudRepository,
    InMemoryHistorialRepository,
    RecordingNotificationService,
]:
    historial = InMemoryHistorialRepository()
    solicitudes = InMemorySolicitudRepository(historial=historial)
    notifier = notifier or RecordingNotificationService()
    svc = DefaultLifecycleService(
        solicitud_repository=solicitudes,
        historial_repository=historial,
        notification_service=notifier,
    )
    return svc, solicitudes, historial, notifier


def _seed(
    repo: InMemorySolicitudRepository,
    *,
    folio: str = "SOL-2026-00001",
    estado: Estado = Estado.CREADA,
    responsible_role: Role = Role.CONTROL_ESCOLAR,
    solicitante: str = "ALU-1",
) -> str:
    tipo_id = uuid4()
    detail = repo.create(
        folio=folio,
        tipo_id=tipo_id,
        solicitante_matricula=solicitante,
        estado=estado,
        form_snapshot=empty_form_snapshot(tipo_id),
        valores={},
        requiere_pago=False,
        pago_exento=False,
    )
    # Override the seeded responsible_role on the cached row.
    repo.seed(
        detail.model_copy(
            update={
                "tipo": TipoSolicitudRow(
                    id=detail.tipo.id,
                    slug=detail.tipo.slug,
                    nombre=detail.tipo.nombre,
                    responsible_role=responsible_role,
                    creator_roles=detail.tipo.creator_roles,
                    requires_payment=detail.tipo.requires_payment,
                    activo=True,
                )
            }
        )
    )
    return folio


def _actor(matricula: str = "OP-1", role: Role = Role.CONTROL_ESCOLAR) -> UserDTO:
    return UserDTO(matricula=matricula, email=f"{matricula}@uaz.edu.mx", role=role)


# ---- transitions ----


def test_atender_moves_creada_to_en_proceso() -> None:
    svc, repo, historial, notifier = _service()
    folio = _seed(repo)
    detail = svc.transition(
        action=ACTION_ATENDER,
        input_dto=TransitionInput(folio=folio, actor_matricula="OP-1"),
        actor=_actor(),
    )
    assert detail.estado is Estado.EN_PROCESO
    assert len(historial.list_for_folio(folio)) == 1
    assert notifier.transitions == [(folio, Estado.EN_PROCESO, "")]


def test_finalizar_moves_en_proceso_to_finalizada() -> None:
    svc, repo, _, _ = _service()
    folio = _seed(repo, estado=Estado.EN_PROCESO)
    detail = svc.transition(
        action=ACTION_FINALIZAR,
        input_dto=TransitionInput(folio=folio, actor_matricula="OP-1"),
        actor=_actor(),
    )
    assert detail.estado is Estado.FINALIZADA


def test_finalizar_from_creada_raises_invalid_transition() -> None:
    svc, repo, _, _ = _service()
    folio = _seed(repo)
    with pytest.raises(InvalidStateTransition):
        svc.transition(
            action=ACTION_FINALIZAR,
            input_dto=TransitionInput(folio=folio, actor_matricula="OP-1"),
            actor=_actor(),
        )


def test_cancelar_from_finalizada_raises_invalid_transition() -> None:
    svc, repo, _, _ = _service()
    folio = _seed(repo, estado=Estado.FINALIZADA)
    with pytest.raises(InvalidStateTransition):
        svc.transition(
            action=ACTION_CANCELAR,
            input_dto=TransitionInput(folio=folio, actor_matricula="OP-1"),
            actor=_actor(role=Role.ADMIN),
        )


def test_solicitante_can_cancel_only_from_creada() -> None:
    svc, repo, _, _ = _service()
    folio = _seed(repo)
    detail = svc.transition(
        action=ACTION_CANCELAR,
        input_dto=TransitionInput(folio=folio, actor_matricula="ALU-1"),
        actor=_actor(matricula="ALU-1", role=Role.ALUMNO),
    )
    assert detail.estado is Estado.CANCELADA


def test_solicitante_cannot_cancel_from_en_proceso() -> None:
    svc, repo, _, _ = _service()
    folio = _seed(repo, estado=Estado.EN_PROCESO)
    with pytest.raises(Unauthorized):
        svc.transition(
            action=ACTION_CANCELAR,
            input_dto=TransitionInput(folio=folio, actor_matricula="ALU-1"),
            actor=_actor(matricula="ALU-1", role=Role.ALUMNO),
        )


def test_responsible_role_can_cancel_en_proceso() -> None:
    svc, repo, _, _ = _service()
    folio = _seed(repo, estado=Estado.EN_PROCESO)
    detail = svc.transition(
        action=ACTION_CANCELAR,
        input_dto=TransitionInput(folio=folio, actor_matricula="OP-1"),
        actor=_actor(),
    )
    assert detail.estado is Estado.CANCELADA


def test_admin_can_cancel_creada_or_en_proceso() -> None:
    svc, repo, _, _ = _service()
    folio = _seed(repo, estado=Estado.EN_PROCESO)
    detail = svc.transition(
        action=ACTION_CANCELAR,
        input_dto=TransitionInput(folio=folio, actor_matricula="ADM-1"),
        actor=_actor(matricula="ADM-1", role=Role.ADMIN),
    )
    assert detail.estado is Estado.CANCELADA


def test_atender_unauthorized_when_role_mismatch() -> None:
    svc, repo, _, _ = _service()
    folio = _seed(repo, responsible_role=Role.CONTROL_ESCOLAR)
    with pytest.raises(Unauthorized):
        svc.transition(
            action=ACTION_ATENDER,
            input_dto=TransitionInput(folio=folio, actor_matricula="DOC-1"),
            actor=_actor(matricula="DOC-1", role=Role.DOCENTE),
        )


def test_transition_on_missing_folio_raises_not_found() -> None:
    svc, _, _, _ = _service()
    with pytest.raises(SolicitudNotFound):
        svc.transition(
            action=ACTION_ATENDER,
            input_dto=TransitionInput(folio="SOL-2026-99999", actor_matricula="OP-1"),
            actor=_actor(),
        )


# ---- listing ----


def test_admin_list_returns_all() -> None:
    svc, repo, _, _ = _service()
    _seed(repo, folio="SOL-2026-00001")
    _seed(repo, folio="SOL-2026-00002", responsible_role=Role.RESPONSABLE_PROGRAMA)
    from _shared.pagination import PageRequest
    from solicitudes.lifecycle.schemas import SolicitudFilter

    page = svc.list_for_personal(
        Role.ADMIN, page=PageRequest(), filters=SolicitudFilter()
    )
    assert page.total == 2


def test_personal_list_scopes_to_role() -> None:
    svc, repo, _, _ = _service()
    _seed(repo, folio="SOL-2026-00001", responsible_role=Role.CONTROL_ESCOLAR)
    _seed(repo, folio="SOL-2026-00002", responsible_role=Role.RESPONSABLE_PROGRAMA)
    from _shared.pagination import PageRequest
    from solicitudes.lifecycle.schemas import SolicitudFilter

    page = svc.list_for_personal(
        Role.CONTROL_ESCOLAR, page=PageRequest(), filters=SolicitudFilter()
    )
    assert page.total == 1


# ---- property test on the state machine matrix ----


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    estado=st.sampled_from(list(Estado)),
    action=st.sampled_from([ACTION_ATENDER, ACTION_FINALIZAR, ACTION_CANCELAR]),
)
def test_transitions_map_is_complete_and_disallowed_pairs_raise(
    estado: Estado, action: str
) -> None:
    """Every (estado, action) pair is either in TRANSITIONS or not allowed.

    The service's ``transition`` raises ``InvalidStateTransition`` for any
    pair not in the map. This test invokes the service through admin (which
    skips authorization) so we are testing the matrix, not auth.
    """
    svc, repo, _, _ = _service()
    folio = "SOL-2026-AUX"
    repo._rows.clear()
    _seed(repo, folio=folio, estado=estado)
    actor = _actor(role=Role.ADMIN)

    if (estado, action) in TRANSITIONS:
        detail = svc.transition(
            action=action,
            input_dto=TransitionInput(folio=folio, actor_matricula="ADM-1"),
            actor=actor,
        )
        assert detail.estado is TRANSITIONS[(estado, action)]
    else:
        with pytest.raises(InvalidStateTransition):
            svc.transition(
                action=action,
                input_dto=TransitionInput(folio=folio, actor_matricula="ADM-1"),
                actor=actor,
            )
