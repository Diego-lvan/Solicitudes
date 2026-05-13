# language: es
Característica: Catálogo de plantillas PDF en el panel administrativo
  Como administrador del sistema
  Quiero consultar el catálogo de plantillas PDF que existen
  Para poder gestionar las plantillas que se usan al renderizar solicitudes con WeasyPrint

  Escenario: El administrador ve el listado de plantillas (happy path)
    Dado existe una plantilla "constancia-estudios" activa
    Y un administrador autenticado
    Cuando el administrador entra al listado de plantillas
    Entonces la respuesta tiene código 200
    Y el listado incluye la plantilla "constancia-estudios"

  Escenario: Un alumno no puede entrar al panel administrativo (alterno)
    Dado un alumno autenticado
    Cuando el alumno entra al listado de plantillas
    Entonces la respuesta tiene código 403
