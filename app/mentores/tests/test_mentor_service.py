from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import pytest
from django.utils import timezone

from _shared.exceptions import DomainValidationError
from _shared.pagination import PageRequest
from mentores.constants import MentorSource
from mentores.exceptions import MentorAlreadyActive, MentorNotFound
from mentores.schemas import MentorPeriodoDTO
from mentores.services.mentor_service import DefaultMentorService
from mentores.tests.fakes import InMemoryMentorRepository
from usuarios.constants import Role
from usuarios.schemas import UserDTO


def make_user_dto_admin(matricula: str = "ADM1") -> UserDTO:
    return UserDTO(
        matricula=matricula, email=f"{matricula.lower()}@x.com", role=Role.ADMIN
    )


@pytest.fixture
def repo() -> InMemoryMentorRepository:
    return InMemoryMentorRepository()


@pytest.fixture
def service(repo: InMemoryMentorRepository) -> DefaultMentorService:
    return DefaultMentorService(
        mentor_repository=repo,
        logger=logging.getLogger("test.mentor_service"),
    )


# ---------------------------------------------------------------------------
# is_mentor / list
# ---------------------------------------------------------------------------

def test_is_mentor_true_for_open_period(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    repo._seed_active("12345678")
    assert service.is_mentor("12345678") is True


def test_is_mentor_false_for_unknown_matricula(
    service: DefaultMentorService,
) -> None:
    assert service.is_mentor("12345678") is False


def test_list_passes_through_to_repo(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    repo._seed_active("11111111")
    repo._seed_active("22222222")
    page = service.list(only_active=True, page=PageRequest(page=1, page_size=10))
    assert page.total == 2
    assert [m.matricula for m in page.items] == ["11111111", "22222222"]


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

def test_add_inserts_new_mentor(service: DefaultMentorService) -> None:
    actor = make_user_dto_admin()
    dto = service.add(
        matricula="12345678", fuente=MentorSource.MANUAL, nota="x", actor=actor
    )
    assert dto.matricula == "12345678"
    assert dto.fecha_baja is None


def test_add_rejects_invalid_matricula_format(service: DefaultMentorService) -> None:
    actor = make_user_dto_admin()
    with pytest.raises(DomainValidationError) as exc_info:
        service.add(
            matricula="abc", fuente=MentorSource.MANUAL, nota="", actor=actor
        )
    assert "matricula" in exc_info.value.field_errors


def test_add_raises_already_active_on_duplicate(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    actor = make_user_dto_admin()
    repo._seed_active("12345678")
    with pytest.raises(MentorAlreadyActive):
        service.add(
            matricula="12345678", fuente=MentorSource.MANUAL, nota="", actor=actor
        )


def test_add_after_deactivation_opens_new_period(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    """Reactivation through ``add`` opens a new period; previous one stays closed."""
    actor = make_user_dto_admin()
    closed = MentorPeriodoDTO(
        id=1,
        matricula="12345678",
        fuente=MentorSource.CSV,
        nota="",
        fecha_alta=datetime(2025, 1, 1, tzinfo=UTC),
        fecha_baja=datetime(2025, 6, 1, tzinfo=UTC),
        creado_por_matricula="ADM1",
        desactivado_por_matricula="ADM1",
    )
    repo._seed(closed)
    dto = service.add(
        matricula="12345678", fuente=MentorSource.MANUAL, nota="back", actor=actor
    )
    assert dto.fecha_baja is None
    assert dto.id != closed.id  # New period, not in-place reactivation.
    history = service.get_history("12345678")
    assert len(history) == 2


def test_add_recovers_from_concurrent_reactivation_race(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    """If a concurrent admin opens the period first, we surface
    ``MentorAlreadyActive`` (not 500) — the repo's ``IntegrityError`` recovery
    converts the race into ``ALREADY_ACTIVE``."""
    actor = make_user_dto_admin()
    closed = MentorPeriodoDTO(
        id=1,
        matricula="12345678",
        fuente=MentorSource.CSV,
        nota="",
        fecha_alta=datetime(2025, 1, 1, tzinfo=UTC),
        fecha_baja=datetime(2025, 6, 1, tzinfo=UTC),
        creado_por_matricula="ADM1",
        desactivado_por_matricula="ADM1",
    )
    repo._seed(closed)
    # Arm the fake to simulate a concurrent reactivator winning the partial-
    # unique-index race. The fake will raise IntegrityError after the active
    # check succeeds, then recover by treating the simulated winner as the
    # current active period.
    winner = MentorPeriodoDTO(
        id=2,
        matricula="12345678",
        fuente=MentorSource.MANUAL,
        nota="",
        fecha_alta=timezone.now(),
        fecha_baja=None,
        creado_por_matricula="ADM2",
        desactivado_por_matricula=None,
    )
    repo._arm_integrity_error(winner)
    with pytest.raises(MentorAlreadyActive):
        service.add(
            matricula="12345678",
            fuente=MentorSource.MANUAL,
            nota="",
            actor=actor,
        )


# ---------------------------------------------------------------------------
# deactivate
# ---------------------------------------------------------------------------

def test_deactivate_closes_open_period(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    actor = make_user_dto_admin("ADM2")
    repo._seed_active("12345678")
    dto = service.deactivate("12345678", actor)
    assert dto.fecha_baja is not None
    assert dto.desactivado_por_matricula == "ADM2"


def test_deactivate_raises_when_no_open_period(
    service: DefaultMentorService,
) -> None:
    actor = make_user_dto_admin()
    with pytest.raises(MentorNotFound):
        service.deactivate("99999999", actor)


# ---------------------------------------------------------------------------
# get_history / was_mentor_at — service-level passthroughs
# ---------------------------------------------------------------------------

def test_get_history_returns_periods_newest_first(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    older = MentorPeriodoDTO(
        id=1,
        matricula="M1",
        fuente=MentorSource.MANUAL,
        nota="",
        fecha_alta=datetime(2024, 1, 1, tzinfo=UTC),
        fecha_baja=datetime(2024, 6, 1, tzinfo=UTC),
        creado_por_matricula="ADM1",
    )
    newer = MentorPeriodoDTO(
        id=2,
        matricula="M1",
        fuente=MentorSource.CSV,
        nota="",
        fecha_alta=datetime(2024, 9, 1, tzinfo=UTC),
        fecha_baja=None,
        creado_por_matricula="ADM1",
    )
    repo._seed(older)
    repo._seed(newer)
    history = service.get_history("M1")
    assert [p.id for p in history] == [newer.id, older.id]


def test_get_history_empty_for_unknown_matricula(
    service: DefaultMentorService,
) -> None:
    assert service.get_history("99999999") == []


def test_was_mentor_at_passthrough(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    alta = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)
    baja = datetime(2024, 6, 1, 9, 0, tzinfo=UTC)
    repo._seed(
        MentorPeriodoDTO(
            id=1,
            matricula="M1",
            fuente=MentorSource.MANUAL,
            nota="",
            fecha_alta=alta,
            fecha_baja=baja,
            creado_por_matricula="ADM1",
        )
    )
    assert service.was_mentor_at("M1", alta) is True
    assert service.was_mentor_at("M1", baja - timedelta(microseconds=1)) is True
    assert service.was_mentor_at("M1", baja) is False


# ---------------------------------------------------------------------------
# Bulk deactivation
# ---------------------------------------------------------------------------

def test_bulk_deactivate_assembles_counts(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    actor = make_user_dto_admin("ADMX")
    repo._seed_active("A1")
    repo._seed_active("A2")
    # A3: already closed.
    repo._seed(
        MentorPeriodoDTO(
            id=99,
            matricula="A3",
            fuente=MentorSource.MANUAL,
            nota="",
            fecha_alta=datetime(2024, 1, 1, tzinfo=UTC),
            fecha_baja=datetime(2024, 6, 1, tzinfo=UTC),
            creado_por_matricula="ADM1",
        )
    )

    result = service.bulk_deactivate(["A1", "A2", "A3", "UNKNOWN"], actor)
    assert result.total_attempted == 4
    assert result.closed == 2  # A1 + A2
    assert result.already_inactive == 2  # A3 (closed) + UNKNOWN

    # A1 and A2 are now closed with the actor stamp.
    assert repo._active_for("A1") is None
    assert repo._active_for("A2") is None


def test_bulk_deactivate_empty_input(service: DefaultMentorService) -> None:
    actor = make_user_dto_admin()
    result = service.bulk_deactivate([], actor)
    assert result.total_attempted == 0
    assert result.closed == 0
    assert result.already_inactive == 0


def test_bulk_deactivate_dedupes_input_before_counting(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    """Duplicate matrículas in input must NOT inflate already_inactive."""
    actor = make_user_dto_admin()
    repo._seed_active("A1")
    # Admin somehow submits the same matrícula three times; expect total=1, closed=1.
    result = service.bulk_deactivate(["A1", "A1", "A1"], actor)
    assert result.total_attempted == 1
    assert result.closed == 1
    assert result.already_inactive == 0


def test_deactivate_all_active_closes_open_only(
    service: DefaultMentorService, repo: InMemoryMentorRepository
) -> None:
    actor = make_user_dto_admin()
    repo._seed_active("A1")
    repo._seed_active("A2")
    repo._seed(
        MentorPeriodoDTO(
            id=99,
            matricula="A3",
            fuente=MentorSource.MANUAL,
            nota="",
            fecha_alta=datetime(2024, 1, 1, tzinfo=UTC),
            fecha_baja=datetime(2024, 6, 1, tzinfo=UTC),
            creado_por_matricula="ADM1",
        )
    )
    result = service.deactivate_all_active(actor)
    assert result.total_attempted == 2
    assert result.closed == 2
    assert result.already_inactive == 0
    assert repo._active_for("A1") is None
    assert repo._active_for("A2") is None
