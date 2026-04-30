# language: es
Característica: Envío de correos transaccionales en el ciclo de vida de una solicitud
  Como sistema de solicitudes
  Quiero notificar por correo al solicitante y al staff cuando una solicitud
  cambia de estado
  Para que todos los involucrados estén informados sin acción manual

  Antecedentes:
    Dado un solicitante "Ada Alumno" con matrícula "ALU-1" y email "alu1@uaz.edu.mx"
    Y tres usuarios staff con rol Control Escolar
    Y una solicitud creada con folio "SOL-2026-00001" en estado CREADA

  Escenario: Envío exitoso al atender la solicitud (happy path)
    Cuando el staff "STAFF-1" atiende la solicitud
    Entonces se envía exactamente un correo al solicitante "alu1@uaz.edu.mx"
    Y el asunto del correo contiene el folio "SOL-2026-00001"
    Y el asunto del correo contiene la frase "en proceso"
    Y el correo incluye una alternativa HTML

  Escenario: Falla SMTP no rompe la transición ni propaga la excepción (alterno)
    Dado que el backend SMTP fallará en el próximo envío
    Cuando el staff "STAFF-1" atiende la solicitud
    Entonces la solicitud queda en estado EN_PROCESO
    Y la bandeja de salida queda vacía
    Y se registra una advertencia con el folio "SOL-2026-00001"
