# Flow — PDF Generation

> **Status:** v1 (initiative 006). Stable end-to-end path for rendering a solicitud as a PDF on demand.
>
> **Owners:** `solicitudes` app — feature `pdf`. Consumes `solicitudes.lifecycle` and `usuarios` via service interfaces.

This flow traces the canonical end-to-end path for downloading the PDF of a solicitud — the complementary terminal action to the lifecycle flow. There are two surfaces that hit the same `PdfService.render_for_solicitud` underneath: the alumno's "Descargar PDF" link on their finalizada solicitud, and the personal/admin "Generar PDF" link on the revision detail page.

## Trigger

Either:

- **Alumno path:** owner of a `FINALIZADA` solicitud opens `/solicitudes/<folio>/` (intake detail) and clicks the **Descargar PDF** button. Button is rendered only when `is_owner and detail.estado == FINALIZADA and detail.tipo.plantilla_id`.
- **Personal/admin path:** opens `/solicitudes/revision/<folio>/` (revision detail) and clicks the **Generar PDF** button. Button is rendered for any estado as long as `detail.tipo.plantilla_id` is set.

Both buttons link to the same URL: `GET /solicitudes/<folio>/pdf/`.

## Sequence (happy path)

```
┌────────┐  ┌────────────────────────┐  ┌────────────┐  ┌─────────────────┐  ┌────────────────────┐  ┌───────────────┐  ┌─────────────┐
│Browser │  │ /solicitudes/          │  │ PdfService │  │ LifecycleService│  │ PlantillaRepository│  │ UserService   │  │ _shared/pdf │
│        │  │  <folio>/pdf/          │  │            │  │                 │  │                    │  │               │  │ render_pdf  │
└───┬────┘  └────────────┬───────────┘  └─────┬──────┘  └────────┬────────┘  └─────────┬──────────┘  └───────┬───────┘  └──────┬──────┘
    │ GET (with stk)     │                    │                  │                     │                    │                 │
    │───────────────────▶│                    │                  │                     │                    │                 │
    │                    │ render_for_solicitud(folio, requester)│                     │                    │                 │
    │                    │───────────────────▶│                  │                     │                    │                 │
    │                    │                    │ get_detail(folio)│                     │                    │                 │
    │                    │                    │─────────────────▶│                     │                    │                 │
    │                    │                    │ SolicitudDetail  │                     │                    │                 │
    │                    │                    │◀─────────────────│                     │                    │                 │
    │                    │                    │ _authorise(...)  │                     │                    │                 │
    │                    │                    │  → ok            │                     │                    │                 │
    │                    │                    │ get_by_id(detail.tipo.plantilla_id)    │                    │                 │
    │                    │                    │─────────────────────────────────────────▶                   │                 │
    │                    │                    │ PlantillaDTO                          │                    │                 │
    │                    │                    │◀────────────────────────────────────────                    │                 │
    │                    │                    │ get_by_matricula(detail.solicitante.matricula)              │                 │
    │                    │                    │──────────────────────────────────────────────────────────────▶                │
    │                    │                    │ UserDTO          │                     │                    │                 │
    │                    │                    │◀──────────────────────────────────────────────────────────────                │
    │                    │                    │ build_render_context(...)              │                    │                 │
    │                    │                    │ engines["django"].from_string(html).render(ctx)             │                 │
    │                    │                    │ assemble_html(body, css)               │                    │                 │
    │                    │                    │ render_pdf(html, base_url=STATIC_ROOT, pdf_identifier=folio.encode())          │
    │                    │                    │──────────────────────────────────────────────────────────────────────────────▶│
    │                    │                    │ pdf bytes                              │                    │                 │
    │                    │                    │◀──────────────────────────────────────────────────────────────────────────────│
    │                    │ PdfRenderResult    │                  │                     │                    │                 │
    │                    │◀───────────────────│                  │                     │                    │                 │
    │ HttpResponse(bytes_,                    │                  │                     │                    │                 │
    │  Content-Type: application/pdf,         │                  │                     │                    │                 │
    │  Content-Disposition: attachment; ...)  │                  │                     │                    │                 │
    │◀───────────────────│                    │                  │                     │                    │                 │
```

## Steps

1. **Routing.** `GET /solicitudes/<folio>/pdf/` matches `re_path(r"^(?P<folio>[A-Z]+-\d{4}-\d{4,})/pdf/$", RenderSolicitudPdfView.as_view(), name="pdf_download")` in `solicitudes/urls.py`. The folio regex is tighter than `<str:folio>` to prevent collision with intake's catch-all detail route.

2. **Authentication (view layer).** `RenderSolicitudPdfView` is decorated with `LoginRequiredMixin`. Anonymous requests trigger `AuthenticationRequired` → `AppErrorMiddleware` redirects to login.

3. **Authorisation (service layer).** The view passes `request.user_dto` straight to `PdfService.render_for_solicitud(folio, requester)`. The service centralises authz so the same matrix applies to any future API surface. See `pdf/design.md` for the full table; in short: ADMIN and personal (CONTROL_ESCOLAR / RESPONSABLE_PROGRAMA) any estado; owner only on `FINALIZADA`; everyone else 403.

4. **Solicitud detail.** `LifecycleService.get_detail(folio)` returns a hydrated `SolicitudDetail` (tipo row with `plantilla_id`, solicitante UserDTO, frozen `form_snapshot`, `valores`, historial). 404 if folio missing.

5. **Plantilla check.** If `detail.tipo.plantilla_id is None` → raise `TipoHasNoPlantilla` (409). The detail templates already hide the trigger button in this case, but the service enforces the gate independent of UI.

6. **Plantilla fetch.** `PlantillaRepository.get_by_id(...)` returns the full `PlantillaDTO` (HTML + CSS).

7. **Solicitante hydration.** `UserService.get_by_matricula(...)` re-fetches the solicitante so SIGA-derived fields (programa, semestre) are populated even if the cached row in `Solicitud.solicitante` is stale or missing them.

8. **Context build.** `build_render_context(solicitud, solicitante, now)` produces `{ solicitante, solicitud, valores, now, firma_lugar_fecha }`. Slugs in `valores` come from `slug_for_label(field.label)` (Django `slugify`, hyphens → underscores).

9. **Template render.** `engines["django"].from_string(plantilla.html).render(ctx)` produces the body. `TemplateSyntaxError` here is wrapped to `PlantillaTemplateError` (422) — should be rare because the service validates syntax at save time, but render-time variables can still trigger errors if the plantilla uses an undefined filter or filter argument.

10. **WeasyPrint.** `render_pdf(full_html, base_url=STATIC_ROOT, pdf_identifier=folio.encode("utf-8"))` produces the bytes. `pdf_identifier` makes the output byte-identical for the same input under a frozen clock.

11. **Response.** `HttpResponse(bytes_, content_type="application/pdf")` with `Content-Disposition: attachment; filename="<slug>-<folio>.pdf"`. The browser saves the file.

## Failure modes

| Cause | Where caught | Status | User-facing message |
| ---   | ---          | ---    | --- |
| Anonymous request | `LoginRequiredMixin` | 302 redirect | (sent to login) |
| Folio doesn't exist | `LifecycleService.get_detail` | 404 | "La solicitud solicitada no existe." |
| Owner before FINALIZADA / non-owner non-personal | `PdfService._authorise` | 403 | "No puedes generar el PDF de esta solicitud." |
| Tipo has no plantilla | `PdfService.render_for_solicitud` step 5 | 409 | "Este tipo de solicitud no tiene plantilla configurada." |
| Plantilla syntax error at render | `engines["django"].from_string(...).render` | 422 | "La plantilla tiene un error de sintaxis." |

All errors flow through `_shared.exceptions.AppError` and `AppErrorMiddleware`.

## Determinism guarantee

Two `GET /solicitudes/SOL-2026-00042/pdf/` requests issued under a frozen clock with no intervening data change produce byte-identical responses. The lever is `pdf_identifier` (WeasyPrint `/ID`) plus `freezegun` fixing `/CreationDate` and `/ModDate`. This is a within-environment guarantee — `STATIC_ROOT` is part of `base_url`, so a plantilla that references `/static/foo.png` may render different bytes across deployments. Plantillas that need cross-deployment byte-stability should embed images as `data:` URIs.

## Adjacent flows

- [solicitud-lifecycle.md](./solicitud-lifecycle.md) — the upstream flow that brings a solicitud to `FINALIZADA`, after which the alumno can download the PDF.

## Notes

- No PDF blob is ever stored. The plantilla + the solicitud's frozen `form_snapshot` + `valores` + the solicitante's current SIGA fields are the canonical source; the bytes are re-derivable on demand.
- `PlantillaPreviewView` (admin-only, `/admin/plantillas/<id>/preview.pdf`) takes a separate path that uses `build_synthetic_context` instead of a real `SolicitudDetail`. Same WeasyPrint wrapper, same determinism story (`pdf_identifier=str(plantilla_id).encode("ascii")`). Returns `Content-Disposition: inline` so the embedded iframe renders rather than downloads, with `X-Frame-Options: SAMEORIGIN` (decorator scoped to that view; rest of the app stays DENY).
