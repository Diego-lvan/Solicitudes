"""Dev seed data for the usuarios app.

Materializes one ``User`` per role with the same matriculas the
``/auth/dev-login`` picker expects, so seeded users can log in immediately.
"""
from __future__ import annotations

from usuarios.constants import Role
from usuarios.models import User

SEEDED_USERS: list[tuple[Role, str, str, str]] = [
    # (role, matricula, email, full_name)
    (Role.ALUMNO, "ALUMNO_TEST", "alumno.test@uaz.edu.mx", "Ana Alumno Apellido"),
    (Role.DOCENTE, "DOCENTE_TEST", "docente.test@uaz.edu.mx", "Diego Docente"),
    (Role.CONTROL_ESCOLAR, "CE_TEST", "ce.test@uaz.edu.mx", "Carla Control Escolar"),
    (
        Role.RESPONSABLE_PROGRAMA,
        "RP_TEST",
        "rp.test@uaz.edu.mx",
        "Raúl Responsable de Programa",
    ),
    (Role.ADMIN, "ADMIN_TEST", "admin.test@uaz.edu.mx", "Andrea Admin"),
]


def run(*, fresh: bool) -> None:
    if fresh:
        User.objects.filter(matricula__in=[m for _, m, _, _ in SEEDED_USERS]).delete()

    for role, matricula, email, full_name in SEEDED_USERS:
        User.objects.update_or_create(
            matricula=matricula,
            defaults={
                "email": email,
                "role": role.value,
                "full_name": full_name,
            },
        )
