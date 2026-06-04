#!/usr/bin/env bash
# Pruebas unitarias + integración (pytest, SIN Playwright).
# Corre dentro del contenedor `web`. Pasa args extra a pytest, p.ej:
#   ./test-unit.sh app/solicitudes/tests/test_services.py
set -euo pipefail
cd "$(dirname "$0")"
docker compose -f docker-compose.dev.yml exec -T web pytest -m "not e2e" "$@"
