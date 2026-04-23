"""Constants for the archivos feature.

ArchivoKind distinguishes the two roles a stored file can play on a solicitud:
- FORM        — uploaded for a specific FieldDefinition (file-typed field)
- COMPROBANTE — payment receipt, attached when the tipo requires payment and
                the solicitante is not exempt
"""
from __future__ import annotations

from enum import StrEnum


class ArchivoKind(StrEnum):
    FORM = "FORM"
    COMPROBANTE = "COMPROBANTE"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(m.value, m.display_name) for m in cls]

    @property
    def display_name(self) -> str:
        return _KIND_DISPLAY[self]


_KIND_DISPLAY: dict[ArchivoKind, str] = {
    ArchivoKind.FORM: "Archivo de formulario",
    ArchivoKind.COMPROBANTE: "Comprobante de pago",
}


# Global hard ceiling for any uploaded file. Per-field caps from the form
# definition are also enforced; whichever is smaller wins.
GLOBAL_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Comprobante-specific extension whitelist (form-field comprobante is a
# well-known kind, not driven by FieldDefinition).
COMPROBANTE_EXTENSIONS: tuple[str, ...] = (".pdf", ".jpg", ".jpeg", ".png")
