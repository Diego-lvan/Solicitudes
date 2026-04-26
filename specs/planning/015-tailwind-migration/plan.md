# 015 — Tailwind v4 Frontend Migration

## Summary

Replace Bootstrap 5 with Tailwind CSS v4 across the entire frontend, adopt a Vercel/shadcn-style pure-monochrome aesthetic, and rewrite all 46 Django templates against hand-rolled component partials backed by Alpine.js. Set up a Tailwind standalone-CLI build pipeline inside the existing `web` Docker container with no host Node prerequisite. Update the `frontend-design` skill end-to-end and every other doc / rule that references Bootstrap. Strict big-bang migration on a single feature branch; single merge.

This is an infrastructure-class initiative that spans all apps' template directories. There is no per-feature `requirements.md`; the initiative-level draft requirements live at `specs/global/explorations/2026-04-26-tailwind-migration.md`.

## Depends on

- **001** — base templates, `app/static/css/app.css`, Dockerfile, docker-compose.dev.yml, Makefile.
- **002 → 014** — every shipped template uses the existing layout established by these initiatives. No code dependency, but every template file produced by them is touched here.

This blocks (during the in-progress window): **013** and **014** template work — they should not start until 015 merges, otherwise their templates would need a second rewrite.

## Affected Apps / Modules

- `app/templates/` — all 46 `*.html` files rewritten.
  - `_shared/` (2 files), `components/` (5 files), `usuarios/` (2), `solicitudes/` (21), `notificaciones/` (4), `mentores/` (7), `reportes/` (4), `base.html` (1).
- `app/static/css/app.css` — replaced (becomes Tailwind input).
- `app/static/css/app.build.css` — **new**, generated, gitignored.
- `app/static/js/app.js` — adapted to Alpine where Bootstrap JS was used.
- `app/static/js/tipo_form.js` — adapted to Alpine; SortableJS calls preserved.
- `app/static/vendor/bootstrap/` — **deleted**.
- `app/static/vendor/bootstrap-icons/` — **deleted**.
- `app/static/vendor/sortablejs/` — kept.
- `app/static/vendor/lucide/` — **new**; SVG sprite + per-icon files.
- `app/static/vendor/alpinejs/alpine.min.js` — **new**; vendored from CDN release.
- `app/static/vendor/tailwindcss` — **new** (binary, gitignored — installed in image).
- `app/static/fonts/Inter/` — **new**; Inter `*.woff2` files self-hosted.
- `app/_shared/templatetags/__init__.py` — **new (or extended if exists)**.
- `app/_shared/templatetags/lucide.py` — **new**; `{% lucide %}` template tag.
- `Dockerfile` — install Tailwind standalone binary (~7 MB).
- `docker-compose.dev.yml` — add `tailwindcss --watch` to `web` service entrypoint.
- `Makefile` — `make css`, `make css-watch` targets.
- `.gitignore` — add `app/static/css/app.build.css`, `app/static/vendor/tailwindcss`.
- `.claude/skills/frontend-design/SKILL.md` — full rewrite.
- `.claude/skills/django-patterns/forms.md` — examples updated to Tailwind/Alpine.
- `.claude/skills/django-patterns/platform.md` — Bootstrap references audited.
- `CLAUDE.md` — Tech Stack section: "Bootstrap 5" → "Tailwind v4 + Alpine.js".
- `.claude/rules/django.md` — Bootstrap class references audited.
- `specs/global/architecture.md` — Tech Stack table: Rendering row updated.
- `specs/global/requirements.md` — Bootstrap mentions audited.

## References

- [global/explorations/2026-04-26-tailwind-migration.md](../../global/explorations/2026-04-26-tailwind-migration.md) — initiative requirements (WHAT/WHY).
- [global/architecture.md](../../global/architecture.md) — current tech stack and template layout rules.
- [.claude/rules/django-code-architect.md](../../../.claude/rules/django-code-architect.md) — architectural law (no template-layer changes here, but the templatetag follows the rules).
- [.claude/rules/django-test-architect.md](../../../.claude/rules/django-test-architect.md) — test conventions; Tier 1/Tier 2 split applies.
- [.claude/skills/django-patterns/e2e.md](../../../.claude/skills/django-patterns/e2e.md) — Playwright golden-path patterns.
- [Tailwind v4 docs](https://tailwindcss.com/docs/v4-beta) — CSS-first config, `@theme`, standalone CLI.
- [Alpine.js v3 docs](https://alpinejs.dev/) — `x-data`, `x-show`, `x-transition`, `x-cloak`.
- [shadcn/ui docs](https://ui.shadcn.com/) — design-token reference (we hand-roll the Django equivalents).
- [Lucide icon set](https://lucide.dev/icons/) — icon library.

## Implementation Details

### 1. Build pipeline (Docker + Tailwind standalone)

**Dockerfile additions** (in the `web` stage, after Python deps install):

```dockerfile
# Tailwind standalone CLI binary (no Node required)
ARG TAILWIND_VERSION=4.0.0
RUN curl -sSL -o /usr/local/bin/tailwindcss \
      "https://github.com/tailwindlabs/tailwindcss/releases/download/v${TAILWIND_VERSION}/tailwindcss-linux-x64" \
    && chmod +x /usr/local/bin/tailwindcss
```

**docker-compose.dev.yml** — wrap the `web` command so the watcher and `runserver` both run:

```yaml
services:
  web:
    command: >
      sh -c "tailwindcss -i /app/app/static/css/app.css
                         -o /app/app/static/css/app.build.css
                         --watch &
             python manage.py runserver 0.0.0.0:8000"
```

(Alt: split into a `command:` script `bin/dev-entrypoint.sh` if the inline form gets unwieldy.)

**Makefile**:

```makefile
.PHONY: css css-watch

css:
	docker compose -f docker-compose.dev.yml exec web \
	  tailwindcss -i /app/app/static/css/app.css \
	              -o /app/app/static/css/app.build.css --minify

css-watch:
	docker compose -f docker-compose.dev.yml exec web \
	  tailwindcss -i /app/app/static/css/app.css \
	              -o /app/app/static/css/app.build.css --watch
```

**.gitignore** additions:

```
app/static/css/app.build.css
```

(Inter font and Lucide sprite ARE checked in — they're vendored assets, not generated.)

**Production build:** `make css` produces a minified `app.build.css`. CI runs `make css` before `collectstatic`.

### 2. Tailwind input file (`app/static/css/app.css`)

Single source of truth for design tokens. Tailwind v4 syntax — no `tailwind.config.js`.

```css
@import "tailwindcss";

@theme {
  /* Color palette — pure monochrome */
  --color-bg:           #ffffff;
  --color-bg-subtle:    #fafafa;
  --color-bg-muted:     #f4f4f5;
  --color-border:       #e4e4e7;       /* zinc-200 */
  --color-border-strong:#d4d4d8;       /* zinc-300 */
  --color-text:         #09090b;       /* zinc-950 */
  --color-text-muted:   #71717a;       /* zinc-500 */
  --color-text-subtle:  #a1a1aa;       /* zinc-400 */
  --color-primary:      #18181b;       /* zinc-900 - primary button bg */
  --color-primary-hover:#000000;
  --color-primary-fg:   #ffffff;

  /* Status palette */
  --color-success:      #16a34a;
  --color-success-soft: #f0fdf4;
  --color-warning:      #d97706;
  --color-warning-soft: #fffbeb;
  --color-danger:       #dc2626;
  --color-danger-soft:  #fef2f2;
  --color-info:         #0284c7;
  --color-info-soft:    #f0f9ff;

  /* Typography */
  --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;

  /* Radius / shadow */
  --radius-sm: 4px;
  --radius:    6px;
  --radius-lg: 8px;
  --shadow-sm: 0 1px 2px rgb(0 0 0 / .04), 0 1px 1px rgb(0 0 0 / .03);
  --shadow:    0 4px 12px rgb(0 0 0 / .06), 0 2px 4px rgb(0 0 0 / .04);
}

@font-face {
  font-family: "Inter";
  font-weight: 400 700;
  font-display: swap;
  src: url("/static/fonts/Inter/InterVariable.woff2") format("woff2");
}

@layer base {
  body {
    font-feature-settings: "cv02","cv03","cv04","cv11";
    letter-spacing: -0.005em;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
  h1, h2, h3, h4 {
    letter-spacing: -0.02em;
    font-weight: 600;
  }
  :focus-visible {
    outline: 2px solid var(--color-text);
    outline-offset: 2px;
    border-radius: var(--radius-sm);
  }
  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }
}

@layer components {
  /* No utility soup — components live as Django partials.
     This layer is for project-specific overrides only.       */
}
```

**Tailwind content scanning (v4 syntax):**

```css
@source "../../templates/**/*.html";
@source "../../**/*.py";  /* For Python-side template strings */
```

### 3. Component partials (`app/templates/components/`)

Hand-rolled, shadcn-style. Each is a small file taking parameters via `{% include %}` `with` syntax. The list:

| Partial | Purpose | Replaces (Bootstrap) |
|---|---|---|
| `button.html` | All button variants (primary/outline/ghost/destructive, sm/md/lg) | `btn btn-*` |
| `card.html` | Card surface (header/body/footer slots via blocks) | `.card` |
| `input.html` | Text input with label + hint + error association | `form-control` |
| `select.html` | Select dropdown | `form-select` |
| `textarea.html` | Textarea | `form-control` |
| `checkbox.html` | Checkbox + label | `form-check` |
| `radio.html` | Radio group | `form-check` |
| `badge_estado.html` | Status badge (refactor existing) | `badge text-bg-*` |
| `breadcrumbs.html` | Breadcrumb nav (refactor existing) | `breadcrumb` |
| `sidebar.html` | App sidebar (refactor existing) | navbar/offcanvas |
| `offcanvas_drawer.html` | Mobile sidebar drawer (Alpine-driven) | `offcanvas` |
| `modal.html` | Dialog (Alpine-driven; `<dialog>` element preferred where feasible) | `modal` |
| `dropdown.html` | Dropdown menu (Alpine-driven) | `dropdown` |
| `toast.html` | Toast notification (Alpine + `aria-live`) | `toast` |
| `alert.html` | Static alert / banner | `alert alert-*` |
| `pagination.html` | Pagination control (refactor existing) | `pagination` |
| `empty_state.html` | Empty / no-results placeholder | (custom in current code) |
| `chip_input.html` | Chip-style multi-value input (refactor existing) | (custom in current code) |
| `field_row.html` | Collapsible draggable form field row (refactor existing) | (custom in current code) |
| `tipo_preview.html` | Live form preview panel (refactor existing) | (custom in current code) |
| `lucide_sprite.html` | Inlined SVG sprite (loaded once in `base.html`) | Bootstrap-Icons CSS |

**Pattern (example, `components/button.html`):**

```django
{% comment %}
  Args:
    type     - submit | button | reset (default: button)
    variant  - primary | outline | ghost | destructive (default: primary)
    size     - sm | md | lg (default: md)
    label    - text content (or use as wrapping include with caller)
    icon     - lucide icon name (optional)
    extra    - extra Tailwind classes
{% endcomment %}
<button type="{{ type|default:'button' }}"
        class="inline-flex items-center justify-center gap-2 font-medium rounded-md
               focus-visible:outline-2 focus-visible:outline-offset-2
               disabled:opacity-50 disabled:pointer-events-none transition-colors
               {% if variant == 'outline' %}border border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-50
               {% elif variant == 'ghost' %}text-zinc-900 hover:bg-zinc-100
               {% elif variant == 'destructive' %}bg-red-600 text-white hover:bg-red-700
               {% else %}bg-zinc-900 text-white hover:bg-black{% endif %}
               {% if size == 'sm' %}h-8 px-3 text-sm
               {% elif size == 'lg' %}h-11 px-6 text-base
               {% else %}h-10 px-4 text-sm{% endif %}
               {{ extra|default:'' }}">
  {% if icon %}{% load lucide %}{% lucide icon class='size-4' %}{% endif %}
  {{ label }}
</button>
```

Each partial follows this convention: comment block listing args, single root element, no JS unless paired with explicit Alpine directives that the caller passes via `extra`.

### 4. Alpine.js integration

Vendor `alpine.min.js` v3.x under `app/static/vendor/alpinejs/`. Load in `base.html` with `defer`:

```html
<script src="{% static 'vendor/alpinejs/alpine.min.js' %}" defer></script>
```

Add `x-cloak` styling in `app.css` `@layer base`:

```css
[x-cloak] { display: none !important; }
```

Bootstrap JS replacement mapping:

| Bootstrap JS | Alpine pattern |
|---|---|
| Modal | `<dialog x-data="{ open: false }" :open="open">` + `dialog.showModal()` via `x-effect` (or pure `<div x-show=... x-transition>` for older browser support) |
| Offcanvas | `<div x-data="{ open: false }" x-show="open" x-transition.duration.200ms.opacity>` |
| Dropdown | `<div x-data="{ open: false }" @click.outside="open = false">` |
| Collapse | `<div x-show="expanded" x-collapse>` (uses official `@alpinejs/collapse` plugin — vendor it too) |
| Tooltip | `<span x-data x-tooltip="'text'">` (vendor `@alpinejs/anchor` if needed; or use native `title=`) |
| Toast | `<div x-data="{ show: true }" x-show="show" x-init="setTimeout(()=>show=false,5000)">` + `aria-live="polite"` |

Vendor: `alpine.min.js`, `@alpinejs/collapse` (for accordion / field-row body), `@alpinejs/focus` (for trap-focus in modals).

### 5. Lucide icon system

Vendor strategy: download the `lucide-static` SVGs that the project actually uses (audit per icon) into `app/static/vendor/lucide/icons/{name}.svg`. Build a single SVG sprite at `app/static/vendor/lucide/sprite.svg`.

Template tag (`app/_shared/templatetags/lucide.py`):

```python
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def lucide(name: str, **kwargs) -> str:
    cls = kwargs.get("class", "size-4")
    aria = 'aria-hidden="true"' if not kwargs.get("label") else f'aria-label="{kwargs["label"]}" role="img"'
    return mark_safe(
        f'<svg class="{cls}" {aria}>'
        f'<use href="/static/vendor/lucide/sprite.svg#{name}"></use>'
        f'</svg>'
    )
```

Usage: `{% load lucide %}{% lucide "plus" class="size-4" %}`.

**Icon audit** is a status.md task: grep templates for `bi bi-*` classes, build a Bootstrap-Icons → Lucide name mapping table, vendor only the needed icons. Expected list (from a quick scan): `plus`, `pencil`, `trash-2`, `chevron-down`, `chevron-right`, `chevron-left`, `chevron-up`, `inbox`, `file-text`, `download`, `upload`, `check`, `x`, `alert-circle`, `info`, `arrow-up-down`, `search`, `filter`, `menu`, `log-out`, `user`, `users`, `mail`. Final list confirmed during template work.

### 6. base.html restructure

Replace the head and body shell:

```django
{% load static lucide %}
<!doctype html>
<html lang="es-MX" class="h-full">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{% block title %}Sistema de Solicitudes — UAZ{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'css/app.build.css' %}" />
    <script src="{% static 'vendor/alpinejs/alpine.min.js' %}" defer></script>
    {% block extra_head %}{% endblock %}
  </head>
  <body class="min-h-full bg-white text-zinc-950 font-sans antialiased
               flex flex-col {% if request.user.is_authenticated %}has-sidebar{% endif %}">
    <a href="#main" class="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2
                           focus:z-50 focus:bg-white focus:text-zinc-900 focus:px-3 focus:py-2
                           focus:rounded-md focus:shadow">
      Saltar al contenido
    </a>

    {# Lucide sprite — loaded once #}
    {% include "components/lucide_sprite.html" %}

    {% include "components/navbar.html" %}

    <div class="flex flex-1 min-w-0">
      {% if request.user.is_authenticated %}
        {% include "components/sidebar.html" %}
      {% endif %}
      <main id="main" class="flex-1 min-w-0">
        {% block content %}{% endblock %}
      </main>
    </div>

    {% block extra_body %}{% endblock %}
  </body>
</html>
```

Skip link uses Tailwind `sr-only` + `focus:not-sr-only` pattern (replaces Bootstrap's `visually-hidden-focusable`).

### 7. Per-app template rewrite

All 46 templates rewritten. Each gets:
- Bootstrap class names removed.
- Replaced with Tailwind utilities and / or `{% include "components/..." %}` partials.
- Bootstrap-Icons (`<i class="bi bi-*">`) replaced with `{% lucide "name" %}`.
- `<form>` action/method/csrf preserved exactly.
- `data-bs-*` attributes replaced with `x-*` Alpine equivalents.
- All `id`s, `name`s, accessible labels preserved exactly.

Per-app sequencing in `status.md` (each app is independent and `[P]`):

| App | Templates | Notable widgets |
|---|---|---|
| `_shared/` | 2 | error pages |
| `components/` | 5 | sidebar, breadcrumbs, badge_estado, etc. — must finish FIRST (everyone else depends) |
| `usuarios/` | 2 | login picker (DEBUG), profile |
| `solicitudes/` | 21 | list/detail/create/revision/tipos/formularios/preview — biggest surface; chip-input, field-row, tipo preview live here |
| `notificaciones/` | 4 | list/detail |
| `mentores/` | 7 | catalog list/detail/create/edit |
| `reportes/` | 4 | dashboard + exports |

### 8. Test updates

- Audit: `rg -n 'btn-|card|navbar|offcanvas|modal|alert-|badge-' app/**/tests/` to find tests that assert on Bootstrap class names. Update assertions to match new Tailwind classes (or, preferably, to assert on roles / text / data-test attributes that survive class changes).
- Add `data-test="..."` attributes to any element where assertions are fragile.
- New Playwright visual-snapshot sweep at `app/tests-e2e/test_visual_snapshot.py`. Renders every URL in a "golden URLs" list at 1280×900 and 320×800 and saves PNG snapshots under `app/tests-e2e/__snapshots__/`. Diff against committed baselines on subsequent runs (use `pytest-playwright`'s built-in `expect_screenshot` or `pytest-snapshot`).
- Existing E2E flows (login, create solicitud, file upload, revision, mentor catalog, reports) must pass unchanged.

### 9. Skill + doc rewrite

After templates are done, rewrite (in this order):

1. `.claude/skills/frontend-design/SKILL.md` — full rewrite. Inline the canonical `app.css` token block, the component partial catalogue, the Alpine pattern table, the Lucide template-tag usage, the Vercel/shadcn aesthetic principles, the WCAG 2.2 AA checklist, the es-MX locale section, the print-styles section, the performance budgets section. Target ~400 lines.
2. `.claude/skills/django-patterns/forms.md` — replace any Bootstrap form snippets with the new component partials and Alpine validation pattern.
3. `.claude/skills/django-patterns/platform.md` — audit for Bootstrap class references; update.
4. `.claude/rules/django.md` — audit; update tech-stack mention.
5. `CLAUDE.md` — Tech Stack section update; add Alpine + Tailwind to the list; mention `make css-watch`.
6. `specs/global/architecture.md` — Tech Stack table: "Django Templates + Bootstrap 5" → "Django Templates + Tailwind v4 + Alpine.js".
7. `specs/global/requirements.md` — audit for Bootstrap mentions.

### 10. Cleanup (final commit before merge)

- Delete `app/static/vendor/bootstrap/`.
- Delete `app/static/vendor/bootstrap-icons/`.
- Confirm no template references `vendor/bootstrap*`.
- Confirm `make css` produces `app.build.css` cleanly from a fresh container.
- Confirm `python manage.py collectstatic --no-input` succeeds.

### Sequencing

1. Build pipeline (Dockerfile, docker-compose.dev.yml, Makefile, .gitignore, `app.css` skeleton) — must work end-to-end with at least one Tailwind class rendering before anything else.
2. Vendor Alpine + Lucide + Inter font; build sprite + template tag.
3. Rewrite `base.html` and **all** of `components/` — every other template depends on these partials.
4. Rewrite per-app templates in parallel `[P]`: usuarios, solicitudes, notificaciones, mentores, reportes, _shared. Solicitudes is the largest and may itself decompose internally.
5. Update tests + add visual-snapshot sweep.
6. Rewrite frontend-design skill + audit other docs/rules/CLAUDE.md/architecture.md.
7. Cleanup: delete vendor Bootstrap, run full Playwright suite, take final screenshots.

## E2E coverage

### In-process integration (Tier 1 — Django `Client`, no browser)

- _None._ (No backend behavior changes; existing Tier 1 tests must continue passing as a regression gate, but no new flows are introduced.)

### Browser (Tier 2 — `pytest-playwright`)

- **Visual snapshot sweep** — render the golden URL list at 1280×900 and 320×800; persist baselines; CI diffs on subsequent runs. Golden URLs (derived from `urls.py`):
  - `/` (home / dashboard if any)
  - `/auth/dev-login/` (DEBUG only — skip in CI)
  - `/solicitudes/`
  - `/solicitudes/nueva/`
  - `/solicitudes/<folio>/` (sample seed)
  - `/solicitudes/tipos/`
  - `/solicitudes/tipos/nuevo/`
  - `/solicitudes/tipos/<id>/editar/`
  - `/solicitudes/revision/`
  - `/solicitudes/revision/<folio>/`
  - `/notificaciones/`
  - `/mentores/`
  - `/mentores/nuevo/`
  - `/reportes/`
  - Error pages: `/404/`, `/500/`
- **Smoke flow — student creates and submits a solicitud:** as authenticated student, navigate to `/solicitudes/nueva/`, pick a tipo, fill all required fields, attach a file, submit; expect redirect to detail page in `PENDIENTE` state.
- **Smoke flow — admin reviews and approves:** as authenticated admin, navigate to `/solicitudes/revision/`, open a `PENDIENTE` solicitud, approve it; expect redirect to revision queue with success toast.
- **Smoke flow — interactive widgets:** as any authenticated user, exercise the offcanvas mobile sidebar (open + close), a modal (open + escape closes), a dropdown (open + click-outside closes), the chip-input (add chip, remove chip), the field-row drag/drop in tipo edit, the tipo live-preview panel.

## Acceptance Criteria

- [ ] Tailwind standalone CLI runs inside the `web` container; `make css` produces a clean `app.build.css`; `make css-watch` rebuilds on file change in dev compose.
- [ ] Zero references to Bootstrap CSS or JS in `app/templates/` or `app/static/`. `app/static/vendor/bootstrap*` deleted.
- [ ] All 46 templates render without console errors at 1280×900 and 320×800 (Playwright snapshot sweep passes).
- [ ] Every interactive widget shipped today still works (modal, dropdown, offcanvas, collapse, toast, chip-input, field-row drag/drop, tipo live preview, sidebar mobile drawer).
- [ ] All existing Django `Client` tests pass (with class-name assertions updated where present).
- [ ] All existing Tier-2 Playwright golden-path flows pass (login, create solicitud, file upload, revision, mentor catalog, reports).
- [ ] WCAG 2.2 AA: contrast ≥4.5:1 body / ≥3:1 large; visible focus on every interactive element; skip link present and reachable; one `<h1>` per page; `aria-current="page"` on active nav; touch targets ≥44×44 (24×24 hard floor); `prefers-reduced-motion` respected.
- [ ] es-MX locale unchanged: dates `d/m/Y`, currency `MXN`, names as three fields.
- [ ] WeasyPrint PDFs unchanged — sample solicitud PDF generates and renders identically to pre-migration.
- [ ] `frontend-design` skill rewritten end-to-end for Tailwind/Alpine/shadcn aesthetic; ~400 lines.
- [ ] `CLAUDE.md`, `.claude/rules/django.md`, `django-patterns/forms.md`, `django-patterns/platform.md`, `specs/global/architecture.md`, `specs/global/requirements.md` audited and updated where Bootstrap was mentioned.
- [ ] No Node.js or npm installed on the developer host; only the Tailwind standalone binary in the container.
- [ ] Single feature branch `feat/015-tailwind-migration`, single PR, atomic merge.

## Open Questions

- **Tailwind v4 release status as of execution.** v4 was in beta at planning time. If GA hasn't shipped when implementation starts, fall back to the latest beta tag pinned in `Dockerfile`. If a blocking bug is found, fall back to v3.4.x with `tailwind.config.js` (the `@theme` block becomes config, but the rest of the plan is unchanged).
- **Alpine `@alpinejs/collapse` plugin licensing** — confirm MIT before vendoring (it is, but verify at vendor time).
- **`<dialog>` element vs `x-show` div for modals.** `<dialog>` has better semantics + native backdrop + escape-key support, but Safari < 15.4 doesn't support `showModal()`. Decide during component build; default to `<dialog>` with an Alpine wrapper for state.
- **Visual-snapshot baseline tolerance.** Sub-pixel font rendering varies by OS/CI runner. May need to commit baselines from CI Linux only and run dev manually. Decide during snapshot-test setup.
