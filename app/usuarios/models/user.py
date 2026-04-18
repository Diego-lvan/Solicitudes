"""Custom User model.

Authentication is delegated to an external provider (RNF-01); we never issue
tokens, never run a login form, and never persist passwords. The model exists
solely to (a) satisfy Django's auth contract for `request.user`, and (b) cache
identity attributes that come from the JWT and SIGA so consumer features can
read them without a second round-trip.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models

from usuarios.constants import Role

if TYPE_CHECKING:
    pass


class UserManager(BaseUserManager["User"]):
    """Manager that intentionally rejects password-based creation.

    Users are upserted from validated JWT claims via the repository layer; the
    Django auth machinery only needs ``get_by_natural_key`` to look up an
    existing row by ``matricula``.
    """

    use_in_migrations = True

    def create_user(self, *args: Any, **kwargs: Any) -> User:
        raise NotImplementedError(
            "Authentication is external; users are upserted via UserRepository."
        )

    def create_superuser(self, *args: Any, **kwargs: Any) -> User:
        raise NotImplementedError(
            "Authentication is external; superusers are not supported."
        )

    def get_by_natural_key(self, username: str | None) -> User:
        return self.get(**{self.model.USERNAME_FIELD: username})


class User(AbstractBaseUser):
    """External-auth user keyed by ``matricula``.

    The ``password`` field inherited from ``AbstractBaseUser`` is left in place
    for ORM compatibility but is never written; Django's auth backends never
    call ``set_password`` on this model.
    """

    matricula = models.CharField(max_length=20, primary_key=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=32, choices=Role.choices())
    full_name = models.CharField(max_length=200, blank=True)
    programa = models.CharField(max_length=200, blank=True)
    semestre = models.IntegerField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "matricula"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["email", "role"]

    objects = UserManager()

    class Meta:
        app_label = "usuarios"
        db_table = "usuarios_user"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self) -> str:
        return f"{self.matricula} <{self.email}>"

    def get_full_name(self) -> str:
        return self.full_name or self.matricula

    def get_short_name(self) -> str:
        return self.full_name.split(" ")[0] if self.full_name else self.matricula
