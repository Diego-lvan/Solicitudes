# End-to-End Testing — Two Tiers

E2E means "exercises the full stack." There are two ways to do that: in-process (fast, no browser) and in-browser (slow, real DOM). **Use both.** They catch different bugs.

| | Tier 1 — In-process | Tier 2 — Browser |
|---|---|---|
| Tool | `pytest-django` `Client` (multi-step) | `pytest-playwright` |
| Speed | ~50 ms / test | ~5–30 s / test |
| Server | none (in-process) | live server fixture |
| Browser | none | Chromium / Firefox / WebKit |
| Catches | routing, perms, view→service→repo wiring, redirect chains, signal flow, full-stack data | everything in tier 1 + CSS, JS, focus order, ARIA, real file uploads |
| Misses | CSS, JS, browser-specific behavior, accessibility | nothing meaningful |
| Count target | ~15–30 across project | ~5–15 across project |

---

## Tier 1 — In-process integration (Django `Client`)

### Where it lives

- **Single-feature multi-step flows** → that feature's `tests/test_views.py`.
- **Cross-feature flows** (touch ≥ 2 apps) → start in the highest-level feature's `test_views.py`. Promote to a top-level `tests-integration/` only if you grow past ~10 cross-feature tests.

### Idiom

```python
# apps/solicitudes/intake/tests/test_views.py
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_alumno_creates_and_submits_solicitud(client_logged_in_alumno, tipo_solicitud_factory):
    tipo = tipo_solicitud_factory(activo=True)

    # 1. GET the create page
    create_url = reverse("solicitudes:intake:create")
    response = client_logged_in_alumno.get(create_url)
    assert response.status_code == 200
    assert response.templates[0].name == "solicitudes/intake/create.html"

    # 2. POST the form (creates a draft)
    response = client_logged_in_alumno.post(
        create_url,
        data={
            "tipo_solicitud_id": tipo.id,
            "titulo": "Constancia de estudios",
            "descripcion": "Para trámite de beca." * 3,
        },
        follow=True,
    )
    assert response.redirect_chain[-1][1] == 302
    folio = response.context["solicitud"].folio
    assert response.context["solicitud"].estado == "BORRADOR"

    # 3. POST submit (state transition)
    submit_url = reverse("solicitudes:intake:submit", args=[folio])
    response = client_logged_in_alumno.post(submit_url, follow=True)
    assert response.context["solicitud"].estado == "PENDIENTE"

    # 4. Verify a notification was queued (via the apps.notificaciones service)
    from django.core import mail
    assert len(mail.outbox) == 1
    assert "Pendiente" in mail.outbox[0].subject
```

### Reusable client fixtures

```python
# tests/conftest.py (project root) or per-app conftest.py
import pytest


@pytest.fixture
def client_logged_in_alumno(client, alumno_user):
    client.force_login(alumno_user)
    return client


@pytest.fixture
def client_logged_in_personal(client, personal_user):
    client.force_login(personal_user)
    return client
```

`force_login` skips the actual auth flow — fine because you have **separate** unit tests for the auth middleware. Cross-feature integration tests should *use* auth, not test it.

### Anti-patterns

- ❌ Calling the service or repository directly from the test — that's a service test, not an integration test. Drive through HTTP.
- ❌ Asserting on internal model state via `Model.objects.get(...)` — assert through the `Client`'s subsequent GET / response context. The whole point is testing the user-visible flow.
- ❌ Running migrations per-test — `pytest-django`'s `--reuse-db` is your friend; the suite handles it for you.

---

## Tier 2 — Browser E2E (`pytest-playwright`)

### Setup

`requirements.txt` (or `requirements-dev.txt`):
```
pytest-playwright>=0.5
```

Install browsers once:
```bash
playwright install chromium
playwright install firefox  # if cross-browser
```

### Layout

```
tests-e2e/
├── conftest.py                    # shared fixtures (live_server, page, authed contexts)
├── pages/                         # Page Object Model
│   ├── __init__.py
│   ├── base_page.py
│   ├── login_page.py
│   ├── solicitud_create_page.py
│   ├── solicitud_detail_page.py
│   └── solicitud_list_page.py
├── flows/                         # multi-page user journeys
│   ├── __init__.py
│   └── alumno_creates_and_submits.py
├── tests/
│   ├── __init__.py
│   ├── test_intake_golden_path.py
│   ├── test_revision_flow.py
│   └── test_pdf_download.py
├── fixtures/
│   ├── sample_files/
│   │   └── comprobante.pdf
│   └── seeds.py                   # Django ORM seeders for E2E test data
├── auth/                          # storageState .json files (gitignored)
└── playwright.config.py
```

### `playwright.config.py`

```python
# tests-e2e/playwright.config.py
import os

# Read from env so CI can override
CI = os.environ.get("CI") == "true"

PLAYWRIGHT_CONFIG = {
    "use": {
        "base_url": os.environ.get("E2E_BASE_URL", "http://localhost:8000"),
        "trace": "on-first-retry" if CI else "retain-on-failure",
        "screenshot": "only-on-failure",
        "video": "retain-on-failure",
        "viewport": {"width": 1280, "height": 800},
        "locale": "es-MX",
        "timezone_id": "America/Mexico_City",
    },
    "retries": 2 if CI else 0,
    "workers": 1 if CI else 4,  # parallel workers; 1 in CI for stability
    "timeout": 30_000,  # 30s per test
}
```

### `conftest.py` — fixtures

```python
# tests-e2e/conftest.py
import pytest
from playwright.sync_api import Browser, BrowserContext, Page

from tests_e2e.fixtures.seeds import seed_alumno_with_session


@pytest.fixture(scope="session")
def authed_context_alumno(browser: Browser, live_server) -> BrowserContext:
    """A browser context with an alumno session cookie pre-injected.

    Uses Django's session bridge (option 2 from the test architect rule)
    so the test doesn't have to drive UI login.
    """
    user, session_cookie = seed_alumno_with_session()
    context = browser.new_context()
    context.add_cookies([{
        "name": "sessionid",
        "value": session_cookie,
        "url": live_server.url,
    }])
    yield context
    context.close()


@pytest.fixture
def alumno_page(authed_context_alumno: BrowserContext) -> Page:
    page = authed_context_alumno.new_page()
    yield page
    page.close()
```

### Page Object Model (POM)

One class per page. Methods read like prose. Selectors live here, **only here**.

```python
# tests-e2e/pages/solicitud_create_page.py
from playwright.sync_api import Page, expect


class SolicitudCreatePage:
    """Page object for /solicitudes/intake/nueva/."""

    URL = "/solicitudes/intake/nueva/"

    def __init__(self, page: Page) -> None:
        self.page = page

    def goto(self) -> None:
        self.page.goto(self.URL)
        expect(self.page).to_have_title("Nueva solicitud")

    def select_tipo(self, tipo_label: str) -> None:
        self.page.get_by_label("Tipo de solicitud").select_option(label=tipo_label)

    def fill_titulo(self, titulo: str) -> None:
        self.page.get_by_label("Título").fill(titulo)

    def fill_descripcion(self, descripcion: str) -> None:
        self.page.get_by_label("Descripción").fill(descripcion)

    def attach_file(self, field_label: str, path: str) -> None:
        self.page.get_by_label(field_label).set_input_files(path)

    def submit(self) -> None:
        self.page.get_by_role("button", name="Guardar").click()

    def expect_validation_error(self, field_label: str, message: str) -> None:
        field = self.page.get_by_label(field_label)
        error = field.locator("xpath=following-sibling::*[contains(@class, 'invalid-feedback')]")
        expect(error).to_contain_text(message)
```

**Use `get_by_role` / `get_by_label` over CSS selectors.** They're accessibility-aware and double as a smoke test that your form labels and ARIA roles are intact. CSS selectors break on every refactor; semantic locators don't.

### Flow composition

A flow composes Page Objects into a single user journey. Reusable across multiple tests.

```python
# tests-e2e/flows/alumno_creates_and_submits.py
from tests_e2e.pages.solicitud_create_page import SolicitudCreatePage
from tests_e2e.pages.solicitud_detail_page import SolicitudDetailPage


def alumno_creates_draft(page, *, tipo: str, titulo: str, descripcion: str) -> str:
    """Returns the folio of the created draft."""
    create = SolicitudCreatePage(page)
    create.goto()
    create.select_tipo(tipo)
    create.fill_titulo(titulo)
    create.fill_descripcion(descripcion)
    create.submit()

    detail = SolicitudDetailPage(page)
    detail.expect_landed()
    return detail.read_folio()


def alumno_submits_draft(page, folio: str) -> None:
    detail = SolicitudDetailPage(page)
    detail.goto(folio)
    detail.click_submit_button()
    detail.expect_estado("Pendiente")
```

### A real test

```python
# tests-e2e/tests/test_intake_golden_path.py
import pytest

from tests_e2e.flows.alumno_creates_and_submits import (
    alumno_creates_draft,
    alumno_submits_draft,
)


@pytest.mark.e2e
def test_alumno_creates_and_submits_solicitud(alumno_page, tipo_solicitud_seed):
    folio = alumno_creates_draft(
        alumno_page,
        tipo="Constancia de estudios",
        titulo="Constancia para beca",
        descripcion="Solicito constancia de estudios para trámite de beca CONACYT.",
    )
    alumno_submits_draft(alumno_page, folio)

    # Final assertion: the detail page now shows estado=Pendiente
    # (already asserted inside alumno_submits_draft; here for clarity)
    assert "Pendiente" in alumno_page.locator(".badge-estado").text_content()
```

Mark with `@pytest.mark.e2e` so you can run unit/integration without browser tests:
```bash
pytest -m "not e2e"            # everything except browser
pytest -m e2e                  # just browser
```

### Authentication strategies

**Option 1 — `storageState` (Playwright-native)**

One setup test logs in via the UI, captures the storage state, every subsequent test reuses it.

```python
# tests-e2e/tests/test_setup_storage_state.py
import pytest

from tests_e2e.pages.login_page import LoginPage


@pytest.mark.e2e_setup
def test_create_alumno_storage_state(page, live_server):
    LoginPage(page).goto().login("alumno@uaz.mx", "test-password")
    page.context.storage_state(path="tests-e2e/auth/alumno.json")
```

Then in tests:
```python
@pytest.fixture
def alumno_page(browser, live_server):
    context = browser.new_context(storage_state="tests-e2e/auth/alumno.json")
    page = context.new_page()
    yield page
    context.close()
```

Re-run `test_create_alumno_storage_state` whenever sessions expire (rare in test runs).

**Option 2 — Django session bridge (faster, less realistic)**

```python
# tests-e2e/fixtures/seeds.py
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import get_user_model

User = get_user_model()


def seed_alumno_with_session() -> tuple[User, str]:
    user, _ = User.objects.get_or_create(
        email="alumno@uaz.mx",
        defaults={"role": "alumno", "is_active": True},
    )
    session = SessionStore()
    session["_auth_user_id"] = str(user.pk)
    session["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
    session.save()
    return user, session.session_key
```

Use **Option 1** for "real user flow" tests (where login matters); **Option 2** when you want to test the *page logic* without auth in the picture.

### Artifacts to capture

| Artifact | Setting | Output |
|---|---|---|
| Trace | `trace="retain-on-failure"` (local), `"on-first-retry"` (CI) | `test-results/<test>/trace.zip` — view with `playwright show-trace trace.zip` |
| Screenshot | `screenshot="only-on-failure"` | `test-results/<test>/test-failed-1.png` |
| Video | `video="retain-on-failure"` | `test-results/<test>/video.webm` |
| HTML report | always (default) | `playwright-report/index.html` |

`.gitignore`:
```
test-results/
playwright-report/
playwright/.cache/
tests-e2e/auth/*.json
```

### CI integration

Run E2E in a **separate CI job** from unit/integration:

```yaml
# .github/workflows/e2e.yml (sketch)
e2e:
  runs-on: ubuntu-latest
  needs: [lint, unit-and-integration]   # block on cheaper jobs first
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.12" }
    - run: pip install -r requirements.txt
    - run: playwright install chromium
    - run: |
        python manage.py migrate --no-input
        pytest -m e2e --tracing on-first-retry
    - uses: actions/upload-artifact@v4
      if: failure()
      with:
        name: playwright-report
        path: |
          playwright-report/
          test-results/
        retention-days: 14
```

The HTML report is the UX. Don't try to read traces in the terminal — open `index.html`.

### File uploads (the one Playwright detail that bites)

```python
# Page Object
def attach_evidence(self, path: str) -> None:
    self.page.locator("input[type=file][name='archivo']").set_input_files(path)

# Test
def test_alumno_attaches_evidence(alumno_page):
    SolicitudCreatePage(alumno_page).attach_evidence(
        "tests-e2e/fixtures/sample_files/comprobante.pdf"
    )
```

`set_input_files` is the only reliable way; never try to drive the OS file dialog.

### HTMX / partial responses

If you adopt HTMX, swap actions trigger a `hx-trigger`-driven request that returns an HTML fragment. Wait for the fragment swap before asserting:

```python
with page.expect_response(lambda r: "/solicitudes/" in r.url and r.status == 200):
    page.get_by_role("button", name="Aprobar").click()

expect(page.locator(".badge-estado")).to_contain_text("Aprobada")
```

### Anti-patterns

- ❌ Driving login via UI on every test (slow, flaky, redundant) — use storage state or session bridge
- ❌ Reproducing form-validation cases in browser tests (slow, redundant) — that's `test_forms.py`'s job
- ❌ Asserting on hard-coded selectors (`#id_titulo`) — use `get_by_label("Título")` so refactors don't cascade
- ❌ Running browser E2E in the same CI job as unit tests — it bloats the critical path; isolate
- ❌ Committing `test-results/` or `playwright-report/` — gitignore them; CI artifacts are the durable copy
- ❌ "Just one more E2E for this validation case" — every browser test is ~20× the cost of a unit test; resist

---

## Local execution & infra

E2E spans both tiers, so local setup matters for both. **Default to `pytest-django`'s `live_server`. Reuse the dev Compose stack for tests is forbidden.**

### Three scenarios

| Scenario | How | When |
|---|---|---|
| **Default local loop** | `pytest -m e2e` (or just `pytest`) — uses `pytest-django`'s `live_server` fixture, which spins Django up in-process on a free port against the test DB (SQLite by default). Browser launches via `pytest-playwright`. | 95% of the time. Fast, transactional rollback per test, zero Docker. |
| **Postgres-against-real-DB smoke** | `docker compose -f docker-compose.test.yml up -d`, then `pytest -m e2e --ds=config.settings.test_postgres`, then `down -v`. | Occasionally — before merge, when a test exercises Postgres-specific behavior (JSONB, full-text, real `select_for_update`), or to reproduce a CI failure locally. |
| **CI** | A Postgres service container (GitHub Actions service / GitLab CI service) OR `docker-compose.test.yml` brought up by the workflow. Always real Postgres. | Every CI run on `main` and PRs. |

### Do NOT reuse `docker-compose.dev.yml` for tests

Three failure modes that show up on every team that tries:

1. **Race condition** — dev is still up when tests launch; tests POST against your half-built feature; the dev DB ends up half-mutated; tests fail mysteriously.
2. **Fixture drift** — dev's seed data silently satisfies an assertion that should fail without it. Bug ships.
3. **Cleanup paralysis** — a test crashes mid-run; the dev DB is in a weird state; you can't reproduce yesterday's bug because the data changed.

Separate compose makes all three structurally impossible.

| Concern | `docker-compose.dev.yml` | `docker-compose.test.yml` |
|---|---|---|
| Data | Your fixtures, manual entries, broken seed data | Empty, throwaway volume |
| Concurrency | Can't run tests while developing | Independent ports/volumes |
| Boot speed | Loads dev fixtures, starts Celery worker, beat, etc. | Bare minimum: Django + Postgres |
| Realism | Dev-only volume mounts, debug settings | Mirrors prod Postgres config |
| Cleanup | Manual `docker volume prune` if it gets dirty | `down -v` is the contract |
| Risk on `down -v` | Loses your dev data | Loses nothing of value |

The two stacks share the **Dockerfile** (same image), not the **compose file**.

### `docker-compose.test.yml` — recommended shape

```yaml
services:
  postgres-test:
    image: postgres:16
    environment:
      POSTGRES_DB: solicitudes_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports: ["55432:5432"]            # different port from dev (5432) to avoid conflicts
    tmpfs: /var/lib/postgresql/data  # in-memory; faster, no volume to clean
```

That's it. **No app container.** Django runs in-process via `live_server`, just talking to the Postgres container. Add Redis here only when initiative 007 (notifications + Celery) lands and a test genuinely exercises the worker.

### `config/settings/test_postgres.py` — opt-in

```python
from .base import *

DATABASES["default"] = {
    "ENGINE": "django.db.backends.postgresql",
    "HOST": "localhost",
    "PORT": "55432",
    "NAME": "solicitudes_test",
    "USER": "test",
    "PASSWORD": "test",
}

# Pytest-django will create/destroy the test DB inside this Postgres instance per session.
# Use --reuse-db locally to skip recreation on subsequent runs.
```

Default `dev.py` keeps SQLite. The Postgres path is reached only when you pass `--ds=config.settings.test_postgres`.

### Make targets — recommended

```makefile
e2e:
	pytest -m e2e

e2e-postgres:
	docker compose -f docker-compose.test.yml up -d
	pytest -m e2e --ds=config.settings.test_postgres; \
	rc=$$?; \
	docker compose -f docker-compose.test.yml down -v; \
	exit $$rc

e2e-headed:                 # debug a flaky test by watching it run
	pytest -m e2e --headed --slowmo 200
```

The `;` chain in `e2e-postgres` ensures `down -v` runs even when pytest fails — otherwise a crash leaves the test container running.

### Browsers

```bash
playwright install chromium     # once per workstation
playwright install firefox      # only if cross-browser tests are configured
```

In CI, install in a workflow step (cached by version):

```yaml
- run: pip install -r requirements.txt
- run: playwright install --with-deps chromium
```

`--with-deps` installs the system libraries Chromium needs on Linux runners.

### Test-DB lifecycle and `--reuse-db`

`pytest-django` creates the test DB once per session and drops it at the end. For fast local iteration:

```bash
pytest -m e2e --reuse-db                 # keep the test DB between runs
pytest -m e2e --reuse-db --create-db     # one-shot recreate (after migrations change)
```

This is independent of the tier — works for Tier 1 and Tier 2 the same way.

### What happens during a `pytest -m e2e` run

1. `pytest-django` decides the test-DB strategy (create or reuse).
2. The first test that requests `live_server` triggers the fixture: Django starts on `127.0.0.1:<random-free-port>`, attached to the test DB.
3. `pytest-playwright` launches Chromium in the configured headed/headless mode.
4. Each test gets a fresh `Page` (via the `page` fixture). DB state is rolled back per test.
5. On failure, traces / screenshots / videos land in `test-results/`.
6. The `live_server` and browser are torn down at session end.

No Compose. No manual `manage.py runserver`. No `RUNSERVER` shell window to remember.

### When you genuinely DO need full Compose

A small set of scenarios warrant `docker-compose.test.yml`:

- The test asserts on Postgres-specific SQL behavior (you'd get a wrong answer from SQLite).
- The test exercises the Celery worker path (initiative 007+) and you want a real Redis.
- You're reproducing a CI failure that only manifests against Postgres.
- Pre-merge sanity check ("does this still work against the realistic stack?").

For those: `make e2e-postgres`. For everything else: `make e2e`.

---

## Per-initiative tracking

Per initiative `plan.md`:

```markdown
## E2E coverage

### In-process integration (Tier 1)
- Cross-feature: notification dispatched on PENDIENTE → APROBADA transition
- Cross-feature: PDF generation triggered after APROBADA

### Browser (Tier 2)
- Golden path: alumno creates and submits solicitud
- Golden path: personal approves a pending solicitud
```

In `status.md`:

```markdown
### E2E
- [ ] Tier 1: cross-feature notification on transition
- [ ] Tier 2: alumno creates and submits (browser)
```

The `code-reviewer` agent will check these against `plan.md` like any other deliverable.
