# language: es
Característica: Dashboard administrativo de reportes
  Como administrador
  Quiero ver totales agregados de solicitudes y exportarlos
  Para tomar decisiones a partir de la información del periodo

  Antecedentes:
    Dado un usuario administrador autenticado

  Escenario: Totales por estado en el dashboard (happy path)
    Dado dos solicitudes en estado CREADA del tipo "Constancia académica"
    Y una solicitud en estado FINALIZADA del tipo "Constancia académica"
    Cuando el administrador abre el dashboard
    Entonces la respuesta tiene código 200
    Y el dashboard muestra "Constancia"

  Escenario: Filtro por rango de fecha excluye solicitudes fuera de rango (alterno)
    Dado una solicitud creada el "2026-04-10"
    Y una solicitud creada el "2025-01-10"
    Cuando el administrador abre el dashboard con el filtro "2026-01-01" a "2026-12-31"
    Entonces la respuesta tiene código 200
    Y el total del dashboard es 1

  Escenario: Export CSV con encabezados y BOM (alterno)
    Dado dos solicitudes en estado CREADA del tipo "Constancia académica"
    Cuando el administrador exporta el reporte en CSV con estado "CREADA"
    Entonces la respuesta tiene código 200
    Y el Content-Type del CSV es "text/csv"
    Y el archivo CSV inicia con BOM UTF-8
    Y el CSV tiene exactamente 3 filas
