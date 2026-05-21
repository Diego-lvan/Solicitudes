"""Helper: build the static panel variable lists for the plantilla editor."""
from __future__ import annotations


def panel_variables() -> dict[str, list[tuple[str, str]]]:
    """Snippets clickable from the editor's Variables tab.

    Each tuple is (snippet, label). Snippets are the literal Django template
    syntax inserted into the textarea; labels are Spanish prose for the chip.
    """
    return {
        "variables_solicitante": [
            ("{{ solicitante.nombre }}", "Nombre"),
            ("{{ solicitante.matricula }}", "Matrícula"),
            ("{{ solicitante.email }}", "Email"),
            ("{{ solicitante.programa }}", "Programa"),
            ("{{ solicitante.semestre }}", "Semestre"),
            ("{{ solicitante.genero }}", "Género"),
        ],
        "variables_solicitud": [
            ("{{ solicitud.folio }}", "Folio"),
            ("{{ solicitud.estado }}", "Estado"),
            ("{{ solicitud.tipo_nombre }}", "Tipo"),
            ("{{ solicitud.created_at }}", "Creación"),
            ("{{ solicitud.updated_at }}", "Actualización"),
        ],
        "variables_fecha": [
            ("{{ firma_lugar_fecha }}", "Lugar y fecha"),
            ("{{ now }}", "Ahora"),
        ],
    }
