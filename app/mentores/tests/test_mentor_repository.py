from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from _shared.pagination import PageRequest
from mentores.constants import MentorSource
from mentores.exceptions import MentorNotFound
from mentores.models import MentorPeriodo
from mentores.repositories.mentor import OrmMentorRepository, UpsertOutcome
from mentores.schemas import MentorUpsertInput
from mentores.tests.factories import make_admin_user, make_mentor_periodo


@pytest.fixture
def repo() -> OrmMentorRepository:
    return OrmMentorRepository()


# ---------------------------------------------------------------------------
# exists_active / get_active_period
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_exists_active_true_for_open_period(repo: OrmMentorRepository) -> None:
    make_mentor_periodo(matricula="12345678", fecha_baja=None)
    assert repo.exists_active("12345678") is True


@pytest.mark.django_db
def test_exists_active_false_when_only_closed_periods_exist(
    repo: OrmMentorRepository,
) -> None:
    make_mentor_periodo(matricula="12345678", fecha_baja=timezone.now())
    assert repo.exists_active("12345678") is False


@pytest.mark.django_db
def test_exists_active_false_for_unknown_matricula(repo: OrmMentorRepository) -> None:
    assert repo.exists_active("99999999") is False


@pytest.mark.django_db
def test_get_active_period_returns_dto(repo: OrmMentorRepository) -> None:
    make_mentor_periodo(matricula="12345678")
    dto = repo.get_active_period("12345678")
    assert dto.matricula == "12345678"
    assert dto.fecha_baja is None


@pytest.mark.django_db
def test_get_active_period_raises_when_no_open_period(
    repo: OrmMentorRepository,
) -> None:
    make_mentor_periodo(matricula="12345678", fecha_baja=timezone.now())
    with pytest.raises(MentorNotFound):
        repo.get_active_period("12345678")


# ---------------------------------------------------------------------------
# add_or_reactivate
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_add_or_reactivate_inserts_when_no_history(repo: OrmMentorRepository) -> None:
    admin = make_admin_user(matricula="ADM1")
    dto, outcome = repo.add_or_reactivate(
        MentorUpsertInput(
            matricula="12345678",
            fuente=MentorSource.MANUAL,
            nota="Mentor de programa X",
            creado_por_matricula=admin.matricula,
        )
    )
    assert outcome is UpsertOutcome.INSERTED
    assert dto.matricula == "12345678"
    assert dto.fecha_baja is None
    assert dto.creado_por_matricula == admin.matricula
    assert dto.nota == "Mentor de programa X"
    assert MentorPeriodo.objects.count() == 1


@pytest.mark.django_db
def test_add_or_reactivate_returns_already_active_when_open_period_exists(
    repo: OrmMentorRepository,
) -> None:
    admin = make_admin_user(matricula="ADM1")
    existing = make_mentor_periodo(
        matricula="12345678", fuente=MentorSource.MANUAL.value, creado_por=admin
    )
    dto, outcome = repo.add_or_reactivate(
        MentorUpsertInput(
            matricula="12345678",
            fuente=MentorSource.CSV,
            creado_por_matricula=admin.matricula,
        )
    )
    assert outcome is UpsertOutcome.ALREADY_ACTIVE
    assert dto.id == existing.pk  # No new row, no overwrite.
    assert dto.fuente is MentorSource.MANUAL  # Source unchanged.
    assert MentorPeriodo.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_add_or_reactivate_recovers_from_concurrent_integrity_error(
    repo: OrmMentorRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Genuine race: a concurrent admin opens a period between our
    ``filter().first()`` check and our ``create()``. The partial unique index
    rejects our insert with ``IntegrityError`` — the recovery branch must
    re-read the now-active row and return ``ALREADY_ACTIVE`` instead of
    surfacing a 500.

    Simulated by patching ``MentorPeriodo.objects.create`` to (a) insert
    the simulated winner directly, then (b) raise ``IntegrityError`` once.
    The recovery branch then re-reads the row the "concurrent admin" wrote.
    """
    admin = make_admin_user(matricula="ADM1")
    other_admin = make_admin_user(matricula="ADM2", email="adm2@x.mx")
    # Pre-condition: a closed period (so `had_history` is True).
    make_mentor_periodo(
        matricula="12345678",
        creado_por=admin,
        fecha_baja=timezone.now(),
    )

    real_create = MentorPeriodo.objects.create
    call_count = {"n": 0}

    def fake_create(**kwargs: Any) -> MentorPeriodo:
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Simulate the concurrent winner: insert a real open period
            # for the same matrícula via direct SQL bypass of our queryset.
            MentorPeriodo._base_manager.create(
                matricula=kwargs["matricula"],
                fuente=kwargs["fuente"],
                nota=kwargs["nota"],
                fecha_alta=timezone.now(),
                creado_por_id=other_admin.matricula,
            )
            raise IntegrityError("simulated partial unique index race")
        return real_create(**kwargs)

    monkeypatch.setattr(MentorPeriodo.objects, "create", fake_create)

    dto, outcome = repo.add_or_reactivate(
        MentorUpsertInput(
            matricula="12345678",
            fuente=MentorSource.MANUAL,
            nota="losing-attempt",
            creado_por_matricula=admin.matricula,
        )
    )
    # Recovery path must surface ALREADY_ACTIVE (no 500 leaks).
    assert outcome is UpsertOutcome.ALREADY_ACTIVE
    # The DTO returned reflects the concurrent winner, not our attempt.
    assert dto.creado_por_matricula == other_admin.matricula
    assert dto.fecha_baja is None
    # Exactly one open period exists; the partial unique index held.
    open_count = MentorPeriodo.objects.filter(
        matricula="12345678", fecha_baja__isnull=True
    ).count()
    assert open_count == 1


@pytest.mark.django_db
def test_add_or_reactivate_opens_new_period_after_deactivation(
    repo: OrmMentorRepository,
) -> None:
    admin = make_admin_user(matricula="ADM1")
    closed = make_mentor_periodo(
        matricula="12345678",
        fuente=MentorSource.MANUAL.value,
        fecha_baja=timezone.now(),
        creado_por=admin,
    )
    dto, outcome = repo.add_or_reactivate(
        MentorUpsertInput(
            matricula="12345678",
            fuente=MentorSource.CSV,
            nota="reimport",
            creado_por_matricula=admin.matricula,
        )
    )
    assert outcome is UpsertOutcome.REACTIVATED
    assert dto.id != closed.pk
    assert dto.fecha_baja is None
    assert dto.fuente is MentorSource.CSV
    assert dto.nota == "reimport"
    assert MentorPeriodo.objects.filter(matricula="12345678").count() == 2


# ---------------------------------------------------------------------------
# Partial unique index — DB-level enforcement
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_partial_unique_index_blocks_two_open_periods() -> None:
    """The partial unique index must reject a second open period at the DB level."""
    admin = make_admin_user(matricula="ADM1")
    make_mentor_periodo(matricula="12345678", creado_por=admin)
    with pytest.raises(IntegrityError), transaction.atomic():
        MentorPeriodo.objects.create(
            matricula="12345678",
            fuente=MentorSource.MANUAL.value,
            nota="",
            fecha_alta=timezone.now(),
            creado_por_id=admin.matricula,
        )


@pytest.mark.django_db(transaction=True)
def test_partial_unique_index_allows_multiple_closed_periods() -> None:
    """Closed periods (fecha_baja != NULL) are not constrained by the index."""
    admin = make_admin_user(matricula="ADM1")
    now = timezone.now()
    for i in range(3):
        make_mentor_periodo(
            matricula="12345678",
            creado_por=admin,
            fecha_alta=now - timedelta(days=10 * (i + 1)),
            fecha_baja=now - timedelta(days=10 * i + 1),
        )
    assert MentorPeriodo.objects.filter(matricula="12345678").count() == 3


# ---------------------------------------------------------------------------
# deactivate
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_deactivate_closes_open_period(repo: OrmMentorRepository) -> None:
    admin = make_admin_user(matricula="ADM1")
    make_mentor_periodo(matricula="12345678", creado_por=admin)
    dto = repo.deactivate("12345678", actor_matricula=admin.matricula)
    assert dto.fecha_baja is not None
    assert dto.desactivado_por_matricula == admin.matricula
    persisted = MentorPeriodo.objects.get(matricula="12345678")
    assert persisted.fecha_baja is not None
    assert persisted.desactivado_por_id == admin.matricula


@pytest.mark.django_db
def test_deactivate_raises_when_no_open_period(repo: OrmMentorRepository) -> None:
    admin = make_admin_user(matricula="ADM1")
    make_mentor_periodo(
        matricula="12345678", fecha_baja=timezone.now(), creado_por=admin
    )
    with pytest.raises(MentorNotFound):
        repo.deactivate("12345678", actor_matricula=admin.matricula)


@pytest.mark.django_db
def test_deactivate_raises_when_unknown_matricula(repo: OrmMentorRepository) -> None:
    admin = make_admin_user(matricula="ADM1")
    with pytest.raises(MentorNotFound):
        repo.deactivate("99999999", actor_matricula=admin.matricula)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_only_active_excludes_closed_periods(repo: OrmMentorRepository) -> None:
    make_mentor_periodo(matricula="A1")
    make_mentor_periodo(matricula="A2", fecha_baja=timezone.now())
    make_mentor_periodo(matricula="A3")
    page = repo.list(only_active=True, page=PageRequest(page=1, page_size=10))
    assert [m.matricula for m in page.items] == ["A1", "A3"]
    assert page.total == 2


@pytest.mark.django_db
def test_list_all_returns_one_row_per_matricula_via_distinct_on(
    repo: OrmMentorRepository,
) -> None:
    """``only_active=False`` should collapse history to one row per matrícula
    (the most-recent period via Postgres ``DISTINCT ON``)."""
    admin = make_admin_user(matricula="ADM1")
    now = timezone.now()
    # Three periods for A1: oldest closed, middle closed, latest open.
    make_mentor_periodo(
        matricula="A1",
        creado_por=admin,
        fecha_alta=now - timedelta(days=30),
        fecha_baja=now - timedelta(days=20),
    )
    make_mentor_periodo(
        matricula="A1",
        creado_por=admin,
        fecha_alta=now - timedelta(days=15),
        fecha_baja=now - timedelta(days=5),
    )
    latest_a1 = make_mentor_periodo(
        matricula="A1",
        creado_por=admin,
        fecha_alta=now - timedelta(hours=1),
    )
    # One closed-only matrícula.
    make_mentor_periodo(
        matricula="A2",
        creado_por=admin,
        fecha_alta=now - timedelta(days=2),
        fecha_baja=now - timedelta(hours=2),
    )
    page = repo.list(only_active=False, page=PageRequest(page=1, page_size=10))
    assert page.total == 2
    assert sorted(m.matricula for m in page.items) == ["A1", "A2"]
    a1_row = next(m for m in page.items if m.matricula == "A1")
    assert a1_row.id == latest_a1.pk  # Most recent period wins.


@pytest.mark.django_db
def test_list_pagination_only_active(repo: OrmMentorRepository) -> None:
    for i in range(5):
        make_mentor_periodo(matricula=f"A{i}")
    page1 = repo.list(only_active=True, page=PageRequest(page=1, page_size=2))
    assert [m.matricula for m in page1.items] == ["A0", "A1"]
    assert page1.total == 5
    assert page1.has_next is True
    page3 = repo.list(only_active=True, page=PageRequest(page=3, page_size=2))
    assert [m.matricula for m in page3.items] == ["A4"]
    assert page3.has_next is False


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_history_returns_periods_newest_first(repo: OrmMentorRepository) -> None:
    admin = make_admin_user(matricula="ADM1")
    now = timezone.now()
    older = make_mentor_periodo(
        matricula="12345678",
        creado_por=admin,
        fecha_alta=now - timedelta(days=10),
        fecha_baja=now - timedelta(days=5),
    )
    newer = make_mentor_periodo(
        matricula="12345678",
        creado_por=admin,
        fecha_alta=now - timedelta(hours=1),
    )
    history = repo.get_history("12345678")
    assert [p.id for p in history] == [newer.pk, older.pk]


@pytest.mark.django_db
def test_get_history_empty_for_unknown_matricula(repo: OrmMentorRepository) -> None:
    assert repo.get_history("99999999") == []


# ---------------------------------------------------------------------------
# was_mentor_at — half-open ``[fecha_alta, fecha_baja)`` boundary semantics
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_was_mentor_at_inclusive_alta_exclusive_baja(repo: OrmMentorRepository) -> None:
    admin = make_admin_user(matricula="ADM1")
    alta = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)
    baja = datetime(2024, 6, 1, 9, 0, tzinfo=UTC)
    make_mentor_periodo(
        matricula="M1", creado_por=admin, fecha_alta=alta, fecha_baja=baja
    )
    # Inclusive on alta:
    assert repo.was_mentor_at("M1", alta) is True
    # 1 microsecond before baja: still in the period.
    assert repo.was_mentor_at("M1", baja - timedelta(microseconds=1)) is True
    # Exclusive on baja:
    assert repo.was_mentor_at("M1", baja) is False


@pytest.mark.django_db
def test_was_mentor_at_open_period_extends_to_infinity(
    repo: OrmMentorRepository,
) -> None:
    admin = make_admin_user(matricula="ADM1")
    alta = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    make_mentor_periodo(matricula="M1", creado_por=admin, fecha_alta=alta)
    far_future = datetime(2099, 1, 1, 0, 0, tzinfo=UTC)
    assert repo.was_mentor_at("M1", far_future) is True


@pytest.mark.django_db
def test_was_mentor_at_handles_gaps_between_periods(
    repo: OrmMentorRepository,
) -> None:
    admin = make_admin_user(matricula="ADM1")
    p1_alta = datetime(2024, 1, 1, tzinfo=UTC)
    p1_baja = datetime(2024, 6, 1, tzinfo=UTC)
    p2_alta = datetime(2024, 9, 1, tzinfo=UTC)
    make_mentor_periodo(
        matricula="M1", creado_por=admin, fecha_alta=p1_alta, fecha_baja=p1_baja
    )
    make_mentor_periodo(matricula="M1", creado_por=admin, fecha_alta=p2_alta)
    # In the gap (Aug 15):
    assert (
        repo.was_mentor_at("M1", datetime(2024, 8, 15, tzinfo=UTC)) is False
    )
    # After reactivation (Dec 15):
    assert (
        repo.was_mentor_at("M1", datetime(2024, 12, 15, tzinfo=UTC)) is True
    )


@pytest.mark.django_db
def test_was_mentor_at_false_before_first_alta(repo: OrmMentorRepository) -> None:
    admin = make_admin_user(matricula="ADM1")
    alta = datetime(2024, 6, 1, tzinfo=UTC)
    make_mentor_periodo(matricula="M1", creado_por=admin, fecha_alta=alta)
    assert (
        repo.was_mentor_at("M1", datetime(2024, 1, 1, tzinfo=UTC)) is False
    )


# ---------------------------------------------------------------------------
# Bulk deactivation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_deactivate_many_closes_only_open_periods_in_input(
    repo: OrmMentorRepository,
) -> None:
    admin = make_admin_user(matricula="ADM1")
    make_mentor_periodo(matricula="A1", creado_por=admin)  # open, in input
    make_mentor_periodo(matricula="A2", creado_por=admin)  # open, in input
    # Already closed — must be skipped.
    make_mentor_periodo(
        matricula="A3", creado_por=admin, fecha_baja=timezone.now()
    )
    make_mentor_periodo(matricula="A4", creado_por=admin)  # open, NOT in input

    closed = repo.deactivate_many(
        ["A1", "A2", "A3", "A99"], actor_matricula=admin.matricula
    )
    assert closed == 2  # A1 + A2; A3 already closed; A99 doesn't exist

    a1 = MentorPeriodo.objects.get(matricula="A1")
    assert a1.fecha_baja is not None
    assert a1.desactivado_por_id == admin.matricula
    a2 = MentorPeriodo.objects.get(matricula="A2")
    assert a2.fecha_baja is not None
    a4 = MentorPeriodo.objects.get(matricula="A4")
    assert a4.fecha_baja is None
    assert a4.desactivado_por_id is None


@pytest.mark.django_db
def test_deactivate_many_with_empty_input_returns_zero(
    repo: OrmMentorRepository,
) -> None:
    admin = make_admin_user(matricula="ADM1")
    make_mentor_periodo(matricula="A1", creado_por=admin)
    closed = repo.deactivate_many([], actor_matricula=admin.matricula)
    assert closed == 0
    assert MentorPeriodo.objects.get(matricula="A1").fecha_baja is None


@pytest.mark.django_db
def test_deactivate_all_active_closes_every_open_period(
    repo: OrmMentorRepository,
) -> None:
    admin = make_admin_user(matricula="ADM1")
    make_mentor_periodo(matricula="A1", creado_por=admin)
    make_mentor_periodo(matricula="A2", creado_por=admin)
    closed_marker = timezone.now() - timedelta(days=10)
    closed_existing = make_mentor_periodo(
        matricula="A3", creado_por=admin, fecha_baja=closed_marker
    )

    closed = repo.deactivate_all_active(actor_matricula=admin.matricula)
    assert closed == 2

    assert MentorPeriodo.objects.get(matricula="A1").fecha_baja is not None
    assert MentorPeriodo.objects.get(matricula="A2").fecha_baja is not None
    # Pre-existing closed period left untouched.
    a3 = MentorPeriodo.objects.get(matricula="A3")
    assert a3.fecha_baja == closed_existing.fecha_baja
    assert a3.desactivado_por_id is None


@pytest.mark.django_db
def test_deactivate_all_active_on_empty_catalog_is_zero(
    repo: OrmMentorRepository,
) -> None:
    admin = make_admin_user(matricula="ADM1")
    closed = repo.deactivate_all_active(actor_matricula=admin.matricula)
    assert closed == 0
