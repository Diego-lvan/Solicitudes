Feature: Completar Perfil de Usuario
  Como usuario nuevo del sistema
  Quiero completar mi información de perfil
  Para tener acceso completo a las funcionalidades del sistema

  Background:
    Given que existe un usuario "usuario_nuevo" que ya cambió su contraseña
    And el usuario tiene perfil_completo en False
    And el usuario "usuario_nuevo" está autenticado

  Scenario: Redirección automática a perfil incompleto
    When el usuario intenta acceder a la página de bienvenida
    Then es redirigido automáticamente a la página de completar perfil
    And ve un formulario con sus datos básicos prellenados

  Scenario: Completar perfil exitosamente
    Given que el usuario está en la página de completar perfil
    When completa los campos requeridos:
      | Campo       | Valor               |
      | first_name  | Juan                |
      | last_name   | Pérez               |
      | email       | juan@test.com       |
      | telefono    | 4921234567          |
      | area        | Ingeniería          |
      | matricula   | 12345               |
    And hace clic en el botón de guardar
    Then el perfil se actualiza exitosamente
    And el flag perfil_completo se establece en True
    And el usuario es redirigido a la página de bienvenida

  Scenario: Validación de nombre con números rechazada
    Given que el usuario está en la página de completar perfil
    When ingresa "Juan123" en el campo first_name
    And completa los demás campos correctamente
    And hace clic en el botón de guardar
    Then ve un mensaje de error "El nombre solo puede contener letras y espacios"
    And permanece en la página de completar perfil

  Scenario: Validación de apellido con caracteres especiales rechazada
    Given que el usuario está en la página de completar perfil
    When ingresa "Pérez@" en el campo last_name
    And completa los demás campos correctamente
    And hace clic en el botón de guardar
    Then ve un mensaje de error "El apellido solo puede contener letras y espacios"
    And permanece en la página de completar perfil

  Scenario: Validación de email duplicado rechazada
    Given que existe otro usuario con email "existente@test.com"
    And el usuario está en la página de completar perfil
    When ingresa "existente@test.com" en el campo email
    And completa los demás campos correctamente
    And hace clic en el botón de guardar
    Then ve un mensaje de error "Este correo electrónico ya está registrado"
    And permanece en la página de completar perfil

  Scenario: Validación de teléfono con formato incorrecto (menos de 10 dígitos)
    Given que el usuario está en la página de completar perfil
    When ingresa "492123456" en el campo telefono
    And completa los demás campos correctamente
    And hace clic en el botón de guardar
    Then ve un mensaje de error "El teléfono debe tener exactamente 10 dígitos"
    And permanece en la página de completar perfil

  Scenario: Validación de teléfono con formato incorrecto (más de 10 dígitos)
    Given que el usuario está en la página de completar perfil
    When ingresa "49212345678" en el campo telefono
    And completa los demás campos correctamente
    And hace clic en el botón de guardar
    Then ve un mensaje de error "El teléfono debe tener exactamente 10 dígitos"
    And permanece en la página de completar perfil

  Scenario: Validación de teléfono con letras rechazada
    Given que el usuario está en la página de completar perfil
    When ingresa "492abc4567" en el campo telefono
    And completa los demás campos correctamente
    And hace clic en el botón de guardar
    Then ve un mensaje de error "El teléfono debe tener exactamente 10 dígitos"
    And permanece en la página de completar perfil

  Scenario: Validación de matrícula fuera de rango (menos de 5 dígitos)
    Given que el usuario está en la página de completar perfil
    When ingresa "1234" en el campo matricula
    And completa los demás campos correctamente
    And hace clic en el botón de guardar
    Then ve un mensaje de error "La matrícula debe tener entre 5 y 8 dígitos"
    And permanece en la página de completar perfil

  Scenario: Validación de matrícula fuera de rango (más de 8 dígitos)
    Given que el usuario está en la página de completar perfil
    When ingresa "123456789" en el campo matricula
    And completa los demás campos correctamente
    And hace clic en el botón de guardar
    Then ve un mensaje de error "La matrícula debe tener entre 5 y 8 dígitos"
    And permanece en la página de completar perfil

  Scenario: Validación de matrícula duplicada rechazada
    Given que existe otro usuario con matricula "12345"
    And el usuario está en la página de completar perfil
    When ingresa "12345" en el campo matricula
    And completa los demás campos correctamente
    And hace clic en el botón de guardar
    Then ve un mensaje de error "Esta matrícula ya está registrada"
    And permanece en la página de completar perfil

  Scenario: Usuario puede mantener su email actual al actualizar perfil
    Given que el usuario tiene email "propio@test.com" en su perfil
    And el usuario está en la página de completar perfil
    When mantiene el email "propio@test.com"
    And completa los demás campos correctamente
    And hace clic en el botón de guardar
    Then el perfil se actualiza exitosamente sin error de email duplicado
