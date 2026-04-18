"""DI factory functions for the usuarios feature.

Wiring lives here so views/middleware never instantiate concretions directly.
"""
from __future__ import annotations

import logging

from django.conf import settings

from usuarios.repositories.user import OrmUserRepository, UserRepository
from usuarios.services.role_resolver import JwtRoleResolver, RoleResolver
from usuarios.services.siga import HttpSigaService, SigaService
from usuarios.services.user_service import DefaultUserService, UserService


def get_user_repository() -> UserRepository:
    return OrmUserRepository()


def get_role_resolver() -> RoleResolver:
    return JwtRoleResolver()


def get_siga_service() -> SigaService:
    return HttpSigaService(
        base_url=settings.SIGA_BASE_URL,
        timeout_seconds=settings.SIGA_TIMEOUT_SECONDS,
        logger=logging.getLogger("usuarios.siga"),
    )


def get_user_service() -> UserService:
    return DefaultUserService(
        user_repository=get_user_repository(),
        role_resolver=get_role_resolver(),
        siga_service=get_siga_service(),
        logger=logging.getLogger("usuarios.user_service"),
    )
