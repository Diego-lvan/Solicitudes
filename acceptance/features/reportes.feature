# language: es
Característica: Dashboard administrativo de reportes
  Como administrador del Sistema de Solicitudes
  Quiero abrir el dashboard de reportes, filtrar por fecha y exportar a CSV
  Para dar seguimiento agregado a las solicitudes de la universidad

  Escenario: El administrador ve el dashboard de reportes con sus métricas
    Dado que inicié sesión como "ADMIN"
    Cuando navego a "/reportes/"
    Entonces veo el texto "Reportes y dashboard"
    Y veo el panel de totales del dashboard de reportes
    Y veo el desglose por estado y por tipo del dashboard de reportes

  Escenario: El administrador filtra por rango de fechas y la página recarga filtrada
    Dado que inicié sesión como "ADMIN"
    Cuando navego a "/reportes/"
    Y aplico un filtro de fechas del "2020-01-01" al "2020-01-31" en el dashboard de reportes
    Entonces la URL contiene "created_from=2020-01-01"
    Y la URL contiene "created_to=2020-01-31"
    Y veo el texto "Reportes y dashboard"

  Escenario: El administrador puede exportar el reporte a CSV
    Dado que inicié sesión como "ADMIN"
    Cuando navego a "/reportes/"
    Entonces el enlace de exportar CSV del dashboard apunta a la ruta de exportación CSV
    Y al exportar el CSV no llego al login ni a una página de error

  Escenario: Un alumno no puede entrar al dashboard de reportes
    Dado que inicié sesión como "ALUMNO"
    Cuando navego a "/reportes/"
    Entonces se me niega el acceso al dashboard de reportes
