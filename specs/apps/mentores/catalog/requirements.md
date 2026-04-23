# mentores · catalog — Requirements

> WHAT this feature does and WHY. No implementation details. Shipped by initiative **008 — Mentors**.

## Purpose

Maintain the institution's authoritative list of student matrículas registered as **mentors**. Mentors are *exempt from the comprobante de pago* on tipos that set `mentor_exempt=True` (RF-04, RF-11). Without this catalog, the intake feature has no way to honor the exemption rule.

The feature is admin-facing only: catalog reads happen on the intake hot path through a single boolean (`is_mentor(matricula)`), but every write surface (manual add, manual deactivate, CSV bulk import) is restricted to administrators.

## Why this is a feature, not a list in code

The set of mentors changes every semester — new matrículas are added, others stop participating. The university wants to manage this data **without releases**, exactly the same way they manage `tipos` (RF-01). Hard-coding the list, sourcing it from SIGA, or treating it as configuration are all wrong shapes:

- Hard-coding loses the audit trail and forces a deploy on every change.
- SIGA does not flag mentors today; even if it did, the institution wants local control.
- A flat config file has no per-row provenance (who registered the mentor, from which import) and no soft-delete history.

## In scope

- An **admin CRUD surface** over the mentor catalog: list (filter by active/all), manual add by matrícula, manual soft-delete (deactivation), and bulk CSV import.
- A **single-boolean read API** consumed by `solicitudes/intake` (`is_mentor(matricula) -> bool`) — the only thing intake needs.
- **Per-row provenance**: which admin created the row, what source it came from (manual or CSV), an optional note, and the date of the current `(alta, baja)` period.
- **Soft delete** so the matrícula stays queryable after deactivation; reactivating a previously-deactivated matrícula is supported.
- A **CSV importer** that tolerates per-row errors (invalid matrículas) without aborting the batch and reports counts (`inserted`, `reactivated`, `skipped_duplicates`, `invalid_rows`) on a result page.
- Cross-feature integration with intake via an **adapter the producer (mentores) provides** to satisfy intake's outbound `MentorService` port.

## Out of scope

- The **comprobante exemption snapshot** itself. That stamping (`Solicitud.pago_exento`) is owned by the intake feature; the catalog only answers `is_mentor(matricula)` at create-time. Past solicitudes must keep their stamped exemption even after a mentor is deactivated (OQ-008-2 — handled by stamping at intake, not by this catalog).
- **Historical period queries** ("was matrícula M a mentor on 2024-04-15?"). This catalog stores *current state only*; reactivation overwrites the prior period. Full historicization is a separate feature in `specs/apps/mentores/historicization/` (initiative 012).
- **Audit log of catalog edits** beyond the per-row `creado_por` + soft-delete fields. If richer auditing is required, that's a future cross-cutting concern wired through `_shared/audit.py`.
- **Self-service mentor signup** or any non-admin write path.
- **Mentor-program metadata** (which program, which mentees, schedule, etc.). This catalog answers a binary question; richer mentor data is not in scope.

## Functional requirements

| ID | Requirement | Source |
|---|---|---|
| RF-MEN-01 | An admin can list mentors, filtered by `solo activos` (default) or `todos`, paginated. | RF-11 |
| RF-MEN-02 | An admin can add a mentor by matrícula. The matrícula format is validated against a configurable regex; an already-active matrícula must be rejected with a clear error. | RF-11 |
| RF-MEN-03 | An admin can deactivate a mentor. Deactivation is idempotent — deactivating an already-inactive matrícula must not error. | RF-11 |
| RF-MEN-04 | An admin can bulk-import matrículas from a single-column CSV (header `matricula`). The importer must report `total_rows`, `inserted`, `reactivated`, `skipped_duplicates`, and a list of `invalid_rows` with row number and reason. Per-row failures must not abort the batch. | RF-11 |
| RF-MEN-05 | The intake feature can ask `is_mentor(matricula) -> bool` and get a correct answer for currently-active mentors, with no other coupling between the two features. | RF-04, RF-11 |
| RF-MEN-06 | A previously-deactivated matrícula must be reactivatable (manually or via CSV import); the system must distinguish "new" from "reactivated" in import counts. | inferred from operational use |
| RF-MEN-07 | Every catalog row carries provenance: source (manual / CSV), the admin who created it, an optional note, and the timestamps of the current period. | RNF-04 |
| RF-MEN-08 | All catalog endpoints (list, add, deactivate, import) must be admin-only; non-admin access returns 403. | RNF-06 |

## Non-functional requirements

- **Cross-feature isolation.** The mentor catalog is a *producer* — it provides an adapter that satisfies intake's consumer-defined `MentorService` port. Intake must not import from `mentores.*` directly. This keeps intake's contract stable as the catalog evolves (e.g., when initiative 012 grows the service with `was_mentor_at` and `get_history`).
- **Stamping integrity.** Whatever `is_mentor(matricula)` returns at the moment a solicitud is filed is the answer for that solicitud forever. Catalog changes after creation must never retroactively alter a stored `pago_exento`.
- **Concurrent admin edits are safe.** Two admins working on the catalog at once must not corrupt the active/inactive flag for the same matrícula (the system must serialize per-matrícula writes, not the whole table).
- **Spanish UI copy** end-to-end (list, add, import, confirm-deactivate). Form labels, error messages, and import-result counts are all in Spanish. Code identifiers in English.
- **Hard delete is impossible by design.** Deactivation is the only removal verb; there is no admin path to remove a row, because future audit queries (and the historicization feature in 012) need the matrícula to remain present.

## Known limitations (deferred to initiative 012)

- The catalog stores **current state only**: reactivating an inactive matrícula resets `fecha_alta` and clears `fecha_baja`. The prior period is lost.
- Deactivation does not capture **who deactivated** (only `creado_por` for the current period).
- There is no detail view at `/mentores/<matricula>/` yet; the list view links to a placeholder URL that 012 fills in.

These are addressed by `specs/apps/mentores/historicization/` (initiative 012).

## Open Questions

- **OQ-008-1** — *(resolved, 2026-04-25)* matrícula format. The default regex is `^\d{8}$`, configurable via the `MENTOR_MATRICULA_REGEX` setting so a different institution rule can be applied without a code change.
- **OQ-008-2** — *(resolved, 2026-04-25)* snapshot integrity for `pago_exento`. The exemption is **stamped at intake-creation time** onto `Solicitud`, so deactivating a mentor afterwards does not retroactively change exemption on prior solicitudes. The catalog feature is intentionally not responsible for protecting that invariant.

## Related Specs

- [design.md](./design.md) — HOW.
- [`specs/apps/mentores/historicization/requirements.md`](../historicization/requirements.md) — successor initiative (012) that adds full per-period history.
- [`specs/apps/solicitudes/intake/design.md`](../../solicitudes/intake/design.md) — the only consumer of `is_mentor`; defines the outbound port.
- [`specs/planning/008-mentors/plan.md`](../../../planning/008-mentors/plan.md) — implementation blueprint.
- [`specs/global/requirements.md`](../../../global/requirements.md) — RF-04, RF-11.
- [`specs/flows/solicitud-lifecycle.md`](../../../flows/solicitud-lifecycle.md) — the cross-app flow that consumes `is_mentor`.
