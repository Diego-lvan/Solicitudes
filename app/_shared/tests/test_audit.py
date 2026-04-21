"""Tests for the structured audit-log writer."""
from __future__ import annotations

import logging

import pytest

from _shared import audit


def test_write_emits_info_with_event_and_extra(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="audit")
    audit.write("solicitud.creada", folio="SOL-2026-00001", actor="ALU-1")
    records = [r for r in caplog.records if r.name == "audit"]
    assert len(records) == 1
    record = records[0]
    assert record.levelno == logging.INFO
    assert record.msg == "solicitud.creada"
    assert getattr(record, "audit_event") == "solicitud.creada"
    assert getattr(record, "folio") == "SOL-2026-00001"
    assert getattr(record, "actor") == "ALU-1"
