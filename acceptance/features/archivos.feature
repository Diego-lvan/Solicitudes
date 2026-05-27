# language: es
Característica: Archivos adjuntos a una solicitud
  Como usuario del Sistema de Solicitudes
  Quiero adjuntar archivos a mi solicitud y descargarlos
  Para respaldar mi petición, sin que terceros sin relación accedan a ellos

  Escenario: El dueño adjunta un archivo y lo descarga desde el detalle (happy path)
    Dado que inicié sesión como "ALUMNO"
    Cuando creo una solicitud de constancia con un archivo adjunto
    Entonces veo el archivo adjunto en el detalle de mi solicitud
    Y veo el enlace de descarga del archivo adjunto
    Y al abrir el enlace de descarga no soy enviado al login ni a una página de error

  Escenario: Un usuario sin relación no puede descargar el archivo (acceso denegado)
    Dado que un alumno tiene una solicitud de constancia con un archivo adjunto
    Cuando inicio sesión como "DOCENTE" e intento abrir la descarga de ese archivo
    Entonces se me niega el acceso al archivo
