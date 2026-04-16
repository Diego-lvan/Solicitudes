Feature: Ver detalles de una solicitud
  Como responsable (Control Escolar, Responsable de Programa, Responsable de Tutorías o Director)
  Quiero ver los detalles de una solicitud específica
  Para poder revisar la información completa y el historial de seguimiento

  Background:
    Given que existe un usuario con username "responsable1", contraseña "jfk42ijdS" y rol "control_escolar"
    And el usuario "responsable1" está autenticado en el sistema
    And existen las siguientes solicitudes con detalles asignadas a "control_escolar":
      | folio          | tipo_solicitud        | estado     |
      | SOL-CE-0001    | Constancia de Estudios | Creada     |
      | SOL-CE-0002    | Constancia de Estudios | En proceso |

  Scenario: Ver detalles de una solicitud
    Given el usuario visita la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0001"
    Then debe ver la página de detalles de la solicitud
    And debe ver el folio "SOL-CE-0001"
    And debe ver el tipo de solicitud "Constancia de Estudios"
    And debe ver el estado "Creada"
    And debe ver el historial de seguimiento
