#!/usr/bin/env bash
# Pruebas unitarias + integración (pytest, SIN Playwright) con cobertura.
# Corre dentro del contenedor `web`. Pasa args extra a pytest, p.ej:
#   ./test-unit.sh app/solicitudes/tests/test_services.py
# Al terminar imprime el reporte de cobertura (term-missing) y genera el
# reporte HTML en app/htmlcov/ (abrir app/htmlcov/index.html).
set -euo pipefail
cd "$(dirname "$0")"
docker compose -f docker-compose.dev.yml exec -T web \
  pytest -m "not e2e" --cov --cov-report=term-missing --cov-report=html "$@"
echo
echo "Reporte HTML: app/htmlcov/index.html"
