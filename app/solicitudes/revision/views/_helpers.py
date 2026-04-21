"""View helpers for the revision feature.

The actor lookup is delegated to ``_shared.request_actor`` so all logged-in
views share the same implementation. This module is kept to host any future
revision-specific helpers.
"""
from __future__ import annotations

from _shared.request_actor import actor_from_request

__all__ = ["actor_from_request"]
