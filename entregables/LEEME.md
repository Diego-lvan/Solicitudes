# Entrega — Proyecto Final · Sistema de Solicitudes (UAZ)

Licenciatura en Ingeniería de Software · Materia de Testing · Junio 2026

**Equipo:** Diego Iván Correa Navarrete · Juan Antonio González del Río · Diego Arturo Ramos Ávila · Ángel David Carlos Silva

Este paquete reúne todos los entregables solicitados. Abajo se mapea cada punto
del checklist del proyecto final a su archivo correspondiente.

## Checklist de entregables

| # | Entregable | Ubicación |
|---|---|---|
| 1 | **Código fuente y pruebas unitarias** | `codigo_fuente/app/` (769 pruebas con pytest; 714 funciones de test únicas) |
| 2 | **Pruebas de Aceptación (behave y Selenium)** | `codigo_fuente/acceptance/` (7 features, 20 escenarios Gherkin en español) |
| 3 | **Matriz de Trazabilidad** | `pruebas/Matriz_de_Trazabilidad.xlsx` (Historia de Usuario → Requerimiento Técnico → Casos de prueba) |
| 4 | **Plan de prueba** | `documentacion/01_Plan_de_Prueba.pdf` |
| 5 | **Plantilla de casos de prueba** | `pruebas/Plantilla_de_Casos_de_Prueba.xlsx` (un renglón por función de prueba) |
| 6 | **Pruebas de performance (JMeter)** | `pruebas/performance/solicitudes_performance.jmx` (2 casos: login 10 usuarios, alta 5 usuarios) |
| 7 | **SRS** | `documentacion/02_SRS.pdf` |
| 8 | **SDD** | `documentacion/03_SDD.pdf` |
| 9 | **Visión y alcance** | `documentacion/04_Vision_y_Alcance.pdf` |
| 10 | **Esquema de base de datos** | `documentacion/05_Esquema_de_Base_de_Datos.pdf` (diagrama ER + diccionario de datos) |
| 11 | **Manual de usuario** | `documentacion/06_Manual_de_Usuario.pdf` (con 22 capturas) |
| 12 | **Manual técnico** | `documentacion/07_Manual_Tecnico.pdf` |

## Evidencia de calidad (requisitos del rubric)

| Requisito | Evidencia |
|---|---|
| Cobertura de código (objetivo 100%) | `pruebas/reportes_calidad/cobertura.txt` y `reportes_calidad/htmlcov/index.html` |
| Complejidad ciclomática ≤ 10 | `pruebas/reportes_calidad/complejidad_ciclomatica.txt` (todos los métodos ≤ 10; promedio A) |
| Índice de mantenibilidad | `pruebas/reportes_calidad/mantenibilidad.txt` (radon mi) |
| PEP8 | Verificado con `ruff check .` — sin errores |
| Metodología TDD | Escenarios primero (Gherkin/behave) y pruebas unitarias antes del código |

## Cómo ejecutar (resumen)

```sh
# 1. Levantar el sistema (Docker)
make up && make migrate && make seed       # o el docker compose equivalente

# 2. Pruebas unitarias + integración + cobertura
make coverage                              # pytest -m "not e2e" --cov

# 3. Complejidad ciclomática
radon cc app -s -n C                       # no debe reportar métodos C/D/E/F (>10)

# 4. Pruebas de aceptación (behave + selenium) — requiere el stack arriba + Chrome
cd acceptance && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/behave

# 5. Performance (JMeter)
jmeter -n -t pruebas/performance/solicitudes_performance.jmx -l resultados.jtl
```

Ver `codigo_fuente/README.md` y `documentacion/07_Manual_Tecnico.pdf` para el detalle.
