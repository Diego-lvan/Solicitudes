# 003-catalog-forms — Catalog & Dynamic Forms — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-25 — Session 2 (full initiative implementation)
- Implemented: data models (`TipoSolicitud`, `FieldDefinition`) + initial migration; `tipos/constants.py` (`FieldType`, `MAX_FIELDS_PER_TIPO=50`, allow-lists for creator/responsible roles); `tipos/exceptions.py` (`TipoNotFound`, `TipoSlugConflict`, `TipoInUse`, `InvalidFieldDefinition`); `tipos/schemas.py` (`TipoSolicitudDTO`, `TipoSolicitudRow`, `FieldDefinitionDTO`, `CreateFieldInput`, `CreateTipoInput`, `UpdateTipoInput`) with Pydantic validators for SELECT options, FILE extensions, role allow-lists, mentor_exempt auto-clear, and 50-field cap; `formularios/schemas.py` (`FieldSnapshot`, `FormSnapshot`); `formularios/validators.py` (extension + size validators); `formularios/builder.py` (`build_django_form`, `field_attr_name`, `to_values_dict` for JSON-safe serialization).
- Implemented: `tipos/repositories/tipo/` interface + `OrmTipoRepository` (prefetch_related fields; transactional `update` with two-phase order rewrite to dodge `(tipo, order)` unique constraint collisions; auto-suffixed slug builder); `tipos/services/tipo_service/` interface + `DefaultTipoService` (rules: deactivate-vs-delete via `has_solicitudes`, `get_for_creator` defense-in-depth check, snapshot rejects inactive tipos); `tipos/dependencies.py` factories.
- Implemented: `tipos/forms/` (`TipoForm` + `FieldFormSet` of `FieldForm` with CSV parsing for options/extensions and per-field-type validation); `tipos/views/{list,create,detail,edit,delete}.py` (admin-only, Pydantic DTO crossing the form→service boundary); `tipos/urls.py`; `static/js/tipo_form.js` for cloning field rows.
- Implemented: templates (`list.html`, `form.html`, `_field_row.html`, `detail.html`, `confirm_deactivate.html`) — institutional UAZ green, table-hover, hidden columns at <md, mobile reflow at 320px verified via Playwright screenshots, Bootstrap Icons, WCAG-aware focus + labels.
- Implemented: `_shared/templatetags/role_display.py` (`role_label` filter for `CONTROL_ESCOLAR` → `Control Escolar`).
- Tests: `pytest` 197 pass total; new `solicitudes/` coverage = 11 repository + 12 service + 11 form + 16 builder + 15 view + 1 Tier 2 Playwright = 66 new tests.
- Quality gates: `ruff check solicitudes/` clean, `mypy solicitudes/` strict clean, `python manage.py check` clean.
- Visual: screenshots captured at 1280×900 desktop and 320×800 mobile for list/detail/create/edit; verified institutional look, no AI-style gradients, role labels render with spaces ("Control Escolar"), no horizontal scroll on mobile.
- pyproject.toml: extended ruff per-file-ignores (`N806`/`E501` for tests, `RUF012` for models layer); added `solicitudes` to coverage source.

## 2026-04-25 — Session 2 (sidebar layout + chip-style options editor)
- Added a role-aware home view at `/` (`_shared/views.py::home`): admins land on `/solicitudes/admin/tipos/`, every other authenticated role lands on `/auth/me`, anonymous bounces to `LOGIN_URL`. Replaced the unconditional `RedirectView` in `config/urls.py`. New tests: `_shared/tests/test_home_view.py` (6 cases — admin, four non-admin roles, anonymous).
- Replaced the top-bar "Tipos" link with a persistent left **sidebar** (`templates/components/sidebar.html`): sections `Inicio` / `Catálogo` (admin-only "Tipos de solicitud") / `Cuenta` (Mi perfil + Cerrar sesión). Below `lg`, the sidebar collapses and is reachable via a hamburger that opens the same component as a Bootstrap offcanvas drawer (`base.html`).
- Restyled the top navbar (`templates/components/nav.html`): brand on the left, user dropdown on the right with avatar + role label; anonymous users see a "Iniciar sesión" button.
- Restyled `/auth/me` (`templates/usuarios/me.html`) to match: avatar header, identity card with sectioned dl, in-page logout button (kept reachable for the Tier 2 auth golden path; sidebar offers a second route).
- Added **chip-style editor + live SELECT preview** for `options_csv` and `accepted_extensions_csv` (`tipos/_field_row.html` + `static/js/tipo_form.js`). Type, Enter or comma to add; backspace on empty input removes the last chip. The hidden CSV input stays the source of truth so the existing form/service code is unchanged. The SELECT preview renders a disabled `<select>` showing the current options (admin sees the live result of their input). The JS also drives field-type-aware visibility: the options cell is only shown for SELECT, the extensions cell only for FILE.
- Added a `role_label` template filter in `_shared/templatetags/role_display.py` (renders `CONTROL_ESCOLAR` → `Control Escolar`). Wired through the navbar, sidebar, and profile templates.
- CSS overhaul (`static/css/app.css`): UAZ green plumbed through Bootstrap variables (`--bs-primary`), sidebar layout, sticky behavior at `lg+`, chip + chip-input styling.
- Fixed two bugs caught only on visual: a multi-line `{# ... #}` Django comment leaking as visible text (Django comments are single-line; switched to `{% comment %}`), and a `<button hidden>` chip template that Bootstrap's CSS overrode (refactored chip rendering to build elements fully in JS).
- Updated E2E tests for the new UI: `test_auth_golden_path` scopes the logout click to `<main>` (the sidebar exposes a second link); `test_tipos_golden_path` types into the chip-input and presses Enter twice instead of filling the now-hidden CSV input.
- Tests: 210 passing total. Ruff clean. Mypy strict clean.

## 2026-04-25 — Session 2 (post-UX-review remediation)
- **Critical (renumber on delete):** popping a new mid-formset row in `tipo_form.js` now walks every surviving `.field-row` and rewrites the prefixed attributes (`name`, `id`, `for`, `aria-controls`, `data-options-for`, `data-form-index`) to a contiguous `0..n-1` sequence. Without this, deleting "row 1" of three new rows left a hole that Django's formset reads as "row missing", silently dropping every subsequent row's data. New helper `renumberRows()` is idempotent.
- **Important (order rewrite skips soft-deleted rows):** `rewriteOrderInputs` now ignores `row.hidden` rows so persisted `order` values run `0..n-1` after a saved-row delete; soft-deleted rows POST `DELETE=true` and `_collect_fields` skips them on the server.
- **Important (validator order):** moved `_check_max_chars_scope` after `_check_options` and `_check_extensions` in `CreateFieldInput` so the actionable shape error (e.g., "SELECT must define at least one option") surfaces first instead of the noisier stale-flag error.
- **Important (caret icon):** the collapse caret now toggles the icon class (`bi-chevron-down` ↔ `bi-chevron-right`) in JS instead of relying on a CSS rotate; visual state survives even with transforms disabled.
- **Important (test coverage):** added 7 new tests covering the bugs above and the gaps the reviewer flagged: `test_create_post_persists_three_fields_after_renumber`, `test_create_post_with_soft_deleted_row_compacts_orders` (Python view tests), `test_admin_can_delete_middle_row_without_data_loss` (Tier 2 e2e), and a dedicated `test_schemas.py` with 4 schema-validator tests (per-type rejection, accept on text types, None always valid, validator-order pin).
- **Suggestions:** seeders helper `_replace_fields` forwards `max_chars`; `_replace_fields` repository helper now imports `MAX_FIELDS_PER_TIPO` and asserts `offset > cap`; sidebar component accepts a `variant` arg so the offcanvas instance is announced as "Navegación móvil" vs "Navegación lateral" (reviewer flagged duplicate landmarks); `seed.py` replaced `✓` with `[done]` per CLAUDE.md no-emojis rule; MutationObserver gained `subtree: true` (forward-looking); schema test moved out of `test_tipo_repository.py` into its own `test_schemas.py`.
- Side fix: a fresh leak of a multiline `{# … #}` Django comment inside `components/sidebar.html` was rendering as visible text at the top of every authenticated page; switched to `{% comment %}` (this is the third time this exact bug has shown up — adding a lint check for multi-line `{# #}` is on the punch list).
- Tests: 132 passing (`solicitudes/` 73 + `_shared/` 59). Ruff clean, mypy strict clean, `manage.py check` clean.
- Visual verification at 1440×900 + 375×800: renumber after mid-row delete reflects in DOM (`fields-1-label === "Tercero"`, `TOTAL_FORMS=2`); caret icon class swaps correctly on toggle; preview re-renders to match.

## 2026-04-25 — Session 2 (per-type cell visibility + max_chars for text fields)
- Model: added `FieldDefinition.max_chars: PositiveIntegerField(null=True, blank=True)`. Edited `0001_initial.py` in place — no real data, dropped+rebuilt the tables (`make seed-fresh` reseeded cleanly).
- Schemas: `FieldDefinitionDTO`, `FieldSnapshot`, and `CreateFieldInput` gained `max_chars: int | None`. New Pydantic validator `_check_max_chars_scope` rejects `max_chars` set on non-TEXT/TEXTAREA types.
- `formularios/builder.py`: TEXT and TEXTAREA now use `max_length = snap.max_chars or default` (200 for TEXT, 2000 for TEXTAREA) instead of the previous hardcoded 200/unbounded. Other field types untouched.
- `tipos/forms/field_form.py`: added `max_chars` IntegerField (1..2000); renamed `max_size_mb` label to "Tamaño máx. del archivo (MB)" and added help text. `clean()` normalizes both fields per type — `max_size_mb` reset to 10 when not FILE; `max_chars` reset to None when not TEXT/TEXTAREA — so a stale value from the now-hidden input cannot reach the schema.
- Repository + service: persist + read + snapshot the new column.
- View helper `_collect_fields`: forwards `max_chars`.
- Template `_field_row.html`: replaced the always-on "Tamaño máx. (MB)" cell with two type-scoped cells declared via `data-shows-for="FILE"` and `data-shows-for="TEXT,TEXTAREA"`. Also added `data-shows-for="SELECT"` to the chip-options cell and `data-shows-for="FILE"` to the extension-multiselect cell, replacing the old per-class lookup in JS.
- `tipo_form.js`: simplified `initTypeToggle` to a generic `data-shows-for` reader (handles every per-type cell uniformly). Live preview's TEXT/TEXTAREA controls now set `maxlength` from `max_chars`.
- Tests: 9 new tests (5 form-level for the per-type clean normalization, 1 round-trip through the repo for `max_chars` on TEXT/TEXTAREA/NUMBER, 1 schema-validator rejection, 2 builder-level for `max_length` enforcement). Total: 73 passing in `solicitudes/`. Ruff clean, mypy strict clean.
- Visual verification at 1440×900 + 375×800: cell visibility correct for all 6 field types (TEXT/TEXTAREA → max_chars only, FILE → max_size + extensions, SELECT → options, NUMBER/DATE → neither). Preview's text input picks up `maxlength="12"` when admin sets max_chars to 12.

## 2026-04-25 — Session 2 (interactive preview + drop per-row chip preview)
- Preview controls (TEXT/TEXTAREA/NUMBER/DATE/SELECT/FILE) are no longer `disabled` — the admin can type, pick a date, choose a file, click through SELECT options. The controls have no `name` attribute so nothing is submitted.
- Removed the per-row "Vista previa del menú" block from `_field_row.html` (and its `renderPreview()` + `escapeHtml()` helpers in `tipo_form.js`) — it was redundant with the right-pane live preview that now shows the same select interactively.
- Updated the chip-input help text to point at the right pane.
- Visual verification at 1440×900 + 375×800: 0 disabled inputs/selects/textareas in the preview; SELECT and TEXT accept user interaction; `.chip-preview` no longer in DOM.

## 2026-04-25 — Session 2 (live preview pane, side-by-side at xl)
- `form.html`: wrapped the editor in `col-12 col-xl-7` and added an `<aside class="col-12 col-xl-5">` with a Bootstrap card hosting `#tipo-preview-body`. Below `xl` (1200px), the aside stacks below the editor — no separate template; a single layout serves both. Also fixed a leaked Django `{# ... #}` comment that was rendering as visible text inside `_field_row.html` (multiline `{# #}` is invalid; switched to `{% comment %}`).
- `app.css`: `.tipo-preview-sticky` is `position: sticky; top: 1rem` only at `min-width: 1200px`; on smaller widths it scrolls normally.
- `tipo_form.js`: added a `~80-line` live-preview renderer. It reads each visible row's state (label, type, required, placeholder, help_text, options, accepted extensions) and emits real Bootstrap controls (TEXT/TEXTAREA/NUMBER/DATE/SELECT/FILE) all `disabled`, plus the tipo's nombre/descripcion as a header. Updates fire on: any `input`/`change` inside `#field-rows` (delegated), nombre/descripcion edits, and a `MutationObserver(childList)` on `#field-rows` so add/delete/Sortable-reorder also re-render.
- Visual verification at 1440×900 + 375×800: preview pane sits to the right of the editor on desktop and shows the rendered form in real time; soft-deleted rows are excluded; SELECT options propagate; FILE `accept` reflects the chosen extensions; mobile reflows (no horizontal scroll, preview stacks below).
- Tests: 64 passing in `solicitudes/`. Ruff clean, `manage.py check` clean.

## 2026-04-25 — Session 2 (collapsible cards + drag-reorder, legend fix, placeholder copy)
- `field_form.py`: `order` is now `HiddenInput()` — the visible numeric "Orden" input is gone.
- `_field_row.html`: rebuilt the row as a Bootstrap card with a `card-header` summary (drag handle ≡, label preview, type badge, ↑/↓ buttons, delete) and a collapsible `card-body`. Header drives expand/collapse; trash button toggles the formset DELETE checkbox (kept off-screen) for existing rows or pops new rows from the DOM.
- `tipo_form.js`: vendored `Sortable.min.js` (1.15.6, 44 KB at `static/vendor/sortablejs/`); init Sortable on `#field-rows` with `handle: .field-drag-handle`. Added: per-row collapse toggle (auto-open for newly-added/empty rows, auto-collapse for filled ones), live header summary that mirrors `label`+`field_type`, ↑/↓ buttons that swap DOM siblings, hidden-input rewrite of `fields-N-order` on form submit so position-in-DOM is the persisted order. Add-button now collapses other rows to keep focus on the one being edited.
- `form.html`: legend "Roles que pueden crear solicitudes de este tipo" was rendering at ~24px because Bootstrap 5 reboot styles `<legend>` as a heading and `.form-label` doesn't reset `font-size`. Forced it back to label size with `fs-6 fw-normal mb-2 float-none w-auto p-0`.
- `field_form.py` (placeholder): label "Marcador de posición" → "Texto de ejemplo dentro del campo"; added inline placeholder example ("Ej. Juan Pérez García") and `help_text` explaining it's a hint, not a saved value. Template renders the help_text under the input.
- `tests-e2e/test_tipos_golden_path.py`: dropped the two `fields-N-order.fill(...)` calls — the JS rewrites order on submit, and Playwright can't `.fill()` a hidden input.
- Visual verification (Playwright in-container) at 1280×900 + 375×800: legend now 16px (matches other labels), `Orden` input not in DOM, collapse toggle works, ↑ button reorders correctly, mobile reflows with no horizontal scroll.
- Tests: 64 in `solicitudes/` passing. Ruff clean, mypy strict clean, `manage.py check` clean.

## 2026-04-25 — Session 2 (FILE extension multiselect)
- Replaced the chip-style typed input for "Extensiones aceptadas (FILE)" with a sectioned `btn-check` toggle multiselect. New constant `COMMON_FILE_EXTENSIONS` in `solicitudes/tipos/constants.py` groups 18 extensions into Documentos / Imágenes / Hojas de cálculo / Otros. New template tag `common_file_extensions` (`solicitudes/templatetags/tipos_tags.py`) exposes the groups.
- `_field_row.html`: replaced the FILE chip-input cell with a grouped toggle picker; the hidden `accepted_extensions_csv` input continues to be the wire format (no backend changes).
- `tipo_form.js`: added `initExtCell` — syncs hidden CSV ↔ checkbox state, renders unsaved-but-saved extensions under a "Personalizadas" group so legacy tipos don't silently drop values; `initTypeToggle` now toggles both `.chip-options-cell` (SELECT) and `.ext-multiselect-cell` (FILE) based on `field_type`.
- Visual verification via Playwright in-container at 1280×900 + 375×800: multiselect renders grouped, toggling .pdf/.docx/.png/.zip syncs the hidden CSV correctly, untoggled extensions stay out of the CSV.
- Tests: 210 still passing. Ruff clean, mypy strict clean, `manage.py check` clean.

## 2026-04-25 — Session 2 (dev seed command)
- Added `manage.py seed` command (`app/_shared/management/commands/seed.py`): auto-discovers a `seeders` module per installed app, orders runs by `DEPENDS_ON`, defaults to idempotent `update_or_create` (preserves manually-added rows), `--fresh` to wipe-and-rebuild, `--only <app_label>` for targeted runs, refuses `DEBUG=False` unless `--allow-prod`.
- Added `usuarios/seeders.py` (one user per role, matching the dev-login picker matriculas) and `solicitudes/seeders.py` (Constancia de Estudios + Solicitud de Cambio de Programa with their fields, declares `DEPENDS_ON = ["usuarios"]`).
- Added Makefile targets `make seed` (idempotent) and `make seed-fresh` (replace seeded rows). Tested live — `make seed-fresh` produces 5 users + 2 tipos + 6 fields.
- Tests: `_shared/tests/test_seed_command.py` — 7 tests (creates, idempotency, fresh preserves handmade rows, --only, --only unknown, refuses DEBUG=False, --allow-prod). Total suite: 204 passing. Ruff + mypy clean.

## 2026-04-25 — Session 2 (post-review remediation)
- Code-reviewer agent reported 0 Critical / 4 Important / 5 Suggestions. Addressed all four Important items:
  1. Removed `TipoService.delete` (it silently soft-deleted, conflicting with the docstring contract). `deactivate` is now the only soft-delete entry point with a docstring explaining hard-delete is intentionally absent for catalog tombstones. Removed the two delete-related service tests.
  2. Plumbed `responsible_role` through `TipoService.list_for_admin` and the repository's SQL filter; deleted the in-memory list comprehension in `TipoListView`. Added view test `test_list_filters_by_responsible_role`.
  3. Edit view's POST handler now wraps `service.get_for_admin(tipo_id)` in `try/except AppError`, redirecting to the list with a flash on stale ids.
  4. Removed silent `if not sub.is_valid(): continue` in `_collect_fields`; added a docstring stating the post-`formset.is_valid()` precondition.
- Tests: 197 still pass after the changes (one added, two removed). Ruff clean, mypy strict clean.
- Follow-up code-reviewer pass: **Ready to proceed.**

## 2026-04-25 — Session 2 (App skeleton)
- Implemented: created `app/solicitudes/` package — `__init__.py`, `apps.py` (`SolicitudesConfig`), `urls.py` mounting `admin/tipos/` under `app_name="solicitudes"`. Stubbed `tipos/urls.py` with `app_name="tipos"` and an empty urlpatterns list (views wired in later sections). Created empty `__init__.py` for all sub-packages: `models/`, `tipos/{forms,repositories/tipo,services/tipo_service,views,tests}/`, `formularios/{,tests}/`, `tests/`, `migrations/`. Registered `solicitudes` in `INSTALLED_APPS` (config/settings/base.py). Wired `path("solicitudes/", include(...))` in `config/urls.py`.
- OQ resolutions agreed with user before starting: OQ-003-1 → labels (and field_type, options, etc.) editable freely after first solicitud; snapshot is the source of truth for historical records. OQ-003-3 → max 50 fields per tipo. mentor_exempt auto-cleared on edit when requires_payment flips false.
- Tests: `python manage.py check` → "System check identified no issues (0 silenced)".

## 2026-04-25
- Initiative directory created (stub)
- Plan, status, and changelog files created as drafts pending `/brainstorm` + `/plan`
- Plan filled in: `TipoSolicitud` + `FieldDefinition` models, `creator_roles` (set) + `responsible_role` (single), per-tipo `requires_payment` and `mentor_exempt` flags, admin CRUD, dynamic form-builder + `FormSnapshot` consumed by 004. Open: field label editability after first solicitud (OQ-003-1), max fields per tipo (OQ-003-3).
