from __future__ import annotations

import pytest

from _shared.exceptions import (
    AppError,
    AuthenticationRequired,
    ExternalServiceError,
    NotFound,
    Unauthorized,
)
from usuarios.exceptions import (
    InvalidJwt,
    RoleNotRecognized,
    SigaUnavailable,
    UserNotFound,
)


@pytest.mark.parametrize(
    ("cls", "base", "code", "status"),
    [
        (InvalidJwt, AuthenticationRequired, "invalid_jwt", 401),
        (RoleNotRecognized, Unauthorized, "role_not_recognized", 403),
        (UserNotFound, NotFound, "user_not_found", 404),
        (SigaUnavailable, ExternalServiceError, "siga_unavailable", 502),
    ],
)
def test_usuarios_exceptions_inherit_and_carry_codes(
    cls: type[AppError], base: type[AppError], code: str, status: int
) -> None:
    err = cls()
    assert isinstance(err, base)
    assert isinstance(err, AppError)
    assert err.code == code
    assert err.http_status == status
    assert err.user_message  # not empty
