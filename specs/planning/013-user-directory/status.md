# 013 — User Directory (admin read-only) — Status

**Status:** Not Started
**Last updated:** 2026-04-26

## Checklist

### Schemas, constants, package skeleton
- [ ] [P] Create `app/usuarios/directory/` package + `__init__.py`, `constants.py` (`PAGE_SIZE = 25`)
- [ ] [P] `schemas.py` — `UserListFilters`, `UserListItem`, `UserDetail`

### Repository
- [ ] `repositories/user_directory/interface.py` — `UserDirectoryRepository(ABC)`
- [ ] `repositories/user_directory/implementation.py` — `OrmUserDirectoryRepository.list` (filter + order + paginate) + `get_detail` (raises `UserNotFound`)
- [ ] `tests/test_repositories.py` — filter combos, ordering stability, pagination correctness, empty results, unknown matrícula → `UserNotFound`

### Service
- [ ] `services/user_directory/interface.py` — `UserDirectoryService(ABC)`
- [ ] `services/user_directory/implementation.py` — `DefaultUserDirectoryService` (delegates list; overlays `is_mentor`; swallows + logs `MentorService` failures → `is_mentor=None`)
- [ ] `tests/test_services.py` — list passthrough, mentor overlay (true/false/None on raise), uses fakes (no real mentor repo)

### Form
- [ ] `forms/filter_form.py` — `DirectoryFilterForm` with permissive `to_filters()`
- [ ] `tests/test_forms.py` — bad role / bad page / blank q / valid combo → correct `UserListFilters`

### Views, URLs, DI
- [ ] `views/admin.py` — `DirectoryListView`, `DirectoryDetailView` (LoginRequired + AdminRequired)
- [ ] Safe `?return=` validation helper (relative path only; reuse `CallbackView`'s pattern)
- [ ] `urls.py` (feature) + include in `app/usuarios/urls.py` under `usuarios:directory:`
- [ ] `dependencies.py` — `get_user_directory_repository`, `get_user_directory_service`

### Templates
- [ ] [P] `templates/usuarios/directory/_filter_form.html` — role select + q + Buscar/Limpiar
- [ ] [P] `templates/usuarios/directory/list.html` — header, filter form include, table, pagination, empty state
- [ ] [P] `templates/usuarios/directory/detail.html` — Identidad / Académico / Mentor / Auditoría sections, "Volver" link, no edit affordances

### Navigation
- [ ] Edit `templates/components/sidebar.html` — add "Directorio · Usuarios" entry inside the ADMIN block (before "Reportes"); active-path excludes `/auth/...`

### View tests
- [ ] `tests/test_views.py` — admin list 200 with QS; admin detail 200 (mentor true / false / None); anonymous redirect; non-admin 403; unknown matrícula 404; permissive parsing (`role=BOGUS&page=abc` → 200 page 1)

### E2E
- [ ] Tier 1 (Client): list + filter + paginate as admin
- [ ] Tier 1 (Client): detail page with `is_mentor=True` and `is_mentor=False`
- [ ] Tier 1 (Client): detail page with `MentorService` raising → 200 + "Desconocido"
- [ ] Tier 1 (Client): authorization gates (anon redirect, non-admin 403)
- [ ] Tier 1 (Client): unknown matrícula → 404
- [ ] Tier 1 (Client): permissive parsing regression

## Blockers

None.

[P] = can run in parallel
