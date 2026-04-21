"""DI wiring for the revision feature."""
from __future__ import annotations

from solicitudes.lifecycle.dependencies import get_lifecycle_service
from solicitudes.revision.services.review_service.implementation import (
    DefaultReviewService,
)
from solicitudes.revision.services.review_service.interface import ReviewService


def get_review_service() -> ReviewService:
    return DefaultReviewService(lifecycle_service=get_lifecycle_service())
