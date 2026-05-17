"""Constants for the respuesta feature."""
from __future__ import annotations

# Maximum files allowed in a single upload batch. Larger deliveries are split
# across multiple batches, which keeps the timeline meaningful.
MAX_FILES_PER_BATCH = 10

# Cap on the comentario textarea, applied both at the form layer and at the
# DTO validator.
MAX_COMENTARIO_CHARS = 2000

# Global hard cap per uploaded file (RT-07). Mirrors archivos.constants.
GLOBAL_MAX_SIZE_BYTES = 10 * 1024 * 1024

# Allowed extensions for response files. Aligned with the intuition behind the
# archivos COMPROBANTE list and the realistic office use case (docs, images,
# zips). Lower-cased; comparison is case-insensitive.
ALLOWED_EXTENSIONS: tuple[str, ...] = (
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
)
