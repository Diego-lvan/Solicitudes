# 015 — Tailwind v4 Frontend Migration — Status

**Status:** Not Started
**Last updated:** 2026-04-26

## Checklist

### Build pipeline (foundation — must finish before anything else)
- [ ] Add Tailwind standalone CLI install to `Dockerfile` (`TAILWIND_VERSION` ARG, download binary, chmod)
- [ ] Update `docker-compose.dev.yml` `web` service `command:` to run `tailwindcss --watch` alongside `runserver`
- [ ] Add `make css` and `make css-watch` targets to `Makefile`
- [ ] Add `app/static/css/app.build.css` to `.gitignore`
- [ ] Write initial `app/static/css/app.css` with `@import "tailwindcss";`, `@theme` token block, `@font-face` for Inter, `@layer base` block, and `@source` directives
- [ ] Verify `make css` produces a non-empty `app.build.css` from a fresh container
- [ ] Verify `make css-watch` rebuilds on `*.html` change

### Vendor assets
- [ ] [P] Vendor Inter variable font under `app/static/fonts/Inter/InterVariable.woff2`
- [ ] [P] Vendor Alpine.js v3 (`alpine.min.js`) under `app/static/vendor/alpinejs/`
- [ ] [P] Vendor `@alpinejs/collapse` plugin under `app/static/vendor/alpinejs/`
- [ ] [P] Vendor `@alpinejs/focus` plugin under `app/static/vendor/alpinejs/`
- [ ] [P] Audit Bootstrap-Icons usage across all templates → produce `bi-* → lucide-*` mapping table
- [ ] [P] Vendor needed Lucide SVGs under `app/static/vendor/lucide/icons/` and build `sprite.svg`

### Lucide template tag
- [ ] Create `app/_shared/templatetags/__init__.py` if missing
- [ ] Create `app/_shared/templatetags/lucide.py` with `{% lucide %}` simple_tag
- [ ] Add unit test for the template tag

### Components (must finish before per-app templates — everyone depends)
- [ ] `components/lucide_sprite.html` — inlined SVG sprite (loaded once in base.html)
- [ ] `components/button.html` — variants (primary/outline/ghost/destructive) × sizes (sm/md/lg)
- [ ] `components/card.html` — header/body/footer slots
- [ ] `components/input.html` — text input + label + hint + error association via `aria-describedby`
- [ ] `components/select.html`
- [ ] `components/textarea.html`
- [ ] `components/checkbox.html`
- [ ] `components/radio.html`
- [ ] `components/badge_estado.html` — refactor existing
- [ ] `components/breadcrumbs.html` — refactor existing with `aria-current="page"`
- [ ] `components/sidebar.html` — refactor existing
- [ ] `components/offcanvas_drawer.html` — Alpine-driven mobile sidebar
- [ ] `components/modal.html` — Alpine-driven (prefer `<dialog>` element with Alpine state)
- [ ] `components/dropdown.html` — Alpine `@click.outside`
- [ ] `components/toast.html` — Alpine + `aria-live="polite"`
- [ ] `components/alert.html` — static alert / banner with `role="alert"` for error variant
- [ ] `components/pagination.html` — refactor existing
- [ ] `components/empty_state.html` — icon + sentence + CTA
- [ ] `components/chip_input.html` — refactor existing chip-style input
- [ ] `components/field_row.html` — refactor draggable collapsible field row (Alpine + SortableJS)
- [ ] `components/tipo_preview.html` — refactor live preview panel
- [ ] `components/navbar.html` — top bar with logo, user menu (dropdown)

### base.html
- [ ] Rewrite `app/templates/base.html` head + body shell using Tailwind utilities, Alpine, Lucide
- [ ] Replace `visually-hidden-focusable` skip link with Tailwind `sr-only focus:not-sr-only` pattern
- [ ] Confirm `[x-cloak]` style is in `app.css` `@layer base`

### JS adaptation
- [ ] Adapt `app/static/js/app.js` — replace any Bootstrap JS API calls with Alpine equivalents or remove
- [ ] Adapt `app/static/js/tipo_form.js` — preserve SortableJS calls; replace any Bootstrap JS API with Alpine equivalents
- [ ] Add unit/integration coverage for any chip-input or field-row JS that lacks it

### Per-app template rewrites (parallel after components are done)
- [ ] [P] Rewrite `_shared/` templates (2 files: error pages)
- [ ] [P] Rewrite `usuarios/` templates (2 files: login picker, profile)
- [ ] [P] Rewrite `notificaciones/` templates (4 files)
- [ ] [P] Rewrite `mentores/` templates (7 files)
- [ ] [P] Rewrite `reportes/` templates (4 files)
- [ ] Rewrite `solicitudes/` templates (21 files — biggest surface; sequence internally: list/detail → create → revision → tipos → formularios → preview)

### Test updates
- [ ] Audit `app/**/tests/` for assertions on Bootstrap class names (`btn-`, `card`, `navbar`, `offcanvas`, `modal`, `alert-`, `badge-`); update to role/text/data-test selectors where assertions are fragile
- [ ] Add `data-test="..."` attributes to elements where tests need stable selectors
- [ ] Run full Tier-1 suite — must be green
- [ ] Add `app/tests-e2e/test_visual_snapshot.py` with the golden URLs list at 1280×900 and 320×800
- [ ] Generate and commit baseline screenshots under `app/tests-e2e/__snapshots__/`
- [ ] Run full Tier-2 suite — must be green

### Skill / doc updates (after templates are done — they reference final state)
- [ ] Rewrite `.claude/skills/frontend-design/SKILL.md` end-to-end for Tailwind v4 + Alpine.js + shadcn aesthetic (~400 lines target)
- [ ] Update `.claude/skills/django-patterns/forms.md` — form examples migrated
- [ ] Audit `.claude/skills/django-patterns/platform.md` for Bootstrap references; update
- [ ] Audit `.claude/rules/django.md` for Bootstrap references; update
- [ ] Update `CLAUDE.md` Tech Stack section: Bootstrap 5 → Tailwind v4 + Alpine.js; mention `make css-watch`
- [ ] Update `specs/global/architecture.md` Tech Stack table: Rendering row
- [ ] Audit `specs/global/requirements.md` for Bootstrap references; update

### Cleanup (final commit before merge)
- [ ] Delete `app/static/vendor/bootstrap/`
- [ ] Delete `app/static/vendor/bootstrap-icons/`
- [ ] Confirm no template references `vendor/bootstrap*`
- [ ] Confirm `python manage.py collectstatic --no-input` succeeds
- [ ] Confirm a sample WeasyPrint PDF still renders identically to pre-migration (visual diff)
- [ ] Final Playwright sweep at 1280×900 + 320×800 across the golden URL list
- [ ] Manual smoke of all interactive widgets (modal, dropdown, offcanvas, collapse, toast, chip-input, field-row drag, tipo preview)

### Accessibility verification
- [ ] [P] axe-core run on every page in the golden URL list — zero serious / critical violations
- [ ] [P] Manual keyboard-only navigation pass on the create-solicitud flow
- [ ] [P] Manual screen-reader pass (VoiceOver) on the create-solicitud flow
- [ ] [P] 200% browser zoom on every page in the golden URL list — no loss of function
- [ ] [P] 320px viewport on every page in the golden URL list — no horizontal scroll outside `.overflow-x-auto`

### E2E
- [ ] Tier 1 (Client): _None new._ Existing Tier 1 suite passes as regression gate.
- [ ] Tier 2 (browser/Playwright): visual snapshot sweep — golden URLs list at 1280×900 + 320×800
- [ ] Tier 2 (browser/Playwright): smoke flow — student creates and submits a solicitud
- [ ] Tier 2 (browser/Playwright): smoke flow — admin reviews and approves a solicitud
- [ ] Tier 2 (browser/Playwright): smoke flow — interactive widgets (offcanvas, modal, dropdown, chip-input, field-row drag, tipo preview)

## Blockers

None.

[P] = can run in parallel
