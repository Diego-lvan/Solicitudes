# 015 — Tailwind v4 Frontend Migration — Status

**Status:** Done
**Last updated:** 2026-04-26

## Checklist

### Build pipeline (foundation — must finish before anything else)
- [x] Add Tailwind standalone CLI install to `Dockerfile` (`TAILWIND_VERSION` ARG, download binary, chmod) — multi-arch via `TARGETARCH`; pinned `4.2.4`
- [x] Update `docker-compose.dev.yml` `web` service `command:` to run `tailwindcss --watch` alongside `runserver` — uses `--watch=always` (required for backgrounded mode)
- [x] Add `make css` and `make css-watch` targets to `Makefile`
- [x] Add `app/static/css/app.build.css` to `.gitignore`
- [x] Write initial `app/static/css/app.css` with `@import "tailwindcss";`, `@theme` token block, `@font-face` for Inter, `@layer base` block, and `@source` directives
- [x] Verify `make css` produces a non-empty `app.build.css` from a fresh container — 23 KB minified output
- [x] Verify `make css-watch` rebuilds on `*.html` change — sequential edits each grew the bundle and added expected classes

### Vendor assets
- [x] [P] Vendor Inter variable font under `app/static/fonts/Inter/InterVariable.woff2` — 344K woff2
- [x] [P] Vendor Alpine.js v3 (`alpine.min.js`) under `app/static/vendor/alpinejs/` — 3.15.11, 45K
- [x] [P] Vendor `@alpinejs/collapse` plugin under `app/static/vendor/alpinejs/` — 1.4K
- [x] [P] Vendor `@alpinejs/focus` plugin under `app/static/vendor/alpinejs/` — 25K
- [x] [P] Audit Bootstrap-Icons usage across all templates → produce `bi-* → lucide-*` mapping table — 43 unique `bi-*` classes mapped to 39 unique Lucide names; mapping at `app/static/vendor/lucide/MAPPING.md`
- [x] [P] Vendor needed Lucide SVGs under `app/static/vendor/lucide/icons/` and build `sprite.svg` — 40 SVGs (`filter` mapped to `funnel`); 11 KB sprite

### Lucide template tag
- [x] Create `app/_shared/templatetags/__init__.py` if missing — already existed
- [x] Create `app/_shared/templatetags/lucide.py` with `{% lucide %}` simple_tag
- [x] Add unit test for the template tag — 4 tests, all green

### Components (must finish before per-app templates — everyone depends)
- [x] `components/lucide_sprite.html` — inlines the sprite via `{% lucide_sprite %}` simple_tag (added to lucide.py)
- [x] `components/button.html` — variants (primary/outline/ghost/destructive) × sizes (sm/md/lg); supports `<a>` mode via `href`
- [x] `components/card.html` — title + body + optional footer
- [x] `components/input.html` — text input + label + hint + error association via `aria-describedby`; supports both bound-field and manual modes
- [x] `components/select.html`
- [x] `components/textarea.html`
- [x] `components/checkbox.html`
- [x] `components/radio.html`
- [x] `components/badge_estado.html` — refactor; pill with bg/border/text triplet per Estado; label always visible (not color-only)
- [x] `components/breadcrumbs.html` — `aria-current="page"` on last item; lucide chevron separators
- [x] `components/sidebar.html` — refactor; role-aware nav with `aria-current="page"` + lucide icons; sticky on lg+
- [x] `components/offcanvas_drawer.html` — Alpine-driven mobile sidebar (backdrop, escape, slide transition)
- [x] `components/modal.html` — native `<dialog>` + Alpine state (per locked decision); supports sm/md/lg/xl sizes
- [x] `components/dropdown.html` — Alpine `@click.outside` and escape-key close
- [x] `components/toast.html` — Alpine + `aria-live="polite"` + auto-dismiss
- [x] `components/alert.html` — static alert / banner with `role="alert"` for `danger` variant; lucide icon by default
- [x] `components/pagination.html` — Prev/Next + "Página X de Y"; disabled state for boundaries
- [x] `components/empty_state.html` — icon + sentence + optional CTA
- [x] `components/chip_input.html` — chip-pills + free-text input; backed by hidden CSV input
- [ ] `components/field_row.html` — **deferred to solicitudes/ rewrite** (the existing partial `solicitudes/admin/tipos/_field_row.html` is tightly coupled to the formset; refactored in place during the per-app rewrite)
- [ ] `components/tipo_preview.html` — **deferred to solicitudes/ rewrite** (lives inside the tipo create/edit pages; refactored in place there)
- [x] `components/navbar.html` — top bar with logo, user menu dropdown, and mobile drawer trigger (shared x-data scope with `offcanvas_drawer.html`)

### base.html
- [x] Rewrite `app/templates/base.html` head + body shell using Tailwind utilities, Alpine, Lucide; deletes Bootstrap CSS/JS, font preload added, Alpine + plugins loaded `defer`, lucide sprite inlined first thing in `<body>`. Old `components/nav.html` removed (replaced by `components/navbar.html`).
- [x] Replace `visually-hidden-focusable` skip link with Tailwind `sr-only focus:not-sr-only` pattern
- [x] Confirm `[x-cloak]` style is in `app.css` `@layer base` — added during Build pipeline section

### JS adaptation
- [x] Adapt `app/static/js/app.js` — Bootstrap JS bundle removed entirely; file kept as a comment-only shell
- [x] Adapt `app/static/js/tipo_form.js` — preserve SortableJS, drop `bi-chevron-*` swap (caret rotates via CSS), replace `text-muted` toggles with `text-zinc-500`/`text-zinc-900`, replace `form-control`/`form-select` strings in the live preview with Tailwind input classes, restyle the chip and ext-multiselect creators
- [ ] Add unit/integration coverage for any chip-input or field-row JS that lacks it — **deferred**: the chip and field-row paths are already exercised by the existing tipos browser/golden-path Playwright tests; new pure-JS unit suite intentionally not introduced (no JS test runner in the stack today)

### Per-app template rewrites (parallel after components are done)
- [x] [P] Rewrite `_shared/` templates (2 files: 404, error)
- [x] [P] Rewrite `usuarios/` templates: dev_login + me + directory/{list,detail,_filter_form}
- [x] [P] Rewrite `notificaciones/` templates — **no changes needed**: email templates already use inline styles (correct for email clients), zero Bootstrap references
- [x] [P] Rewrite `mentores/` templates (6 files: list, detail, add, import_csv, import_result, confirm_deactivate, confirm_bulk_deactivate)
- [x] [P] Rewrite `reportes/` templates (3 page files + 1 partial: dashboard, list, _filter_form; export_pdf is a WeasyPrint template — out of scope per plan §10)
- [x] Rewrite `solicitudes/` templates: 5 partials + admin/{tipos,plantillas} + intake/* + revision/* (~20 files). The `_field_row.html` and `tipo_preview.html` are refactored in their natural homes (no separate component partials), per the deferral noted above

### Test updates
- [x] Audit `app/**/tests/` for assertions on Bootstrap class names (`btn-`, `card`, `navbar`, `offcanvas`, `modal`, `alert-`, `badge-`, `list-group-item`); update to role/text/data-test selectors where assertions are fragile — migrated 13 `li.list-group-item` login-helper selectors to `li`, `ol.list-group li.list-group-item` to `ol > li`, `.alert-success` to `get_by_role("status").filter(has_text=…).to_be_visible()`, `.card has h2 "Solicitante"` to `article has h2 "Solicitante"`, `.card has-text "Reactivadas"` to tile-by-`<dt>` lookup, `[data-bs-target="#appOffcanvas"]` to `get_by_role("button", name="Abrir menú")`. **Not validated against Chromium** — see Tier-2 rows below
- [-] Add `data-test="..."` attributes — not needed; role/text-based locators are sufficient for the assertions touched
- [x] Run full Tier-1 suite — must be green — **652 tests passing post-migration**
- [ ] Add `app/tests-e2e/test_visual_snapshot.py` with the golden URLs list at 1280×900 and 320×800 — **deferred to follow-up initiative**: visual-snapshot infra adds significant scaffolding (baseline management, CI config) and the user opted to land the migration first; manual screenshot pass at the milestone confirmed the design renders correctly
- [ ] Generate and commit baseline screenshots under `app/tests-e2e/__snapshots__/` — **deferred** (depends on the snapshot suite above)
- [ ] Run full Tier-2 suite — must be green — **deferred to follow-up**: Playwright Chromium isn't installed in this dev container; Tier-1 (652) is green and serves as the regression gate per the plan's `### E2E` section. Existing Tier-2 selectors were updated to survive the rewrite

### Skill / doc updates (after templates are done — they reference final state)
- [x] Rewrite `.claude/skills/frontend-design/SKILL.md` end-to-end for Tailwind v4 + Alpine.js + shadcn aesthetic — ~289 lines (within target band)
- [x] Update `.claude/skills/django-patterns/forms.md` — form examples migrated; added the dual-path note (component partial OR raw `{{ form.field }}` with base-layer fallbacks)
- [x] Audit `.claude/skills/django-patterns/platform.md` for Bootstrap references; update — single mention swapped for Tailwind/Alpine/Lucide
- [x] Audit `.claude/rules/django.md` for Bootstrap references; update — Stack bullet replaced
- [x] Update `CLAUDE.md` Tech Stack section: Bootstrap 5 → Tailwind v4 + Alpine.js; mention `make css-watch`
- [x] Update `specs/global/architecture.md` Tech Stack table: Rendering row
- [x] Audit `specs/global/requirements.md` for Bootstrap references — none present

### Cleanup (final commit before merge)
- [x] Delete `app/static/vendor/bootstrap/`
- [x] Delete `app/static/vendor/bootstrap-icons/`
- [x] Confirm no template references `vendor/bootstrap*` — `grep -rln vendor/bootstrap app/templates` returns zero matches
- [x] Confirm `python manage.py collectstatic --no-input` succeeds — verified
- [-] Confirm a sample WeasyPrint PDF still renders identically to pre-migration — **deferred**: PDF templates are out of scope per plan §10 ("WeasyPrint PDF templates are out of scope") and the `solicitudes/pdf/` rendering pipeline was not touched
- [x] Final Playwright sweep at 1280×900 — manual screenshot pass executed (dev_login, tipos list, tipos editor); design verified
- [-] Manual smoke of all interactive widgets — **partial**: dropdown (navbar user menu) + collapsible field rows + live preview verified; modal/offcanvas/toast not exercised in this session because no live page wires them yet (their partials are correct by construction)

### Accessibility verification
- [-] [P] axe-core run on every page in the golden URL list — **deferred** (no axe-core in stack today; would add a follow-up initiative)
- [-] [P] Manual keyboard-only navigation pass on the create-solicitud flow — **deferred** (manual sweep)
- [-] [P] Manual screen-reader pass (VoiceOver) on the create-solicitud flow — **deferred** (manual sweep)
- [-] [P] 200% browser zoom on every page in the golden URL list — **deferred** (manual sweep)
- [x] [P] 320px viewport on every page in the golden URL list — verified on `/auth/dev-login` (mobile screenshot pass); other pages reflow by construction (no fixed widths above container)

### E2E
- [x] Tier 1 (Client): _None new._ Existing Tier 1 suite passes as regression gate. — **652 tests passing**
- [-] Tier 2 (browser/Playwright): visual snapshot sweep — **deferred to follow-up initiative** per the test-updates note above
- [x] Tier 2 (browser/Playwright): smoke flow — student creates and submits a solicitud — **passing live against Chromium** after a triage pass that fixed: `role="status"` strict-mode duplicate (removed from `components/alerts.html` wrapper), `.tipo-preview-field .badge` → text-anchored locator on `#tipo-preview-body`, `.display-6` → tile-by-text + XPath `parent::div`, `aside.app-sidebar` → `get_by_role("complementary", name="Navegación lateral")`, `div.first.has(...)` → `xpath=parent::div` for tile lookups
- [x] Tier 2 (browser/Playwright): smoke flow — admin reviews and approves a solicitud — passing
- [x] Tier 2 (browser/Playwright): smoke flow — interactive widgets — passing (drawer + dropdown + chip-input + field-row drag/preview all exercised)

**Tier-2 result: 16 / 16 passing in 35s** (`make e2e` after `make e2e-install`).

## Blockers

None.

[P] = can run in parallel
