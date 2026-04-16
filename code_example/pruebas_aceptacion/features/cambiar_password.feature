Feature: Cambio Obligatorio de Contraseña
  Como usuario administrador nuevo
  Quiero cambiar mi contraseña predeterminada
  Para mantener la seguridad de mi cuenta

  Background:
    Given que existe el usuario admin con password "admin" que debe cambiar contraseña
    And el usuario admin está autenticado

  Scenario: Cambio obligatorio de contraseña para admin nuevo
    When el usuario intenta acceder a cualquier página del sistema
    Then es redirigido automáticamente a la página de cambio de contraseña
    And ve un mensaje indicando que debe cambiar su contraseña por seguridad

  Scenario: Cambio exitoso de contraseña
    Given que el usuario está en la página de cambio de contraseña
    When ingresa la contraseña actual "admin"
    And ingresa la nueva contraseña "NuevaPass123!"
    And confirma la nueva contraseña "NuevaPass123!"
    And hace clic en el botón de cambiar contraseña
    Then la contraseña se actualiza exitosamente
    And el flag debe_cambiar_password se establece en False
    And el usuario es redirigido a la página de completar perfil

  Scenario: Validación de contraseña débil rechazada
    Given que el usuario está en la página de cambio de contraseña
    When ingresa la contraseña actual "admin"
    And ingresa la nueva contraseña "123456"
    And confirma la nueva contraseña "123456"
    And hace clic en el botón de cambiar contraseña
    Then ve un mensaje de error indicando que la contraseña es demasiado común
    And permanece en la página de cambio de contraseña

  Scenario: Validación de contraseña corta rechazada
    Given que el usuario está en la página de cambio de contraseña
    When ingresa la contraseña actual "admin"
    And ingresa la nueva contraseña "Pass1!"
    And confirma la nueva contraseña "Pass1!"
    And hace clic en el botón de cambiar contraseña
    Then ve un mensaje de error indicando que la contraseña debe tener al menos 8 caracteres
    And permanece en la página de cambio de contraseña

  Scenario: Contraseñas nuevas no coinciden
    Given que el usuario está en la página de cambio de contraseña
    When ingresa la contraseña actual "admin"
    And ingresa la nueva contraseña "NuevaPass123!"
    And confirma la nueva contraseña "DiferentePass123!"
    And hace clic en el botón de cambiar contraseña
    Then ve un mensaje de error indicando que las contraseñas no coinciden
    And permanece en la página de cambio de contraseña

  Scenario: Contraseña actual incorrecta
    Given que el usuario está en la página de cambio de contraseña
    When ingresa la contraseña actual "contraseña_incorrecta"
    And ingresa la nueva contraseña "NuevaPass123!"
    And confirma la nueva contraseña "NuevaPass123!"
    And hace clic en el botón de cambiar contraseña
    Then ve un mensaje de error indicando que la contraseña actual es incorrecta
    And permanece en la página de cambio de contraseña

  Scenario: Contraseña muy similar al nombre de usuario rechazada
    Given que el usuario está en la página de cambio de contraseña
    When ingresa la contraseña actual "admin"
    And ingresa la nueva contraseña "admin123"
    And confirma la nueva contraseña "admin123"
    And hace clic en el botón de cambiar contraseña
    Then ve un mensaje de error indicando que la contraseña es muy similar al nombre de usuario
    And permanece en la página de cambio de contraseña

  Scenario: Usuario que ya cambió contraseña puede cambiarla nuevamente voluntariamente
    Given que existe un usuario "usuario_normal" que ya cambió su contraseña
    And el usuario "usuario_normal" está autenticado
    And que el usuario está en la página de cambio de contraseña
    When ingresa la contraseña actual "Pass123!"
    And ingresa la nueva contraseña "OtraPass456!"
    And confirma la nueva contraseña "OtraPass456!"
    And hace clic en el botón de cambiar contraseña
    Then la contraseña se actualiza exitosamente
    And el usuario es redirigido a la página de bienvenida

