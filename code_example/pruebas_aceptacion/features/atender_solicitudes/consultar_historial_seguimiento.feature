Feature: Consultar historial de seguimiento
  Como responsable (Control Escolar, Responsable de Programa, Responsable de Tutorías o Director)
  Quiero consultar el historial de seguimiento de una solicitud
  Para poder ver todos los cambios de estado y observaciones realizadas

  Background:
    Given que existe un usuario con username "responsable1", contraseña "jfk42ijdS" y rol "control_escolar"
    And el usuario "responsable1" está autenticado en el sistema
    And existen las siguientes solicitudes con historial asignadas a "control_escolar":
      | folio          | tipo_solicitud         | estado     |
      | SOL-CE-0001    | Constancia de Estudios | Creada     |
      | SOL-CE-0002    | Constancia de Estudios | En proceso |
      | SOL-CE-0003    | Constancia de Estudios | Terminada  |

  Scenario: Ver historial de una solicitud recién creada
    Given el usuario visita la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0001"
    Then debe ver el historial de seguimiento con las siguientes entradas:
      | Estado  | Observaciones                   |
      | Creada  | Solicitud creada por el usuario |

  Scenario: Ver historial de una solicitud en proceso
    Given el usuario visita la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0002"
    Then debe ver el historial de seguimiento con las siguientes entradas:
      | Estado     | Observaciones                     |
      | Creada     | Solicitud creada por el usuario   |
      | En proceso | La solicitud está siendo revisada |

  Scenario: Ver historial completo de una solicitud terminada
    Given el usuario visita la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0003"
    Then debe ver el historial de seguimiento con las siguientes entradas:
      | Estado     | Observaciones                     |
      | Creada     | Solicitud creada por el usuario   |
      | En proceso | La solicitud está siendo revisada |
      | Terminada  | Solicitud aprobada y procesada    |

  Scenario: Verificar que el historial muestra fechas
    Given el usuario visita la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0002"
    Then debe ver el historial de seguimiento
    And cada entrada del historial debe mostrar una fecha

  Scenario: Verificar orden cronológico del historial
    Given el usuario visita la página de "Solicitudes a Atender"
    When hace clic en el botón "Atender" de la solicitud con folio "SOL-CE-0003"
    Then el historial debe estar ordenado cronológicamente
