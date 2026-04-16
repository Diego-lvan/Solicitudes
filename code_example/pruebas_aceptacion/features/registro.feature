
Feature: Registro de Nuevos Usuarios
  Como visitante del sistema
  Quiero poder registrarme con mi información personal
  Para crear una cuenta y acceder al sistema

  Scenario: Registro fallido de alumno sin matrícula
    When el usuario visita la página de registro
    And completa el formulario con los siguientes datos de alumno:
      | Campo       | Valor               |
      | username    | alumno_sin_mat      |
      | email       | sin_mat@test.com    |
      | first_name  | Sin                 |
      | last_name   | Matricula           |
      | rol         | alumno              |
      | matricula   |                     |
      | password1   | testpass123!        |
      | password2   | testpass123!        |
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error indicando que la matrícula es obligatoria para alumnos

  Scenario: Registro fallido con email duplicado
    Given que existe un usuario con email "duplicado@test.com"
    When el usuario visita la página de registro
    And completa el formulario con email "duplicado@test.com"
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error indicando que el email ya está registrado

  Scenario: Registro fallido con contraseñas que no coinciden
    When el usuario visita la página de registro
    And ingresa contraseñas diferentes en password1 y password2
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error de contraseñas no coincidentes

  Scenario: Validación de nombre con números rechazada
    When el usuario visita la página de registro
    And completa el formulario con first_name "Juan123"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error "El nombre solo puede contener letras y espacios"

  Scenario: Validación de apellido con caracteres especiales rechazada
    When el usuario visita la página de registro
    And completa el formulario con last_name "Pérez@#"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error "El apellido solo puede contener letras y espacios"

  Scenario: Validación de username duplicado rechazada
    Given que existe un usuario solamente con username "usuario_existente"
    When el usuario visita la página de registro
    And completa el formulario con username "usuario_existente"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error "Este nombre de usuario ya está en uso"

  Scenario: Validación de username con caracteres especiales rechazada
    When el usuario visita la página de registro
    And completa el formulario con username "usuario@invalido"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error "El nombre de usuario solo puede contener letras, números y guiones bajos"

  Scenario: Validación de teléfono con menos de 10 dígitos rechazada
    When el usuario visita la página de registro
    And completa el formulario con telefono "492123456"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error "El teléfono debe tener exactamente 10 dígitos"

  Scenario: Validación de teléfono con más de 10 dígitos rechazada
    When el usuario visita la página de registro
    And completa el formulario con telefono "49212345678"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error "El teléfono debe tener exactamente 10 dígitos"

  Scenario: Validación de teléfono con letras rechazada
    When el usuario visita la página de registro
    And completa el formulario con telefono "492abc4567"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error "El teléfono debe tener exactamente 10 dígitos"

  Scenario: Validación de matrícula con menos de 5 dígitos rechazada
    When el usuario visita la página de registro
    And completa el formulario de alumno con matricula "1234"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error "La matrícula debe tener entre 5 y 8 dígitos"

  Scenario: Validación de matrícula con más de 8 dígitos rechazada
    When el usuario visita la página de registro
    And completa el formulario de alumno con matricula "123456789"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error "La matrícula debe tener entre 5 y 8 dígitos"

  Scenario: Validación de matrícula duplicada rechazada
    Given que existe un usuario con matricula "12345"
    When el usuario visita la página de registro
    And completa el formulario de alumno con matricula "12345"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error "Esta matrícula ya está registrada"

  Scenario: Validación de contraseña muy corta rechazada
    When el usuario visita la página de registro
    And completa el formulario con password1 "Pass1!" y password2 "Pass1!"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error indicando que la contraseña debe tener al menos 8 caracteres

  Scenario: Validación de contraseña muy común rechazada
    When el usuario visita la página de registro
    And completa el formulario con password1 "password123" y password2 "password123"
    And completa el resto de campos correctamente
    And hace clic en el botón de registrar
    Then el usuario permanece en la página de registro
    And ve un error indicando que la contraseña es muy común

