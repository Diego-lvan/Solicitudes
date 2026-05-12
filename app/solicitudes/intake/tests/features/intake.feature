# language: es
Característica: Alta de solicitudes desde la pantalla del alumno
  Como alumno autenticado
  Quiero poder ver los tipos de solicitud disponibles y entrar a crear una
  Para que pueda iniciar mi trámite académico desde el portal

  Antecedentes:
    Dado existe un tipo de solicitud "constancia-estudios" activo para rol alumno

  Escenario: El alumno ve el catálogo de tipos disponibles (happy path)
    Dado un alumno autenticado con matrícula "ALU100"
    Cuando el alumno entra al catálogo de solicitudes
    Entonces la respuesta tiene código 200
    Y el catálogo lista el tipo "constancia-estudios"

  Escenario: Visitante sin sesión es bloqueado (alterno)
    Dado un visitante sin sesión iniciada
    Cuando entra al catálogo de solicitudes
    Entonces la respuesta no es 200
