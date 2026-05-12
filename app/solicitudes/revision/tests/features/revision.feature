# language: es
Característica: Cola de revisión para personal responsable
  Como personal de Control Escolar
  Quiero ver únicamente las solicitudes que me toca revisar
  Para atender los trámites que corresponden a mi rol

  Escenario: Control Escolar ve solo solicitudes de su rol responsable (happy path)
    Dado un tipo "ce-tipo" cuyo responsable es Control Escolar con una solicitud "SOL-2026-10001"
    Y un tipo "rp-tipo" cuyo responsable es Responsable de Programa con una solicitud "SOL-2026-10002"
    Y un usuario de Control Escolar autenticado
    Cuando consulta la cola de revisión
    Entonces la respuesta tiene código 200
    Y la cola contiene el folio "SOL-2026-10001"
    Y la cola no contiene el folio "SOL-2026-10002"

  Escenario: Un alumno no puede entrar a la cola de revisión (alterno)
    Dado un alumno autenticado
    Cuando entra a la cola de revisión
    Entonces la respuesta tiene código 403
