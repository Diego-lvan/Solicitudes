# language: es
Característica: Acceso al sistema
  Como usuario de la Universidad Autónoma de Zacatecas
  Quiero iniciar sesión con mi rol
  Para acceder a las funciones que me corresponden

  Escenario: El alumno inicia sesión y llega a su perfil
    Dado que inicié sesión como "ALUMNO"
    Cuando navego a "/auth/me"
    Entonces veo el texto "ALUMNO_TEST"

  Escenario: Un visitante sin sesión es redirigido al login
    Dado que no he iniciado sesión
    Cuando navego a "/"
    Entonces la URL contiene "/auth/dev-login"
