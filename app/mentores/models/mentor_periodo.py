"""Mentor catalog model — per-period (alta, baja) historicization.

Replaces the single-row-per-matrícula ``Mentor`` model with one row per
mentorship period. Reactivation **opens a new period** (a new row) instead
of overwriting the previous row's ``fecha_alta``. The catalog can answer:

- "Is this matrícula currently a mentor?" → exists with ``fecha_baja IS NULL``.
- "What is the full history for this matrícula?" → all rows ordered by
  ``fecha_alta`` desc.
- "Was this matrícula a mentor at this point in time?" → period containing
  the timestamp under the half-open interval ``[fecha_alta, fecha_baja)``.

The partial unique index ``unique_active_period_per_matricula`` enforces the
"at most one open period per matrícula" invariant at the DB level.

**Postgres-only:** the partial unique index requires Postgres. The project's
dev/test stacks both target Postgres; the SQLite fallback in
``config.settings.dev`` will not run these migrations correctly.

**No ``auto_now_add`` on ``fecha_alta``** — Django's ``pre_save`` hook for
``auto_now_add`` fires unconditionally on insert (including via
``bulk_create``) and would silently overwrite explicit values during the
data migration that backfills history from the legacy ``Mentor`` table.
The repository stamps ``fecha_alta = timezone.now()`` explicitly inside
``add_or_reactivate``; the data migration carries forward the original
``Mentor.fecha_alta`` values verbatim.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from mentores.constants import MentorSource


class MentorPeriodo(models.Model):
    """One row per ``(fecha_alta, fecha_baja)`` mentorship period."""

    id = models.BigAutoField(primary_key=True)
    matricula = models.CharField(max_length=20, db_index=True)
    fuente = models.CharField(max_length=16, choices=MentorSource.choices())
    nota = models.CharField(max_length=200, blank=True)
    fecha_alta = models.DateTimeField()
    fecha_baja = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    desactivado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        app_label = "mentores"
        db_table = "mentores_mentorperiodo"
        verbose_name = "periodo de mentor"
        verbose_name_plural = "periodos de mentor"
        constraints = [
            models.UniqueConstraint(
                fields=["matricula"],
                condition=models.Q(fecha_baja__isnull=True),
                name="unique_active_period_per_matricula",
            ),
        ]
        indexes = [
            models.Index(fields=["matricula", "fecha_baja"]),
        ]
        ordering = ["-fecha_alta"]

    def __str__(self) -> str:
        estado = "activo" if self.fecha_baja is None else "inactivo"
        return f"{self.matricula} [{estado}] alta={self.fecha_alta:%Y-%m-%d}"
