from __future__ import annotations

import time

import jwt
import pytest

from _shared.auth import decode_jwt, parse_claims
from _shared.exceptions import AuthenticationRequired

SECRET = "unit-test-secret-must-be-at-least-32-bytes-long"
ALGS = ["HS256"]


def _token(payload: dict[str, object]) -> str:
    return jwt.encode(payload, SECRET, algorithm="HS256")


def test_decode_valid_token() -> None:
    now = int(time.time())
    token = _token(
        {"sub": "12345", "email": "u@uaz.edu.mx", "rol": "alumno", "iat": now, "exp": now + 60}
    )
    payload = decode_jwt(token, secret=SECRET, algorithms=ALGS)
    claims = parse_claims(payload)
    assert claims.sub == "12345"
    assert claims.rol == "alumno"


def test_expired_token_raises_authentication_required() -> None:
    now = int(time.time())
    token = _token(
        {"sub": "x", "email": "u@x", "rol": "alumno", "iat": now - 200, "exp": now - 100}
    )
    with pytest.raises(AuthenticationRequired):
        decode_jwt(token, secret=SECRET, algorithms=ALGS)


def test_invalid_signature_raises_authentication_required() -> None:
    now = int(time.time())
    token = jwt.encode(
        {"sub": "x", "email": "u@x", "rol": "alumno", "iat": now, "exp": now + 60},
        "another-different-unit-test-secret-32-bytes-min",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationRequired):
        decode_jwt(token, secret=SECRET, algorithms=ALGS)


def test_garbage_token_raises_authentication_required() -> None:
    with pytest.raises(AuthenticationRequired):
        decode_jwt("not-a-jwt", secret=SECRET, algorithms=ALGS)
