# language: es
Característica: Catálogo de mentores con importación CSV
  Como administrador del Sistema de Solicitudes
  Quiero importar mentores desde un archivo CSV
  Para mantener el catálogo actualizado sin capturar uno por uno

  Escenario: El administrador importa un CSV con filas válidas e inválidas y ve el resumen
    Dado que inicié sesión como "ADMIN"
    Cuando el administrador abre la pantalla de importar mentores
    Entonces veo el texto "Importar mentores (CSV)"
    Cuando el administrador sube un CSV de mentores con filas válidas y una inválida
    Entonces el administrador ve el resumen de la importación de mentores
    Y veo el texto "Filas rechazadas"
    Y veo el texto "La matrícula debe tener 8 dígitos."

  Escenario: Un CSV con encabezado incorrecto se rechaza con un mensaje de error
    Dado que inicié sesión como "ADMIN"
    Cuando el administrador abre la pantalla de importar mentores
    Y el administrador sube un CSV de mentores con encabezado incorrecto
    Entonces el administrador ve el error de encabezado de mentores

  Escenario: Un alumno no puede acceder a la importación de mentores
    Dado que inicié sesión como "ALUMNO"
    Cuando el administrador abre la pantalla de importar mentores
    Entonces el alumno recibe negación de acceso a la importación de mentores
