Feature: Listar solicitudes asignadas a atender
  Como responsable (Control Escolar, Responsable de Programa, Responsable de Tutorías o Director)
  Quiero ver una lista de todas las solicitudes asignadas a mi rol
  Para poder gestionar y dar seguimiento a las solicitudes pendientes

  Background:
    Given que existe un usuario con username "responsable1", contraseña "jfk42ijdS" y rol "control_escolar"
    And el usuario "responsable1" está autenticado en el sistema
    And existen las siguientes solicitudes asignadas a "control_escolar":
      | folio          | tipo_solicitud         | estado     |
      | SOL-CE-0001    | Constancia de Estudios | Creada     |
      | SOL-CE-0002    | Constancia de Estudios | En proceso |
      | SOL-CE-0003    | Constancia de Estudios | En proceso |

  Scenario: Ver listado de solicitudes asignadas
    When el usuario visita la página de "Solicitudes a Atender"
    Then debe ver una tabla con las siguientes columnas:
      | Folio      | Tipo de Solicitud | Estado     | Acción |
    And la tabla muestra las siguientes filas:
      | Folio          | Tipo de Solicitud      | Estado     |
      | SOL-CE-0001    | Constancia de Estudios | Creada     |
      | SOL-CE-0002    | Constancia de Estudios | En Proceso |
      | SOL-CE-0003    | Constancia de Estudios | En Proceso |

  Scenario: Filtrar solicitudes por estado
    Given el usuario visita la página de "Solicitudes a Atender"
    When aplica el filtro por estado "En proceso"
    Then la tabla solo muestra las siguientes filas:
      | Folio          | Tipo de Solicitud      | Estado     |
      | SOL-CE-0002    | Constancia de Estudios | En Proceso |
      | SOL-CE-0003    | Constancia de Estudios | En Proceso |
    And la cantidad de solicitudes mostradas es 2

  Scenario: Buscar una solicitud por folio
    Given el usuario visita la página de "Solicitudes a Atender"
    When escribe "SOL-CE-0002" en el campo de búsqueda de folio
    Then la tabla muestra solo la siguiente fila:
      | Folio          | Tipo de Solicitud      | Estado     |
      | SOL-CE-0002    | Constancia de Estudios | En Proceso |
    And la cantidad de solicitudes mostradas es 1

  Scenario: Ver listado sin solicitudes asignadas
    Given no existen solicitudes asignadas a "control_escolar"
    When el usuario visita la página de "Solicitudes a Atender"
    Then debe ver un mensaje indicando que no hay solicitudes
    And la tabla no muestra ninguna fila

  Scenario: Buscar una solicitud por folio que no existe
    Given el usuario visita la página de "Solicitudes a Atender"
    When escribe "SOL-XX-9999" en el campo de búsqueda de folio
    Then debe ver un mensaje indicando que no hay solicitudes
    And la tabla no muestra ninguna fila
