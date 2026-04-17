"""Build a Django ``LOGGING`` dict that injects the current request id."""
from __future__ import annotations

import contextvars
import logging
from typing import Any

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def set_request_id(request_id: str | None) -> contextvars.Token[str | None]:
    return _request_id_var.set(request_id)


def reset_request_id(token: contextvars.Token[str | None]) -> None:
    _request_id_var.reset(token)


def get_request_id() -> str | None:
    return _request_id_var.get()


class RequestIDFilter(logging.Filter):
    """Attach the current request id (or '-') to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get() or "-"
        return True


def build_logging_config(*, json_format: bool, level: str) -> dict[str, Any]:
    formatters: dict[str, dict[str, Any]]
    if json_format:
        formatters = {
            "default": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "fmt": "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
            }
        }
    else:
        formatters = {
            "default": {
                "format": "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
            }
        }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {"()": "_shared.logging_config.RequestIDFilter"},
        },
        "formatters": formatters,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "filters": ["request_id"],
            },
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
        },
    }
