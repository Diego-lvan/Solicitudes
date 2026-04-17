DC_DEV  := docker compose -f docker-compose.dev.yml
DC_TEST := docker compose -f docker-compose.test.yml
EXEC    := $(DC_DEV) exec -T web

.PHONY: help up down build logs shell migrate makemigrations \
        lint type test e2e e2e-postgres e2e-headed clean certs

help:  ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

certs:  ## Generate self-signed dev certs (mkcert preferred, openssl fallback)
	@mkdir -p certs
	@if [ -s certs/server.crt ] && [ -s certs/server.key ]; then \
	  echo "certs/ already populated; skipping"; \
	elif command -v mkcert >/dev/null 2>&1; then \
	  mkcert -install && mkcert -cert-file certs/server.crt -key-file certs/server.key localhost 127.0.0.1; \
	else \
	  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
	    -keyout certs/server.key -out certs/server.crt \
	    -subj "/CN=localhost" \
	    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"; \
	fi

up: certs  ## Start dev stack (nginx + web + db + mailhog)
	$(DC_DEV) up -d --build

down:  ## Stop dev stack
	$(DC_DEV) down

build:  ## Rebuild the web image
	$(DC_DEV) build web

logs:  ## Tail web logs
	$(DC_DEV) logs -f web

shell:  ## Django shell inside web
	$(EXEC) python manage.py shell

migrate:  ## Apply migrations against dev DB
	$(EXEC) python manage.py migrate

makemigrations:  ## Generate migrations
	$(EXEC) python manage.py makemigrations

lint:  ## ruff inside web
	$(EXEC) ruff check .

type:  ## mypy inside web
	$(EXEC) mypy .

test:  ## Unit + integration tests (in-process, SQLite)
	$(EXEC) pytest

e2e:  ## All Tier 1 + Tier 2 tests (in-process, SQLite, Playwright if installed)
	$(EXEC) pytest -m e2e

e2e-postgres:  ## Same as e2e against ephemeral Postgres
	$(DC_TEST) up -d --wait
	$(EXEC) pytest -m e2e --ds=config.settings.test_postgres; \
	rc=$$?; \
	$(DC_TEST) down -v; \
	exit $$rc

e2e-headed:  ## Browser tests with visible Chromium
	$(EXEC) pytest -m e2e --headed --slowmo 200

clean:  ## Stop everything, remove volumes
	$(DC_DEV) down -v
	$(DC_TEST) down -v
