from __future__ import annotations

import logging

import pytest

from mentores.exceptions import CsvParseError
from mentores.services.csv_importer import DefaultMentorCsvImporter
from mentores.tests.fakes import InMemoryMentorRepository
from usuarios.constants import Role
from usuarios.schemas import UserDTO

ADMIN = UserDTO(matricula="ADMX", email="admx@x.com", role=Role.ADMIN)

# `transaction.atomic()` inside the importer needs a real DB handle even when
# the repo is in-memory — apply ``django_db`` to every test in this module.
pytestmark = pytest.mark.django_db


@pytest.fixture
def repo() -> InMemoryMentorRepository:
    return InMemoryMentorRepository()


@pytest.fixture
def importer(repo: InMemoryMentorRepository) -> DefaultMentorCsvImporter:
    return DefaultMentorCsvImporter(
        mentor_repository=repo,
        logger=logging.getLogger("test.csv_importer"),
    )


def _csv(*rows: str) -> bytes:
    return ("\n".join(rows) + "\n").encode("utf-8")


def test_clean_csv_inserts_all_rows(importer: DefaultMentorCsvImporter) -> None:
    payload = _csv("matricula", "11111111", "22222222", "33333333")
    result = importer.import_csv(payload, actor=ADMIN)
    assert result.total_rows == 3
    assert result.inserted == 3
    assert result.reactivated == 0
    assert result.skipped_duplicates == 0
    assert result.invalid_rows == []


def test_header_with_bom_accepted(importer: DefaultMentorCsvImporter) -> None:
    payload = b"\xef\xbb\xbfmatricula\n11111111\n"
    result = importer.import_csv(payload, actor=ADMIN)
    assert result.inserted == 1


def test_missing_header_raises(importer: DefaultMentorCsvImporter) -> None:
    payload = _csv("11111111", "22222222")
    with pytest.raises(CsvParseError):
        importer.import_csv(payload, actor=ADMIN)


def test_wrong_header_raises(importer: DefaultMentorCsvImporter) -> None:
    payload = _csv("alumno", "11111111")
    with pytest.raises(CsvParseError):
        importer.import_csv(payload, actor=ADMIN)


def test_empty_file_raises(importer: DefaultMentorCsvImporter) -> None:
    with pytest.raises(CsvParseError):
        importer.import_csv(b"", actor=ADMIN)


def test_non_utf8_raises(importer: DefaultMentorCsvImporter) -> None:
    payload = b"matricula\n\xff\xfe\n"
    with pytest.raises(CsvParseError):
        importer.import_csv(payload, actor=ADMIN)


def test_invalid_rows_accumulate_without_aborting(
    importer: DefaultMentorCsvImporter,
) -> None:
    payload = _csv(
        "matricula",
        "11111111",  # ok
        "abc",  # bad: not 8 digits
        "",  # bad: empty
        "22222222",  # ok
        "1234",  # bad: too short
    )
    result = importer.import_csv(payload, actor=ADMIN)
    assert result.total_rows == 5
    assert result.inserted == 2
    assert len(result.invalid_rows) == 3
    rows = sorted(r["row"] for r in result.invalid_rows)
    assert rows == [3, 4, 6]  # +1 header + 1-based


def test_active_duplicate_is_skipped(
    importer: DefaultMentorCsvImporter, repo: InMemoryMentorRepository
) -> None:
    repo._seed_active("11111111")
    payload = _csv("matricula", "11111111", "22222222")
    result = importer.import_csv(payload, actor=ADMIN)
    assert result.skipped_duplicates == 1
    assert result.inserted == 1


def test_inactive_row_is_reactivated(
    importer: DefaultMentorCsvImporter, repo: InMemoryMentorRepository
) -> None:
    from datetime import UTC, datetime

    from mentores.constants import MentorSource
    from mentores.schemas import MentorPeriodoDTO

    repo._seed(
        MentorPeriodoDTO(
            id=1,
            matricula="11111111",
            fuente=MentorSource.MANUAL,
            nota="",
            fecha_alta=datetime(2025, 1, 1, tzinfo=UTC),
            fecha_baja=datetime(2025, 6, 1, tzinfo=UTC),
            creado_por_matricula="ADM1",
            desactivado_por_matricula="ADM1",
        )
    )
    payload = _csv("matricula", "11111111")
    result = importer.import_csv(payload, actor=ADMIN)
    assert result.reactivated == 1
    assert result.inserted == 0
    assert result.skipped_duplicates == 0


def test_counts_add_up_for_100_rows(
    importer: DefaultMentorCsvImporter, repo: InMemoryMentorRepository
) -> None:
    """Acceptance criterion: inserted + skipped + reactivated + invalid == 100."""
    rows = ["matricula"]
    for i in range(80):
        rows.append(f"{10000000 + i:08d}")
    for i in range(10):
        rows.append("xxx")  # invalid
    for i in range(10):
        rows.append(f"{10000000 + i:08d}")  # duplicates of first 10
    payload = _csv(*rows)
    result = importer.import_csv(payload, actor=ADMIN)
    assert result.total_rows == 100
    assert (
        result.inserted
        + result.skipped_duplicates
        + result.reactivated
        + len(result.invalid_rows)
        == 100
    )
    assert result.inserted == 80
    assert result.skipped_duplicates == 10
    assert len(result.invalid_rows) == 10


def test_whitespace_around_matricula_is_trimmed(
    importer: DefaultMentorCsvImporter,
) -> None:
    payload = _csv("matricula", "  11111111  ", "22222222")
    result = importer.import_csv(payload, actor=ADMIN)
    assert result.inserted == 2
