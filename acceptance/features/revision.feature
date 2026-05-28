# language: es
Característica: Cola de revisión para el personal responsable
  Como personal responsable de la Universidad Autónoma de Zacatecas
  Quiero ver y atender las solicitudes asignadas a mi rol
  Para dar seguimiento a los trámites que me corresponden

  Escenario: Control Escolar ve en su cola una solicitud que le corresponde
    Dado que un alumno registró una solicitud de "constancia-de-estudios" para revisión
    Cuando ingresa Control Escolar a la cola de revisión
    Entonces se muestra el encabezado de la cola de revisión
    Y la cola de revisión muestra las columnas de folio, solicitante y estado
    Y la cola de revisión incluye la solicitud recién registrada

  Escenario: Control Escolar atiende una solicitud y cambia a EN PROCESO
    Dado que un alumno registró una solicitud de "constancia-de-estudios" para revisión
    Cuando Control Escolar abre el detalle de la solicitud registrada
    Y Control Escolar pulsa el botón de atender la solicitud
    Entonces el detalle de revisión muestra el estado "En proceso"

  Escenario: Un alumno no puede entrar a la cola de revisión
    Dado que inicié sesión como "ALUMNO"
    Cuando ingreso a la cola de revisión sin permisos
    Entonces se muestra la negación de acceso a la revisión
