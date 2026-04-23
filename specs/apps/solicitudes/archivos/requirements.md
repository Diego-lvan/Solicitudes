# archivos — Requirements

## Purpose

Persistent storage for solicitud attachments. Two kinds of files attach to a solicitud:

- **FORM** files — uploads bound to a `FieldDefinition` of `field_type=FILE`
- **COMPROBANTE** files — payment receipts attached when the tipo requires payment and the solicitante is not exempt

Files are validated at upload (extension + size), stored by a backend-agnostic
`FileStorage` interface (currently `LocalFileStorage`, future S3/Azure Blob),
indexed by an `ArchivoSolicitud` row, and downloadable only by the
solicitante, the responsible-role personal, or an admin.

## Functional requirements

- **RF-04**: comprobante de pago is required when `tipo.requires_payment AND not pago_exento`; absence rejects the form with `comprobante_required`.
- **RF-10**: the system organizes files by `solicitud.folio`. ZIP files are stored as-is — no extraction.
- **RT-07**: every uploaded file is hard-capped at 10 MB. Per-`FieldDefinition` `max_size_mb` may be smaller; the smaller value wins.

## Non-goals

- Antivirus / malware scanning (deferred; if compliance requires it, plug in a `FileScanner` adapter at the service entry point).
- Total-storage cap per solicitud (no aggregate cap; only the per-file cap applies).
- Editing files post-upload. Re-upload semantics replace the prior file (one row per `(folio, field_id)` for FORM, one COMPROBANTE per folio).
- Direct upload URLs. Files are submitted as part of the intake form's `multipart/form-data`; archivos has no dedicated POST endpoint of its own.

## Authorization

- Read (download): solicitante, responsible-role personal, or admin.
- Mutate (delete archivo): solicitante or admin, only while the solicitud is in `CREADA`.
- Files become immutable once the solicitud transitions to `EN_PROCESO` or beyond.

## State boundaries

- FORM uploads only allowed in `CREADA`. After `EN_PROCESO`, the form fields are locked and no FORM archivo can be added or replaced.
- COMPROBANTE uploads only allowed in `CREADA`. (Re-upload during review is intentionally out of scope; if a comprobante is wrong at review time, the solicitud is cancelled and re-filed.)

## Related Specs

- [design.md](./design.md) — canonical reference for shape + wiring
- [planning/005-file-management](../../../planning/005-file-management/plan.md) — implementation initiative
- [apps/solicitudes/intake/design.md](../intake/design.md) — the only caller of `archivo_service.store_for_solicitud`
- [apps/solicitudes/lifecycle/design.md](../lifecycle/design.md) — `SolicitudDetail` is the cross-feature read source
