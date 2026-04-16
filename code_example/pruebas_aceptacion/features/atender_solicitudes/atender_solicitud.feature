Feature: Atender una solicitud
  Como responsable (Control Escolar, Responsable de Programa, Responsable de Tutorías o Director)
  Quiero atender las solicitudes asignadas a mi rol
  Para poder cambiar su estado y agregar observaciones de seguimiento

  Background:
    Given que existe un usuario con username "responsable1", contraseña "jfk42ijdS" y rol "control_escolar"
    And el usuario "responsable1" está autenticado en el sistema
    And existen las siguientes solicitudes asignadas a "control_escolar":
      | folio          | tipo_solicitud         | estado     |
      | SOL-CE-0001    | Constancia de Estudios | Creada     |
      | SOL-CE-0002    | Constancia de Estudios | En proceso |

  Scenario: Cambiar estado de una solicitud a "En proceso"
    Given el usuario visita la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0001"
    And empiezo a revisar la solicitud
    Then debe ver un mensaje "La solicitud fue marcada como En proceso."
    And la solicitud "SOL-CE-0001" debe tener el estado "En proceso"

  Scenario: Cambiar estado de una solicitud a "Terminada"
    Given el usuario visita la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0001"
    And empiezo a revisar la solicitud
    Then debe ver un mensaje "La solicitud fue marcada como En proceso."
    And selecciona el estado "Terminada"
    And escribe "Constancia generada y entregada al estudiante" en el campo de observaciones
    And hace clic en el botón "Guardar"
    Then debe ver un mensaje "Solicitud cerrada correctamente."
    And la solicitud "SOL-CE-0002" debe tener el estado "Terminada"

  Scenario: Cancelar una solicitud
    Given el usuario visita la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0001"
    And empiezo a revisar la solicitud
    Then debe ver un mensaje "La solicitud fue marcada como En proceso."
    And selecciona el estado "Cancelada"
    And escribe "Solicitud cancelada por documentación incompleta" en el campo de observaciones
    And hace clic en el botón "Guardar"
    Then debe ver un mensaje "Solicitud cerrada correctamente."
    And la solicitud "SOL-CE-0001" debe tener el estado "Cancelada"

  Scenario: Atender solicitud sin agregar observaciones
    Given el usuario visita la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0001"
    And empiezo a revisar la solicitud
    Then debe ver un mensaje "La solicitud fue marcada como En proceso."
    And selecciona el estado "Cancelada"
    And hace clic en el botón "Guardar"
    Then debe ver un mensaje "Las observaciones son obligatorias al cerrar la solicitud."

  Scenario: Regresar sin guardar cambios
    Given el usuario visita la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0001"
    And empiezo a revisar la solicitud
    Then debe ver un mensaje "La solicitud fue marcada como En proceso."
    And hace clic en el botón "Cancelar"
    Then debe regresar a la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0001"
    And la solicitud "SOL-CE-0001" debe tener el estado "En proceso"
