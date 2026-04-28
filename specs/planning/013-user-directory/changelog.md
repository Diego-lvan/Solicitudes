# 013 — User Directory (admin read-only) — Changelog

> Append-only. Never edit or delete existing entries.

## 2026-04-26
- Initiative created via `/brainstorm` → `/plan`.
- Scope: admin-only paginated list of `usuarios.User` + read-only detail page; role filter + free-text search; mentor status overlaid live via `MentorService`.
- Key decisions:
  - **Read-only by design.** SIGA + the auth provider own user data; no mutation paths shipped.
  - **New `UserDirectoryRepository` instead of reusing `UserRepository.list_all()`** — preserves the existing DEBUG-only contract documented in `usuarios/design.md` ("Production code paths should not enumerate users").
  - **Cross-feature read via `MentorService`** (interface), not `MentorRepository` — per the architectural rule.
  - **Permissive querystring parsing** (mirrors `reportes` RF-REP-06) — bad `role` / `page` degrades to "no filter" / page 1, never 400.
  - **CSV/Excel/PDF export, links to user's solicitudes, edit/delete: explicit non-goals** for v1.
  - **No Tier-2 Playwright in v1** — internal admin tooling, low risk; Tier-1 in-process coverage only.
  - **Sidebar entry under existing ADMIN section**, "Directorio · Usuarios", active-path excludes `/auth/...` to avoid false highlighting on the profile page.
- Files written: `specs/apps/usuarios/directory/{requirements,design}.md`, `specs/planning/013-user-directory/{plan,status,changelog}.md`.
- Roadmap row added.

## 2026-04-26 (impl session 1)
- Implemented section "Schemas, constants, package skeleton": `app/usuarios/directory/{__init__,constants,schemas}.py` (PAGE_SIZE=25; `UserListFilters`/`UserListItem`/`UserDetail` Pydantic v2 frozen DTOs).
- Implemented section "Repository": interface `UserDirectoryRepository` + `OrmUserDirectoryRepository` (filter on role + Q over matrícula/full_name/email; ordered by `(role, matricula)`; offset/slice pagination; `get_detail` raises `usuarios.exceptions.UserNotFound`).
- Tests: `tests/test_repositories.py` — 11 tests covering filter combos (role, q, role+q), ordering stability, pagination correctness (multi-page + past-end + empty), and detail get + UserNotFound. All 11 pass against Postgres.
- Test wrapper around `make_user` injects unique email per matrícula because the existing `usuarios/tests/factories.py` default email captures a `baker.seq` generator inside an f-string (latent bug — not fixing here, out of scope).
- Stack: parallel docker compose project `solicitudes013` on host ports 8013/8444/5433 to coexist with the main worktree's stack.

## 2026-04-26 (impl session 2)
- Implemented section "Service": `services/user_directory/{interface,implementation}.py` — `DefaultUserDirectoryService` injects `UserDirectoryRepository` + `MentorService` (interface, per cross-feature rule) + `page_size` + `logger`. List delegates to repo; `get_detail` overlays `is_mentor` and swallows mentor exceptions to `None` with WARNING log + traceback.
- Tests `tests/test_services.py` — 5 tests using local fakes (no real mentor wiring): list passthrough, mentor true/false, swallow-and-log on raise, propagation of `UserNotFound` without calling mentor. All pass.
- Implemented section "Form": `forms/filter_form.py` — permissive `to_filters()` that handles missing `cleaned_data` keys defensively (bad inputs degrade silently).
- Tests `tests/test_forms.py` — 8 cases (bad/blank role, bad/zero/negative page, blank q after strip, valid combo). All pass.
- Implemented section "Views, URLs, DI": `views/admin.py` (`DirectoryListView`, `DirectoryDetailView` — both `AdminRequiredMixin`); `views/_helpers.py` (`safe_return_path`: rejects scheme/netloc/protocol-relative — relative paths only; `build_filter_querystring`); `urls.py` (`directory:list`/`directory:detail`); `dependencies.py` factory functions.
- Wired `usuarios.directory.urls` into `app/usuarios/urls.py` under prefix `usuarios/`. URL reversals confirmed: `/usuarios/`, `/usuarios/A1/`.
- **Plan correction**: §6 prose vs. snippet inconsistency on `back_qs` resolved per user input — implementation follows the prose (`?return=` validated as relative, fallback to bare list URL); the inline snippet was a stale draft.
- Implemented section "Templates": three Bootstrap 5 templates (`_filter_form.html`, `list.html`, `detail.html`) following the `frontend-design` skill — h1 sized `.h3`, `.table-hover` not striped, low-priority columns hidden `<md`/`<lg`, empty-state per the canonical shape, status badges via `text-bg-*`, single neutral card style for the four detail sections.
- Implemented section "Navigation": new "Directorio · Usuarios" entry in the sidebar admin block before "Reportes"; active-path matcher excludes `/auth/...`.
- Visually verified at 1280×900 desktop and 320×800 mobile via Playwright against the parallel dev stack — list paginates / filters cleanly, detail shows the 2×2 card grid with all four sections, mobile reflows to a hamburger nav with three columns and no horizontal scroll. Screenshots in `/tmp/013-screens/`.
- Implemented section "View tests" (also covers Tier-1 E2E in plan §"E2E coverage"): 19 tests in `tests/test_views.py` — list rendering for admin, paginate+filter, q-search, row→detail link with `?return=` preservation, empty state, permissive parsing of `role=BOGUS&page=abc`, detail with mentor true/false/raises (mocked at `DefaultMentorService.is_mentor`), safe `?return=` accept-and-fallback, 404 on unknown matrícula, anon redirect, and 403 for ALUMNO/DOCENTE/CONTROL_ESCOLAR/RESPONSABLE_PROGRAMA.
- Test infra note: had to build inverse of `PROVIDER_ROLE_MAP` for JWT minting because internal `Role.value.lower()` does not equal the provider claim string for `RESPONSABLE_PROGRAMA` (claim is `resp_programa`). Pre-existing tests sidestepped this by not minting RP tokens.
- Worktree compose adjustment: dropped `nginx-dev` (not needed for screenshots; saves the TLS cert dance in MCP Playwright) and exposed `web` directly on host port `8015` so screenshots could hit `http://localhost:8015/...`.
- Full suite: **634 passed, 1 failure (`mentores/tests/test_backfill_migration.py::test_backfill_preserves_fecha_alta_verbatim`), 16 errors (Tier-2 e2e, chromium not installed in this worker)**. The 1 failure was confirmed pre-existing on `main` (NOT-NULL violation on `usuarios_user.gender` from initiative 011's migration interacting with the backfill fixture); 16 e2e errors are pre-existing infra (run `make e2e-install` once to enable). Neither is in scope for this initiative.

## 2026-04-26 (review round 1)
- `code-reviewer` agent dispatched against full initiative diff. Returned 0 Critical, 2 Important, 4 Suggestions.
- **Important #1 (accepted, fixed):** `_filter_form.html` was hardcoding the role `<option>` set instead of iterating `form.role.field.choices`. Two-source-of-truth drift hazard. Replaced with a `{% for value, label in form.role.field.choices %}` loop. Visually verified — dropdown still renders all six options ("Todos los roles" + the five Roles) and pre-selects the active filter.
- **Important #2 (accepted, fixed in-scope):** `app/usuarios/tests/factories.py::make_user` had a latent bug — its email default was `f"{baker.seq('user')}@..."` which f-strings the *generator object* into the string, making every default email identical and breaking the unique constraint after the second call. The two local wrappers added in session 1 were a workaround. Fixed the factory to derive `matricula` and `email` from `uuid4().hex[:10]` (mirrors the `mentores/tests/factories.py` pattern). Removed both local wrappers in `tests/test_repositories.py` and `tests/test_views.py`. Full suite still passes (635 — see below).
- **Suggestion: length cap on `safe_return_path` (accepted, fixed):** Added `_MAX_RETURN_LEN = 512`; helper now returns `None` for raw values exceeding it. New regression test `test_detail_oversized_return_falls_back_to_list` exercises a 600-char payload and asserts the rendered href falls back to `/usuarios/`.
- **Suggestion: `?return=` double-encoding readability in `list.html` (partial):** Refactoring into a view-built field would add more state to each `UserListItem` than it removes from the template; instead added a one-line comment in the template body explaining why `%3F` + `|urlencode` are both required. Future maintainer has the context.
- **Suggestion: sidebar matcher will activate on any future `/usuarios/...` admin pages:** Noted, no action — accurate but no follow-up needed today; this is the only `/usuarios/...` admin page.
- **Suggestion: changelog should call out `LoginRequiredMixin` simplification:** Done — `AdminRequiredMixin` already extends `LoginRequiredMixin` (verified at `app/usuarios/permissions.py:32`), so applying just `AdminRequiredMixin` is functionally identical to the plan's `LoginRequiredMixin + AdminRequiredMixin`.
- **Suggestion: `docker-compose.worktree.yml` not in plan:** Documented in the impl-session-2 entry above; this is an infra-only file used purely to run a parallel dev stack inside the worktree on alt ports.
- Re-verified: `pytest usuarios/directory/tests/` → 44 passed. Full suite (skipping tests-e2e) → **635 passed, 1 pre-existing failure** (same `mentores backfill migration`, unchanged).
- Visually re-verified: filter dropdown (driven by `form.role.field.choices`) renders all roles with `DOCENTE` correctly preselected when `?role=DOCENTE`; detail page given `?return=https://evil.example.com/` falls back to `/usuarios/` (assertion via Playwright DOM read on the back-button href).
- Sent for closeout: needs `/review` confirmation, then SDD closeout (the existing `specs/apps/usuarios/directory/{requirements,design}.md` get a status-flip + design-promotion of `safe_return_path` semantics, accent-sensitive `icontains` limitation, and the cross-feature mentor overlay contract; roadmap row 013 → Done).

## 2026-04-26 (review round 2 — /review + closeout)
- `/review` ran clean except for one WARNING: `views/admin.py` held two public classes (`DirectoryListView`, `DirectoryDetailView`), violating the One-Class-Per-File rule. Plan §6 had bundled them — plan-vs-rule conflict; rule wins.
- Fixed by splitting into `views/list.py` and `views/detail.py`. Updated `urls.py` imports. Removed `views/admin.py`. Updated `plan.md` §1 (file tree) and §6 (view section) to reflect the split and to document the corrected `safe_return_path` back-link wiring.
- User caught a multi-line `{# ... #}` comment leaking as visible text in `list.html` — Django's `{# #}` is single-line only. Replaced with `{% comment %}…{% endcomment %}`. Re-verified visually at 1280×900 and 320×800 against the main dev stack: comment text absent from rendered HTML; `grep "percent-encoded" /usuarios/` returns 0 matches. My earlier "verified" claim had been based on a screenshot taken before adding the comment — recorded so the same gap doesn't repeat.
- Re-verified: `pytest usuarios/directory/tests/` → **44 passed, exit 0** (fresh in this session).
- SDD closeout performed: `specs/apps/usuarios/directory/requirements.md` left unchanged (user-visible behavior matches brainstorm); `specs/apps/usuarios/directory/design.md` updated to promote stable details from `plan.md`; `specs/global/roadmap.md` row 013 → `Done`; `specs/planning/013-user-directory/status.md` top → `Done` (Last updated bumped). No `flows/*.md` change — directory is a single read, not a multi-app flow.
