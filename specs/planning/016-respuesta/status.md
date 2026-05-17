# 016 — Response Files & Comments — Status

**Status:** Done
**Last updated:** 2026-05-17

## Checklist

### Models & migration
- [x] Add `RespuestaSolicitud` to `app/solicitudes/models/respuesta_solicitud.py`
- [x] Add `ArchivoRespuesta` to `app/solicitudes/models/archivo_respuesta.py`
- [x] `makemigrations solicitudes` and commit the single new migration
- [x] `migrate --plan` shows no drift after running

### Feature scaffold (respuesta)
- [x] [P] `respuesta/constants.py`
- [x] [P] `respuesta/exceptions.py` (6 exception classes inheriting from `_shared.exceptions`)
- [x] [P] `respuesta/schemas.py` (`UploadedFile`, `CreateRespuestaInput`, `ArchivoRespuestaDTO`, `RespuestaDTO`, `ArchivoRespuestaRecord`)
- [x] `respuesta/repositories/respuesta/interface.py` (`RespuestaRepository(ABC)`)
- [x] `respuesta/repositories/respuesta/implementation.py` (`OrmRespuestaRepository`)
- [x] `respuesta/services/respuesta_service/interface.py` (`RespuestaService(ABC)`)
- [x] `respuesta/services/respuesta_service/implementation.py` (`DefaultRespuestaService`)
- [x] `respuesta/forms/respuesta_upload_form.py` (`RespuestaUploadForm`)
- [x] `respuesta/views/personal.py` (`CreateRespuestaView`)
- [x] `respuesta/views/shared.py` (`DownloadArchivoRespuestaView`)
- [x] `respuesta/urls.py` (mounted, `app_name = "respuesta"`)
- [x] `respuesta/dependencies.py` (factory wiring, reuses `archivos.dependencies.get_file_storage`)
- [x] Include `respuesta.urls` from `app/solicitudes/urls.py`

### Tests (respuesta)
- [x] [P] `respuesta/tests/test_schemas.py` (empty-batch + 10-file caps via DTO validator)
- [x] [P] `respuesta/tests/test_exceptions.py` (HTTP status sentinels)
- [x] [P] `respuesta/tests/test_forms.py` (valid combos, empty rejection, 11-files rejection)
- [x] `respuesta/tests/test_respuesta_repository.py` (real DB; create, list, get_archivo_record, query-count cap)
- [x] `respuesta/tests/test_respuesta_service.py` (in-memory fake repo + recording fake storage; state guards; transactional rollback; visibility matrix)
- [x] `respuesta/tests/test_views.py` (HTTP layer; permission matrix; download authz)
- [x] `respuesta/tests/fakes.py` (`InMemoryRespuestaRepository`, `RecordingFileStorage`)
- [x] `respuesta/tests/factories.py` (`make_respuesta`, `make_archivo_respuesta`)

### PDF authz amendment
- [x] Drop the owner-FINALIZADA branch from `pdf/services/pdf_service/implementation.py::_authorize_render_for_solicitud`
- [x] Update `pdf/tests/test_pdf_service.py` (owner/FINALIZADA → Unauthorized) and the `test_views.py` matrix accordingly

### Template & view-context updates
- [x] Remove the "Descargar PDF" button from `templates/solicitudes/intake/detail.html`
- [x] Add the "Documentos de respuesta" section to `intake/detail.html` (gated on `estado == FINALIZADA` AND batches non-empty)
- [x] Relabel the PDF button in `templates/solicitudes/revision/detail.html` to "Descargar borrador"
- [x] Add the "Adjuntar respuesta" card to `revision/detail.html` (gated on `estado == EN_PROCESO`)
- [x] Add the "Respuestas entregadas" listing card to `revision/detail.html`
- [x] Wire `respuestas` and `upload_form` context keys in `solicitudes/intake/views/detail.py` and `solicitudes/revision/views/detail.py`

### E2E
- [x] Tier 1 (Client): personal uploads two batches, finalizes, alumno sees only after FINALIZADA — in `respuesta/tests/test_views.py`
- [x] Tier 1 (Client): PDF owner-FINALIZADA authz regression — in `pdf/tests/test_views.py`
- [x] Tier 2 (browser/Playwright): personal adjuntar respuesta + finalizar, alumno descarga — `tests-e2e/tests/test_respuesta_flow.py`

### Closeout
- [x] `/review` passes against `plan.md`
- [x] Update `apps/solicitudes/respuesta/design.md` (promote from this plan)
- [x] Update `apps/solicitudes/pdf/design.md` (authz matrix)
- [x] Update `apps/solicitudes/revision/design.md` (new card references)
- [x] Update `apps/solicitudes/intake/design.md` (new section reference)
- [x] Append to `specs/flows/solicitud-lifecycle.md` the response-upload + visibility-on-FINALIZADA step
- [x] Flip roadmap row 016 to `Done`

## Blockers

None.

[P] = can run in parallel
