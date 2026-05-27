# language: es
Característica: Alta de solicitudes desde la pantalla del alumno
  Como alumno de la Universidad Autónoma de Zacatecas
  Quiero crear solicitudes desde el catálogo de tipos
  Para tramitar los documentos académicos que necesito

  Escenario: El alumno ve el catálogo de tipos disponibles
    Dado que inicié sesión como "ALUMNO"
    Cuando el alumno abre el catálogo de solicitudes
    Entonces veo el texto "Crear solicitud"
    Y veo el texto "Constancia de Estudios"

  Escenario: El alumno llena el formulario dinámico y crea una solicitud
    Dado que inicié sesión como "ALUMNO"
    Cuando el alumno abre el formulario del tipo "constancia-de-estudios"
    Entonces veo el texto "Constancia de Estudios"
    Cuando el alumno llena los campos del formulario dinámico
    Y el alumno envía el formulario de la solicitud
    Entonces la URL contiene "/solicitudes/SOL-"
    Y el alumno ve el folio de su nueva solicitud
    Cuando el alumno abre la lista de mis solicitudes
    Entonces el alumno ve el folio de su nueva solicitud en la lista

  Escenario: Un visitante sin sesión es bloqueado del catálogo
    Dado que no he iniciado sesión
    Cuando el alumno abre el catálogo de solicitudes
    Entonces la URL contiene "/auth/dev-login"
