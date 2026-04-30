"""Regression tests for the ``0003_backfill_mentor_periodos`` data migration.

Two acceptance criteria from `plan.md`:

1. Empty source ``Mentor`` table → migration runs as a no-op without error.
2. Populated source ``Mentor`` table → every row is carried into
   ``MentorPeriodo`` with **`fecha_alta` preserved verbatim** — this is the
   regression guard for the "Critical fix #1" described in the plan's
   changelog (the ``auto_now_add`` footgun that would silently overwrite
   historical alta timestamps during ``bulk_create``).

The tests use Django's :class:`MigrationExecutor` to roll the schema back
to the pre-historicization state (`0001_initial`), seed the legacy
``Mentor`` table, then roll forward through `0002` → `0003` and assert
the resulting ``MentorPeriodo`` rows match the seeded data.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from django.apps.registry import Apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


def _historical_apps_at(state: tuple[str, str]) -> Apps:
    """Return an ``apps`` registry reflecting model state at ``state``."""
    executor = MigrationExecutor(connection)
    return executor.loader.project_state(state).apps


@pytest.fixture
def reset_to_pre_historicization() -> Iterator[None]:
    """Roll mentores back to ``0001_initial`` for the test, then forward to
    HEAD on teardown so subsequent tests see the full schema."""
    executor = MigrationExecutor(connection)
    executor.migrate([("mentores", "0001_initial")])
    yield
    # Teardown: re-apply through the latest migration so the next test sees
    # the post-012 schema. ``MigrationExecutor`` re-reads the loader to pick
    # up the migrations we rolled past.
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate([("mentores", "0004_drop_mentor")])


@pytest.mark.django_db(transaction=True)
def test_backfill_runs_as_noop_on_empty_mentor_table(
    reset_to_pre_historicization: Any,
) -> None:
    # State: ``Mentor`` table exists, no rows; ``MentorPeriodo`` does not exist yet.
    mentor_apps = _historical_apps_at(("mentores", "0001_initial"))
    Mentor = mentor_apps.get_model("mentores", "Mentor")
    assert Mentor.objects.count() == 0

    # Forward to 0003 — should run cleanly with zero rows to carry over.
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate([("mentores", "0003_backfill_mentor_periodos")])

    post_apps = _historical_apps_at(("mentores", "0003_backfill_mentor_periodos"))
    MentorPeriodo = post_apps.get_model("mentores", "MentorPeriodo")
    assert MentorPeriodo.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_backfill_preserves_fecha_alta_verbatim(
    reset_to_pre_historicization: Any,
) -> None:
    """The ``auto_now_add`` regression guard: seeded ``Mentor.fecha_alta``
    values must appear unchanged in ``MentorPeriodo.fecha_alta``."""
    mentor_apps = _historical_apps_at(("mentores", "0001_initial"))
    Mentor = mentor_apps.get_model("mentores", "Mentor")
    User = mentor_apps.get_model("usuarios", "User")

    admin = User.objects.create(
        matricula="ADMIN_BACKFILL", email="ab@uaz.edu.mx", role="ADMIN"
    )

    # The legacy ``Mentor.fecha_alta`` is ``auto_now_add=True`` so a plain
    # ``create`` would stamp ``now()``. Use ``filter().update()`` afterwards
    # to bypass ``pre_save`` and pin a specific historical value — that's
    # exactly the regression case: a row whose ``fecha_alta`` is from the
    # past, NOT the migration's ``now``.
    fecha_old_active = datetime(2024, 1, 15, 9, 0, tzinfo=UTC)
    fecha_old_closed_alta = datetime(2023, 6, 1, 12, 0, tzinfo=UTC)
    fecha_old_closed_baja = datetime(2023, 12, 1, 12, 0, tzinfo=UTC)
    fecha_mid = datetime(2025, 3, 10, 8, 0, tzinfo=UTC)

    Mentor.objects.create(
        matricula="A1",
        activo=True,
        fuente="MANUAL",
        nota="active",
        creado_por_id=admin.pk,
    )
    Mentor.objects.create(
        matricula="A2",
        activo=False,
        fuente="CSV",
        nota="closed",
        creado_por_id=admin.pk,
    )
    Mentor.objects.create(
        matricula="A3",
        activo=True,
        fuente="MANUAL",
        nota="middle",
        creado_por_id=admin.pk,
    )
    Mentor.objects.filter(pk="A1").update(fecha_alta=fecha_old_active)
    Mentor.objects.filter(pk="A2").update(
        fecha_alta=fecha_old_closed_alta, fecha_baja=fecha_old_closed_baja
    )
    Mentor.objects.filter(pk="A3").update(fecha_alta=fecha_mid)

    # Forward through 0002 (schema add) and 0003 (data migration).
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate([("mentores", "0003_backfill_mentor_periodos")])

    post_apps = _historical_apps_at(("mentores", "0003_backfill_mentor_periodos"))
    MentorPeriodo = post_apps.get_model("mentores", "MentorPeriodo")

    rows = {p.matricula: p for p in MentorPeriodo.objects.all()}
    assert set(rows) == {"A1", "A2", "A3"}, "All three Mentor rows must backfill"

    # Carry-forward of ``fecha_alta`` — the headline regression guard.
    assert rows["A1"].fecha_alta == fecha_old_active
    assert rows["A2"].fecha_alta == fecha_old_closed_alta
    assert rows["A3"].fecha_alta == fecha_mid

    # ``fecha_baja`` carried for closed row, NULL for the open ones.
    assert rows["A2"].fecha_baja == fecha_old_closed_baja
    assert rows["A1"].fecha_baja is None
    assert rows["A3"].fecha_baja is None

    # Other fields carried verbatim.
    assert (rows["A1"].fuente, rows["A1"].nota) == ("MANUAL", "active")
    assert (rows["A2"].fuente, rows["A2"].nota) == ("CSV", "closed")
    assert rows["A1"].creado_por_id == admin.pk

    # ``desactivado_por`` is NULL for legacy rows (OQ-012-1).
    assert all(p.desactivado_por_id is None for p in rows.values())
