"""Unit tests for the formularios file validators."""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from solicitudes.formularios.validators import (
    make_extension_validator,
    make_size_validator,
)

# ---- extension validator ----


def test_extension_validator_accepts_allowed() -> None:
    validate = make_extension_validator([".pdf", ".zip"])
    validate(SimpleUploadedFile("a.PDF", b"x", content_type="application/pdf"))


def test_extension_validator_rejects_disallowed() -> None:
    validate = make_extension_validator([".pdf"])
    with pytest.raises(ValidationError):
        validate(SimpleUploadedFile("a.exe", b"x"))


def test_extension_validator_ignores_none_file_or_name() -> None:
    validate = make_extension_validator([".pdf"])
    # None file → no-op (early return).
    validate(None)  # type: ignore[arg-type]
    # File with no name → no-op.
    f = SimpleUploadedFile("placeholder.pdf", b"x")
    f.name = None  # type: ignore[assignment]
    validate(f)


# ---- size validator ----


def test_size_validator_accepts_within_limit() -> None:
    validate = make_size_validator(1)
    validate(SimpleUploadedFile("a.pdf", b"x" * 10))


def test_size_validator_rejects_over_limit() -> None:
    validate = make_size_validator(1)
    big = SimpleUploadedFile("a.pdf", b"x" * (2 * 1024 * 1024))
    with pytest.raises(ValidationError):
        validate(big)


def test_size_validator_ignores_none_file() -> None:
    validate = make_size_validator(1)
    validate(None)  # type: ignore[arg-type]
