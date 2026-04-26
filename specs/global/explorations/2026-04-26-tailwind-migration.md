# Tailwind v4 Frontend Migration — Requirements

## Purpose

Replace the Bootstrap 5 frontend with Tailwind CSS v4 across the entire app, adopt a modern monochrome admin aesthetic (Vercel/shadcn-style), and update the project's frontend-design skill and related documentation to match. The current Bootstrap-based UI reads as a generic 2010-era admin panel; the system needs a contemporary, premium feel suitable for a modern academic platform without losing any functionality, accessibility guarantees, or es-MX localization.

This is cross-cutting (touches every Django app's templates, the build pipeline, and multiple `.claude/` artifacts), which is why it lives under `global/explorations/` until `/plan` decides whether to consolidate it into a `shared/frontend/` requirements home or treat it as a one-shot infrastructure initiative. Recommended placement: keep it as an infrastructure-class initiative under `specs/planning/015-tailwind-migration/` and not promote to a feature folder.

## User stories

- **As a user (student / faculty / admin), I want the app to look modern and premium**, so that I trust the institution and find the interface pleasant to work in daily.
  - **Acceptance:** every page rendered at 1280×900 reads as visually consistent with Vercel / shadcn / Linear-tier admin tooling — pure monochrome, hairline borders, Inter typography, mid radius, generous-but-dense spacing.
  - **Acceptance:** no decorative brand color appears in the chrome; all color in the UI carries semantic meaning (status badges, errors, focus, links).
  - **Acceptance:** primary actions render as `zinc-900` solid buttons with white text; the focus ring is `zinc-950` with `outline-offset: 2px`.
  - **Acceptance:** all body text uses Inter (self-hosted), with `font-feature-settings: "cv02","cv03","cv04","cv11"` and slight negative tracking.

- **As a user**, I want every existing feature to keep working exactly as before, so that the redesign is a pure visual/structural upgrade and not a regression.
  - **Acceptance:** every interactive widget shipped today still works: modals, dropdowns, offcanvas/sidebar, collapse, tooltips, toasts, the chip-style options input, the field-row drag/drop with collapse, the tipo-form live preview pane, sidebar+offcanvas mobile drawer.
  - **Acceptance:** all existing form-submission, validation, and error-rendering behavior is preserved.
  - **Acceptance:** all existing Django `Client`-level tests continue to pass without behavioral changes.
  - **Acceptance:** all Tier-2 Playwright golden-path E2E flows (login, create solicitud, file upload, revision, mentor catalog, reports) pass.

- **As a developer (you), I want a single, coherent design system documented in the frontend-design skill**, so that future templates ship with consistent look-and-feel without re-deriving the rules each time.
  - **Acceptance:** `.claude/skills/frontend-design/SKILL.md` is rewritten end-to-end to teach Tailwind v4 + Alpine.js + the new component partials, with copy-paste-ready Django snippets for each canonical component.
  - **Acceptance:** the skill includes the canonical `app.css` token block (`@theme` directive) as the single source of truth for design tokens.
  - **Acceptance:** any other doc that references Bootstrap (`CLAUDE.md`, `.claude/rules/django.md`, `django-patterns/forms.md`, `django-patterns/platform.md`, `specs/global/architecture.md`, `specs/global/requirements.md` if applicable) is updated.

- **As a developer**, I want the Tailwind build to run inside the existing Docker dev stack with no Node prerequisite on my host, so that `make dev` continues to be the only command I need.
  - **Acceptance:** the Tailwind standalone CLI binary is installed in the `web` Docker image; no `node`, `npm`, or sidecar container is added.
  - **Acceptance:** `docker-compose.dev.yml` runs `tailwindcss --watch` as a background process inside `web` so CSS rebuilds on template/CSS changes without manual intervention.
  - **Acceptance:** `make css` produces a one-shot production build; CI / production builds use this path.

- **As a user on mobile (320px wide) or at 200% browser zoom**, I want the redesigned UI to remain fully usable, so that accessibility is not regressed.
  - **Acceptance:** every page reflows correctly at 320×800 with no horizontal scroll except inside `.overflow-x-auto` table wrappers.
  - **Acceptance:** every page passes WCAG 2.2 AA at 200% zoom.

- **As any user (including screen-reader users)**, I want accessibility to be at least as good as today, so that the institution remains compliant.
  - **Acceptance:** WCAG 2.2 AA contrast (4.5:1 body, 3:1 large/UI) on every page.
  - **Acceptance:** every input still has a `<label>`; errors still associate via `aria-describedby`; skip-to-content link still present; `aria-current="page"` on active nav.
  - **Acceptance:** every interactive element has a visible focus ring; touch targets ≥44×44 (24×24 hard floor per SC 2.5.8).
  - **Acceptance:** `prefers-reduced-motion` is respected — no non-essential animation when the user prefers reduced motion.

## Constraints

- **Single-developer migration.** No team blocked, no parallel feature work in the affected paths — pick the strategy that yields the cleanest end state, not the safest incremental rollout.
- **Atomic deploy.** This is a server-rendered Django app behind nginx; no feature flag is required. The whole UI flips on merge.
- **No backend changes.** Views, services, repositories, models, forms (the `Form` classes — their HTML rendering may change), URL conf, middleware: untouched. This is visual + JS-equivalence only.
- **WeasyPrint PDF templates are out of scope.** Print is a separate medium; PDFs continue to use their own CSS in `app/_shared/pdf/` (or wherever they live). Tailwind has no value there.
- **No feature flag, no dark mode, no new features.** Strictly migration + redesign.
- **`code_example/` is excluded.** It's deprecated reference material per CLAUDE.md.
- **All user-facing copy stays in Spanish.** No copy changes.
- **es-MX locale conventions preserved** — date `d/m/Y`, currency `MXN`, number `1,234.56`, names as three fields.
- **No external CDNs in production.** Inter font self-hosted under `static/fonts/`; Lucide SVGs vendored under `static/vendor/lucide/`. Tailwind output is a static file generated at build time.

## Non-goals

- No backend refactor of any kind. No migration of forms to django-crispy or alternatives. No introduction of HTMX, React, or any other framework.
- No new features. No new pages. No copy changes. No new permissions or roles.
- No changes to WeasyPrint PDF templates.
- No dark mode (deferred indefinitely).
- No changes to the test infrastructure beyond updating any test that asserts on Bootstrap class names (those become Tailwind class names) and adding the visual-snapshot Playwright sweep listed below.
- No work in `code_example/`.
- No introduction of TypeScript, no JS bundler beyond the Tailwind binary, no PostCSS plugins beyond what Tailwind v4 ships natively.
- No npm / Node.js install on the developer host or in CI.
- No introduction of a third-party Tailwind component library (Flowbite, Preline, daisyUI). Components are hand-rolled as Django partials following shadcn design tokens. Preline may be referenced as inspiration for future complex widgets.

## Related modules

- → `app/templates/_shared/` — base templates and shared partials.
- → `app/templates/components/` — shared component partials (sidebar, breadcrumbs, badges, chip-input, field-row, etc.).
- → `app/templates/usuarios/` — user templates (login picker, profile if present).
- → `app/templates/solicitudes/` — the largest surface (~21 templates: list/detail/create/revision/tipos/formularios/preview).
- → `app/templates/notificaciones/` — notification list/detail.
- → `app/templates/mentores/` — mentor catalog templates.
- → `app/templates/reportes/` — dashboard + exports.
- → `app/static/css/app.css` — replaced with Tailwind input file.
- → `app/static/js/app.js`, `app/static/js/tipo_form.js` — adapted for Alpine.js where Bootstrap JS was used.
- → `app/static/vendor/bootstrap/`, `app/static/vendor/bootstrap-icons/` — deleted.
- → `app/static/vendor/sortablejs/` — kept (used by field-row drag/drop).
- → `app/static/vendor/lucide/` — **new**; vendored Lucide SVG sprite + individual SVGs.
- → `app/static/fonts/` — **new**; self-hosted Inter font files.
- → `app/_shared/templatetags/` — **new or extended**; `{% lucide %}` template tag.
- → `Dockerfile` — install Tailwind standalone binary + add font directory.
- → `docker-compose.dev.yml` — run `tailwindcss --watch` alongside `runserver`.
- → `Makefile` — `make css`, `make css-watch` targets.
- → `.gitignore` — ignore generated `app/static/css/app.build.css`.
- → `.claude/skills/frontend-design/SKILL.md` — full rewrite for Tailwind/Alpine/shadcn.
- → `.claude/skills/django-patterns/forms.md` — update form examples.
- → `.claude/skills/django-patterns/platform.md` — review for Bootstrap class references.
- → `CLAUDE.md` — tech stack section update (Bootstrap 5 → Tailwind v4 + Alpine.js).
- → `.claude/rules/django.md` — review for Bootstrap class references.
- → `specs/global/architecture.md` — Tech Stack table: Rendering row updated.
- → `specs/global/requirements.md` — review for Bootstrap mentions.

## Open questions

(All resolvable inside `plan.md`; none block the spec.)

- Exact list of "golden URLs" for the Playwright visual-snapshot sweep — derived from the URL conf during planning.
- Whether any test currently asserts on Bootstrap class names (e.g., `assertContains(response, "btn-primary")`). Plan needs an audit pass and a list of files to update.
- Whether the existing `app/templates/_shared/components` partials (if any) carry behavior that would be lost in re-write — verified during planning by reading each component file.
- Whether `LiveServerTestCase` / `pytest-playwright` snapshot baselines should be checked into git — propose: yes, in `app/tests-e2e/__snapshots__/` with a Makefile target to regenerate.

## Decisions locked from brainstorm (reference for `plan.md`)

These are not requirements but design decisions already made; they document the WHAT enough that `/plan` can encode the HOW:

- **Aesthetic:** Vercel/shadcn pure monochrome. `zinc-950` text, `zinc-900` primary buttons, `zinc-200` hairline borders, **no decorative accent hue**. Status colors carry all chromatic meaning.
- **Tailwind:** v4 (CSS-first config via `@theme` in `app.css`).
- **Build pipeline:** Tailwind standalone CLI binary, installed in the `web` image, run as a background watcher in dev compose. No Node, no sidecar container.
- **JS framework:** Alpine.js (~15kb) for declarative interactivity. SortableJS retained for drag/drop. Bootstrap JS deleted.
- **Component approach:** hand-rolled Django partials in `app/templates/components/` following shadcn design tokens. No third-party Tailwind component library.
- **Iconography:** Lucide (vendored SVG sprite + per-icon files), invoked via `{% lucide "name" class="..." %}` template tag. Bootstrap-Icons deleted.
- **Font:** Inter, self-hosted, with stylistic-set features enabled.
- **Migration strategy:** big-bang. Single feature branch, single PR, Bootstrap deleted in the same PR.
- **WeasyPrint PDFs:** untouched.
- **Status palette:** Tailwind `emerald-600` / `amber-600` / `rose-600` / `sky-600` / `zinc-500`.
- **Radius:** `rounded-md` (6px) default; `rounded-lg` (8px) for cards and modals.
- **Elevation:** `shadow-sm` only on overlays / modals. Cards rely on hairline borders.
