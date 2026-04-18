from __future__ import annotations

from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    name = "usuarios"
    verbose_name = "Usuarios y autenticación"
    default_auto_field = "django.db.models.BigAutoField"
