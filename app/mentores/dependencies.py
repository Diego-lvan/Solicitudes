"""DI factory functions for the mentores feature."""
from __future__ import annotations

import logging

from mentores.adapters.intake_adapter import MentoresIntakeAdapter
from mentores.repositories.mentor import OrmMentorRepository
from mentores.repositories.mentor.interface import MentorRepository
from mentores.services.csv_importer import DefaultMentorCsvImporter
from mentores.services.csv_importer.interface import MentorCsvImporter
from mentores.services.mentor_service import DefaultMentorService
from mentores.services.mentor_service.interface import MentorService
from solicitudes.intake.mentor_port import MentorService as IntakeMentorService


def get_mentor_repository() -> MentorRepository:
    return OrmMentorRepository()


def get_mentor_service() -> MentorService:
    return DefaultMentorService(
        mentor_repository=get_mentor_repository(),
        logger=logging.getLogger("mentores.service"),
    )


def get_mentor_csv_importer() -> MentorCsvImporter:
    return DefaultMentorCsvImporter(
        mentor_repository=get_mentor_repository(),
        logger=logging.getLogger("mentores.csv_importer"),
    )


def get_intake_mentor_adapter() -> IntakeMentorService:
    """Adapter satisfying intake's outbound ``MentorService`` port.

    Returned as the port type so callers (``solicitudes.intake.dependencies``)
    can use it without naming the concrete class.
    """
    return MentoresIntakeAdapter(get_mentor_service())
