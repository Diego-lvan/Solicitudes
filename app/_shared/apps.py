from __future__ import annotations

from django.apps import AppConfig


class SharedConfig(AppConfig):
    name = "_shared"
    verbose_name = "Shared infrastructure"
