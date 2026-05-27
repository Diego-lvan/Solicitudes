# language: es
Característica: Catálogo de plantillas PDF en el panel administrativo
  Como administrador del Sistema de Solicitudes de la UAZ
  Quiero gestionar el catálogo de plantillas de PDF
  Para mantener los documentos que genera el sistema

  Escenario: El administrador ve el listado de plantillas
    Dado que inicié sesión como "ADMIN"
    Cuando el administrador abre el catálogo de plantillas
    Entonces veo el texto "Plantillas de PDF"
    Y veo el texto "Constancia de Estudios"

  Escenario: El administrador abre el editor de una plantilla con preview en vivo
    Dado que inicié sesión como "ADMIN"
    Cuando el administrador abre el catálogo de plantillas
    Y el administrador edita la plantilla "Constancia de Estudios"
    Entonces veo el texto "Edita el HTML/CSS y observa el preview en vivo a la derecha."
    Y veo el texto "Preview"
    Y el administrador ve el editor de la plantilla "Constancia de Estudios"

  Escenario: Un alumno no puede entrar al catálogo de plantillas
    Dado que inicié sesión como "ALUMNO"
    Cuando el administrador abre el catálogo de plantillas
    Entonces el alumno recibe negación de acceso al catálogo de plantillas
    Y no veo el texto "Plantillas de PDF"
