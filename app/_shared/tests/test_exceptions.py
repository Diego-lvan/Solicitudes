from __future__ import annotations

import pytest

from _shared.exceptions import (
    AppError,
    AuthenticationRequired,
    Conflict,
    DomainValidationError,
    ExternalServiceError,
    NotFound,
    Unauthorized,
)


@pytest.mark.parametrize(
    ("cls", "code", "status"),
    [
        (AppError, "app_error", 500),
        (NotFound, "not_found", 404),
        (Conflict, "conflict", 409),
        (Unauthorized, "unauthorized", 403),
        (AuthenticationRequired, "authentication_required", 401),
        (DomainValidationError, "validation_error", 422),
        (ExternalServiceError, "external_service_error", 502),
    ],
)
def test_each_subclass_carries_code_and_status(
    cls: type[AppError], code: str, status: int
) -> None:
    err = cls()
    assert err.code == code
    assert err.http_status == status
    assert err.user_message  # not empty


def test_domain_validation_error_collects_field_errors() -> None:
    err = DomainValidationError("bad", field_errors={"name": ["requerido"]})
    assert err.field_errors == {"name": ["requerido"]}


def test_app_error_subclasses_are_exceptions() -> None:
    with pytest.raises(NotFound):
        raise NotFound("missing")


def test_default_field_errors_is_empty_dict() -> None:
    err = DomainValidationError()
    assert err.field_errors == {}
