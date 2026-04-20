# 011 — Field Auto-fill from User Data — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25
- Initiative created from a conversational brainstorm during 003's closeout review.
- Key decisions:
  - **Auto-fill, not prefill.** Fields with `source != USER_INPUT` are invisible to the alumno as inputs; the backend resolves the values from the actor's `UserDTO` at submit time. Rejected: prefill-editable approach (alumno could overwrite, defeating the point of binding to canonical SIGA data).
  - **Failure is hard.** If a required auto-fill field has no resolvable value (SIGA down + cache empty), the submission fails with a clear error pointing the alumno to Control Escolar. No silent partial save. (Aligns with the user's "que falle" answer on the SIGA-down edge case.)
  - **Backend-only resolution.** The "Datos del solicitante" preview panel and the submit-time merge both call `UserService.hydrate_from_siga` server-side. Client-supplied values for auto-fill field_ids are silently dropped — the form factory excludes those fields entirely, so they cannot ride along in `form.to_values_dict()`.
  - **Source ↔ FieldType compatibility** enforced at the schema layer (`_check_source_matches_type` validator) and re-enforced at the form-clean layer (auto-resets to `USER_INPUT` on type switch).
  - **`SigaProfile` shape stays alumno-shaped for now.** Docente sources are deferred to whichever future initiative first needs one (OQ-011-2). The current `UserDTO` already returns empty values for non-applicable academic fields, so a docente filing an alumno-only tipo simply gets empty auto-fill values — no error if the field is optional.
  - **Sequencing.** Schema/admin/builder tasks depend only on 003 and can land before 004 ships intake. Resolver + intake integration depend on 004's `intake/` package existing.
- Open questions captured: OQ-011-1 (refresh button on preview panel), OQ-011-2 (docente SIGA shape), OQ-011-3 (split into 011a/011b vs single initiative).
