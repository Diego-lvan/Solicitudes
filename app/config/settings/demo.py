"""Demo settings — production hardening with the dev-login role picker on.

Used for the public demo deploy (e.g. Railway) where the external auth
provider is not wired up. DEBUG stays False (no tracebacks leak); the only
relaxation vs prod is mounting /auth/dev-login so the app is actually usable.
Inherits everything else from prod: Postgres, WhiteNoise static, JSON logs,
secure cookies, and the fail-fast required env vars.
"""
from __future__ import annotations

from .prod import *  # noqa: F403

# Stand-in for the external auth provider: a role picker at /auth/dev-login.
ENABLE_DEV_LOGIN = True
LOGIN_URL = "/auth/dev-login"
LOGIN_REDIRECT_URL = "/auth/dev-login"
AUTH_PROVIDER_LOGIN_URL = "/auth/dev-login"
AUTH_PROVIDER_LOGOUT_URL = "/auth/dev-login"
