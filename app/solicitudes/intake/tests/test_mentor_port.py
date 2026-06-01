"""Tests for the default mentor port adapter (pre-008 binding)."""
from __future__ import annotations

from solicitudes.intake.mentor_port import FalseMentorService


def test_false_mentor_service_always_reports_not_a_mentor() -> None:
    service = FalseMentorService()
    assert service.is_mentor("A12345") is False
