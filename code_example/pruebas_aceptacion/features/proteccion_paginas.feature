Feature: Protección de Páginas del Sistema
  Como sistema de control de acceso
  Quiero proteger las páginas que requieren autenticación
  Para garantizar que solo usuarios autorizados accedan a funcionalidades específicas

  Scenario: Acceso a gestión de usuarios requiere rol de administrador
    Given que existe un usuario con username "alumno_test" y rol "alumno"
    And el usuario "alumno_test" está autenticado
    When el usuario intenta acceder a "/auth/usuarios/"
    Then el usuario es redirigido a la página de bienvenida
    And ve un mensaje indicando acceso no autorizado

  Scenario: Usuario no admin no ve opción "Gestionar Usuarios" en el menú
    Given que existe un usuario con username "alumno_test" y rol "alumno"
    And el usuario "alumno_test" está autenticado
    When el usuario visita la página de bienvenida
    Then no ve el enlace "Gestionar Usuarios" en el menú de navegación

  Scenario: Usuario administrador ve opción "Gestionar Usuarios" en el menú
    Given que existe un administrador con username "admin"
    And el administrador "admin" está autenticado
    When el administrador visita cualquier página del sistema
    Then ve el enlace "Gestionar Usuarios" en el menú de navegación

  Scenario: Middleware redirige a cambiar contraseña si debe_cambiar_password es True
    Given que existe un usuario "nuevo_usuario" con debe_cambiar_password en True
    And el usuario "nuevo_usuario" está autenticado
    When el usuario intenta acceder a "/solicitudes/"
    Then es redirigido a "/auth/cambiar-password/"
    And no puede acceder a otras páginas hasta cambiar su contraseña

  Scenario: Middleware redirige a completar perfil si perfil_completo es False
    Given que existe un usuario "usuario_perfil_incompleto" con perfil_completo en False
    And el usuario ya cambió su contraseña
    And el usuario "usuario_perfil_incompleto" está autenticado
    When el usuario intenta acceder a "/solicitudes/"
    Then es redirigido a "/auth/perfil/"
    And no puede acceder a otras páginas hasta completar su perfil


