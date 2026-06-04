#!/usr/bin/env bash
# Validación de calidad estática: PEP8/lint (ruff) + complejidad ciclomática (radon).
# Corre dentro del contenedor `web`. Sale con código !=0 si alguna validación falla.
#   ./quality.sh
# Excluye los tests de la complejidad (el límite ≤10 aplica al código de producción).
set -uo pipefail
cd "$(dirname "$0")"

DC="docker compose -f docker-compose.dev.yml"
EXCLUDE="*/tests/*,*/test_*.py"
fail=0

echo "==> PEP8 / lint  (ruff check .)"
if $DC exec -T web ruff check .; then
  echo "OK: ruff sin errores"
else
  echo "FALLA: ruff reportó errores"
  fail=1
fi

echo
echo "==> Asegurando radon en el contenedor"
$DC exec -T web sh -c 'command -v radon >/dev/null 2>&1 || pip install -q radon'

echo
echo "==> Complejidad ciclomática > 10  (radon cc -n C, sin tests) — debe estar vacío"
cc_out="$($DC exec -T web radon cc . -s -n C -e "$EXCLUDE")"
if [ -n "$cc_out" ]; then
  echo "$cc_out"
  echo "FALLA: hay métodos con complejidad ciclomática > 10"
  fail=1
else
  echo "OK: ningún método de producción supera complejidad 10"
fi

echo
echo "==> Resumen de complejidad (promedio)"
$DC exec -T web radon cc . -s -e "$EXCLUDE" --total-average | tail -2

echo
if [ "$fail" -eq 0 ]; then
  echo "TODO OK: PEP8 y complejidad ciclomática dentro de los límites."
else
  echo "HAY FALLAS: revisa la salida de arriba."
fi
exit "$fail"
