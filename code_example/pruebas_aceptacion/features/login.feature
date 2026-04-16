
Feature: Gestión de Login de Usuarios
  Como usuario del sistema
  Quiero poder iniciar sesión con mis credenciales
  Para acceder a las funcionalidades del sistema según mi rol

  Scenario: Login exitoso con credenciales válidas
    Given que existe un usuario con username "alumno_test" y password "testpass123" y rol "alumno"
    When el usuario visita la página de login
    And ingresa username "alumno_test" y password "testpass123"
    And hace clic en el botón de iniciar sesión
    Then el usuario es redirigido a la página de bienvenida
    And ve el mensaje "Bienvenid@"

  Scenario: Login fallido con credenciales incorrectas
    Given que existe un usuario con username "alumno_test" y password "testpass123" y rol "alumno"
    When el usuario visita la página de login
    And ingresa username "alumno_test" y password "wrongpassword"
    And hace clic en el botón de iniciar sesión
    Then el usuario permanece en la página de login
    And ve el mensaje "Usuario o contraseña incorrectos"

  Scenario: Login con usuario inexistente
    When el usuario visita la página de login
    And ingresa username "usuario_inexistente" y password "cualquier_pass"
    And hace clic en el botón de iniciar sesión
    Then el usuario permanece en la página de login
    And ve el mensaje "Usuario o contraseña incorrectos"

  Scenario: Acceso a página protegida sin autenticación
    When el usuario intenta acceder a la página de perfil sin estar autenticado
    Then el usuario es redirigido a la página de login

  Scenario: Logout exitoso
    Given que el usuario "alumno_test" está autenticado
    When el usuario hace clic en cerrar sesión
    Then el usuario es redirigido a la página de login

  Scenario: Ver credenciales admin predeterminadas en primera vez
    Given que existe el usuario admin por defecto que debe cambiar contraseña
    When el usuario visita la página de login
    Then ve un mensaje informativo con las credenciales predeterminadas
    And el mensaje muestra "Usuario: admin"
    And el mensaje muestra "Contraseña: admin"
    And el mensaje indica que debe cambiar la contraseña

  Scenario: Login admin y redirección automática a cambio de contraseña
    Given que existe el usuario admin con password "admin" que debe cambiar contraseña
    When el usuario visita la página de login
    And ingresa username "admin" y password "admin"
    And hace clic en el botón de iniciar sesión
    Then el usuario es redirigido a la página de cambio de contraseña
    And ve el mensaje indicando que debe cambiar su contraseña

  Scenario: Credenciales admin no se muestran después de cambiar contraseña
    Given que existe el usuario admin que ya cambió su contraseña
    When el usuario visita la página de login
    Then no ve el mensaje con las credenciales predeterminadas
    And solo ve el formulario de login normal

  Scenario: Usuario con perfil incompleto es redirigido después del login
    Given que existe un usuario con username "usuario_perfil_incompleto" y perfil incompleto
    And el usuario ya cambió su contraseña
    When el usuario visita la página de login
    And ingresa username "usuario_perfil_incompleto" y su password
    And hace clic en el botón de iniciar sesión
    Then el usuario es redirigido a la página de completar perfil
