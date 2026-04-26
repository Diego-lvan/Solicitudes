# 015 — Tailwind v4 Frontend Migration — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-26
- Initiative created.
- Brainstorm draft requirements written to `specs/global/explorations/2026-04-26-tailwind-migration.md` (kept under `explorations/` because the initiative is infrastructure-class and spans every app's templates — no single feature folder is the right home; not promoted to `apps/<app>/<feature>/requirements.md`).
- Key decisions locked in brainstorm (consolidated in `plan.md`):
  - **Aesthetic:** Vercel/shadcn pure monochrome (`zinc-950` text, `zinc-900` primary, `zinc-200` hairline borders, no decorative accent hue, status colors carry all chromatic meaning).
  - **Tailwind:** v4 (CSS-first config via `@theme`).
  - **Build pipeline:** Tailwind standalone CLI binary inside the existing `web` Docker container; no Node, no sidecar.
  - **JS framework:** Alpine.js v3 + `@alpinejs/collapse` + `@alpinejs/focus`. SortableJS retained for drag/drop. All Bootstrap JS deleted.
  - **Components:** hand-rolled Django partials in `templates/components/`; no third-party Tailwind component library.
  - **Iconography:** Lucide via vendored SVG sprite + `{% lucide %}` template tag. Bootstrap-Icons deleted.
  - **Font:** Inter, self-hosted (variable woff2), with `cv02 cv03 cv04 cv11` features and slight negative tracking.
  - **Migration strategy:** big-bang. Single feature branch `feat/015-tailwind-migration`, single PR.
  - **Out of scope:** WeasyPrint PDF templates, backend Python, `code_example/`, dark mode, new features.
- Roadmap row added (#015, Not Started, depends on 001 + all shipped initiatives transitively, blocks 013 + 014 template work during in-progress window).
