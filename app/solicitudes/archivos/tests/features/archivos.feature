# language: es
Característica: Descarga de archivos adjuntos a una solicitud
  Como solicitante o personal autorizado
  Quiero poder bajar los archivos que se subieron en una solicitud
  Para revisar comprobantes o documentos relacionados al trámite

  Escenario: El dueño de la solicitud descarga su archivo (happy path)
    Dado un alumno dueño "ALU-DUE" con un archivo subido a su solicitud
    Cuando el alumno solicita descargar su archivo
    Entonces la respuesta tiene código 200
    Y la respuesta incluye un header Content-Disposition de attachment

  Escenario: Un usuario no relacionado no puede descargar el archivo (alterno)
    Dado un alumno dueño "ALU-DUE" con un archivo subido a su solicitud
    Y un docente sin relación con esa solicitud
    Cuando el docente intenta descargar el archivo del alumno
    Entonces la respuesta tiene código 403
