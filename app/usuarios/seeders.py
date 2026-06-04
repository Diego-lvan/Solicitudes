"""Dev seed data for the usuarios app.

Materializes one ``User`` per role with the same matriculas the
``/auth/dev-login`` picker expects, so seeded users can log in immediately.

Academic fields (``programa``/``semestre``) stand in for what SIGA would
normally enrich. They matter because tipos can declare auto-fill fields
(``USER_PROGRAMA``, ``USER_SEMESTRE``, …) that resolve from the hydrated
UserDTO; with SIGA unavailable (e.g. the demo deploy) the resolver falls back
to these cached values, so a seeded alumno must carry a ``programa`` for the
Constancia de Estudios intake to succeed.
"""
from __future__ import annotations

from typing import Any

from usuarios.constants import Role
from usuarios.models import User

SEEDED_USERS: list[dict[str, Any]] = [
    {
        "role": Role.ALUMNO,
        "matricula": "ALUMNO_TEST",
        "email": "alumno.test@uaz.edu.mx",
        "full_name": "Ana Alumno Apellido",
        "programa": "Ingeniería de Software",
        "semestre": 6,
    },
    {
        "role": Role.DOCENTE,
        "matricula": "DOCENTE_TEST",
        "email": "docente.test@uaz.edu.mx",
        "full_name": "Diego Docente",
        "programa": "Ingeniería de Software",
        "semestre": None,
    },
    {
        "role": Role.CONTROL_ESCOLAR,
        "matricula": "CE_TEST",
        "email": "ce.test@uaz.edu.mx",
        "full_name": "Carla Control Escolar",
        "programa": "",
        "semestre": None,
    },
    {
        "role": Role.RESPONSABLE_PROGRAMA,
        "matricula": "RP_TEST",
        "email": "rp.test@uaz.edu.mx",
        "full_name": "Raúl Responsable de Programa",
        "programa": "Ingeniería de Software",
        "semestre": None,
    },
    {
        "role": Role.ADMIN,
        "matricula": "ADMIN_TEST",
        "email": "admin.test@uaz.edu.mx",
        "full_name": "Andrea Admin",
        "programa": "",
        "semestre": None,
    },
]


def run(*, fresh: bool) -> None:
    if fresh:
        User.objects.filter(matricula__in=[u["matricula"] for u in SEEDED_USERS]).delete()

    for u in SEEDED_USERS:
        User.objects.update_or_create(
            matricula=u["matricula"],
            defaults={
                "email": u["email"],
                "role": u["role"].value,
                "full_name": u["full_name"],
                "programa": u["programa"],
                "semestre": u["semestre"],
            },
        )
