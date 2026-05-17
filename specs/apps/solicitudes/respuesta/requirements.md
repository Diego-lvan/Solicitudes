# respuesta — Requirements

> WHAT this feature does and WHY. No implementation details.

## Purpose

Today, the only "output" of a solicitud is the auto-rendered template PDF (`solicitudes/pdf`), and the solicitante is shown that PDF when the solicitud reaches `FINALIZADA`. In practice the template is a *draft aid* — the personal that atiende needs to print it, sign it, possibly attach extra documents, and only then is there a real deliverable. The current flow treats the draft as the final output, which is wrong.

This feature changes the model: the template-rendered PDF becomes a **draft for the handler only**, and the handler explicitly **uploads one or more response files (with an optional comment)** that become what the solicitante receives. The handler can build the response over multiple uploads while the solicitud is `EN_PROCESO`; uploads are append-only; the solicitante sees the response only after `FINALIZADA`.

This satisfies the operational need behind **RF-09** (atención de solicitudes) by making the deliverable explicit rather than implicit, and reframes **RF-03** plantillas as authoring aids rather than the final document.

## User stories

- As **personal in the responsible role**, I want to download the template pre-filled with the solicitud data so that I can use it as a starting point for the official document I'll deliver, without re-typing the solicitante's info.
  - **Acceptance:** From the revision detail page of a solicitud whose tipo has a plantilla, I can click "Descargar borrador" and receive the same PDF the system renders today, labeled as a draft.
  - **Acceptance:** When the tipo has no plantilla, the "Descargar borrador" affordance is not shown.

- As **personal in the responsible role**, I want to attach one or more response files to a solicitud I'm working on, with an optional comment, so that the solicitante receives the actual signed/finished documents (which may or may not be the templated draft).
  - **Acceptance:** While the solicitud is `EN_PROCESO`, the revision detail page exposes a form that accepts 0–10 files plus an optional comment (≤ 2000 chars).
  - **Acceptance:** A submission with neither files nor a non-empty comment is rejected with a clear message.
  - **Acceptance:** Submitting persists the upload as a single batch (timestamp, actor, optional comment, attached files). Multiple batches per solicitud are allowed.
  - **Acceptance:** Files are subject to the same per-file rules as intake archivos (10 MB hard cap, existing extension allow-list, ZIPs stored as-is).
  - **Acceptance:** The handler cannot upload batches while the solicitud is `CREADA`, `FINALIZADA`, or `CANCELADA`. Attempting to do so yields a 409 with a Spanish error message.

- As **personal in the responsible role**, I want my uploads to be append-only so that the audit trail of what I delivered is preserved.
  - **Acceptance:** There is no in-app affordance to delete or replace a previously-uploaded response file or batch. The Django admin remains an escape hatch for exceptional cases.

- As **the solicitante**, I want to see and download the response files (and read the handler's comments) once my solicitud is `FINALIZADA`, so that I receive the actual deliverable.
  - **Acceptance:** While the solicitud is in any non-terminal estado, no response files or comments are visible to the solicitante.
  - **Acceptance:** Once `FINALIZADA`, the intake detail page shows a "Documentos de respuesta" section listing each batch in chronological order: actor name, timestamp, comment (if any), and a downloadable link per file.
  - **Acceptance:** The solicitante does not receive a PDF download of the auto-rendered template at any point in the flow.

- As **an admin**, I want full visibility into response uploads on any solicitud regardless of estado, so that I can audit deliveries.
  - **Acceptance:** Admin can list and download response files for any solicitud at any estado.

## Constraints

- **Append-only at the app layer.** Reason: response files are a delivery record; in-app deletion would erode the audit trail. Removal remains possible via Django admin for exceptional cases.
- **Visibility to solicitante is gated by `FINALIZADA`.** Reason: matches today's behavior for the template PDF and prevents work-in-progress from leaking to the solicitante.
- **Upload window is `EN_PROCESO` only.** Reason: forces the handler to explicitly take the solicitud (`CREADA → EN_PROCESO`) before delivering, keeping intent visible in the lifecycle history.
- **Per-file 10 MB cap (RT-07) and the existing extension allow-list apply.** Reason: consistency with `archivos`; no new validation surface.
- **Max 10 files per upload batch.** Reason: soft cap that matches realistic office deliveries; larger deliveries split into multiple batches and remain visible in the timeline.
- **No new email notification per upload batch.** Reason: the existing `FINALIZADA` notification (RF-07) already signals to the solicitante that the deliverable is ready.
- **All UI copy in Spanish (es-MX), per RT-08.**

## Non-goals

- **Editing or deleting response files via the application.** Append-only is intentional. Django admin is the escape hatch.
- **Per-file comments.** One optional comment per batch, never per file.
- **Solicitante-side replies or threading.** Communication is one-way: handler → solicitante.
- **Email notification on each upload batch.** Only the existing `FINALIZADA` email remains.
- **Bulk / zip download of all response files.** One-by-one download only.
- **Auto-attaching the rendered template PDF into a response batch.** The handler always decides what to upload.
- **Solicitante visibility into response files while `EN_PROCESO`.** Strictly hidden until `FINALIZADA`.
- **Changing the PDF rendering engine, plantilla authoring surface, or the plantilla data model.** The `pdf` feature continues to render on demand from the live solicitud; only its consumer-side authorization changes.

## Related modules

- → `apps/solicitudes/pdf` — the auto-rendered template becomes a draft for the handler; its authorization matrix drops the "owner / FINALIZADA → allowed" row. The intake detail template no longer surfaces a "Descargar PDF" button to the solicitante; the revision detail relabels its button to "Descargar borrador".
- → `apps/solicitudes/lifecycle` — read-only consumer via `LifecycleService.get_detail` to resolve the solicitud, validate estado for write paths, and obtain solicitante matrícula for the download authorization check.
- → `apps/solicitudes/revision` — the revision detail template hosts the new upload form and the list of existing batches for the handler.
- → `apps/solicitudes/intake` — the alumno-facing detail template gains a "Documentos de respuesta" section, rendered only when `estado == FINALIZADA`.
- → `apps/solicitudes/archivos` — **not modified**. The per-file size/extension rules are reused (lifted or duplicated as a small util; decided in `plan.md`).
- → `apps/notificaciones` — **not modified**. The existing `FINALIZADA` email is the only notification touching this flow.
- → `shared/infrastructure` — reuses the existing `FileStorage` abstraction for bytes.
- → `flows/` — a new cross-feature flow doc may be added after the initiative completes, covering the handler-delivers-response path end-to-end.

## Open questions

- Should the per-file extension/size validation logic be **lifted from `archivos` into a small shared util**, or duplicated locally inside `respuesta`? Either preserves `archivos`' invariants; decision belongs in `plan.md` based on how much code is involved.
- Comment text rendering in the templates: plain text vs. light Markdown. Default is plain text with line breaks preserved; revisit only if users ask for formatting.
- Whether to emit a new entry in the solicitud's existing `HistorialEstado` timeline (or a parallel `eventos` log) for each batch, so the revision detail shows uploads inline with state transitions. Out of scope for v1; can be added without schema breakage later.
