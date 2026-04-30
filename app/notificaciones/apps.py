from __future__ import annotations

from django.apps import AppConfig


class NotificacionesConfig(AppConfig):
    name = "notificaciones"
    verbose_name = "Notificaciones por correo"
    default_auto_field = "django.db.models.BigAutoField"
