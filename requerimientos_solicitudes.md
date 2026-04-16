# Requerimientos del Sistema de Solicitudes

## RF1. Catalogo dinamico de tipos de solicitud

- El sistema debe permitir crear, editar y eliminar tipos de solicitud desde la interfaz (sin cambios en codigo).
- Cada tipo de solicitud define:
  - Nombre y descripcion.
  - Rol destinatario (a quien se le envia).
  - Si requiere pago (booleano).
  - Los campos/datos que necesita (formulario dinamico).
  - Los archivos requeridos (con tipo permitido y cantidad).
  - Si tiene una plantilla/template asociada (opcional).
- Ejemplos de tipos: constancias, kardex, convalidacion, apoyos, movilidad nacional/internacional, listas, SNI, estimulos, actas de examen.

## RF2. Formularios dinamicos por tipo de solicitud

- Cada tipo de solicitud tiene un formulario configurable con campos personalizados.
- Tipos de campo soportados: texto, area de texto, numero, fecha, seleccion (dropdown), archivo.
- Cada campo define: etiqueta, tipo, si es requerido, opciones (para selects), orden de aparicion.
- Los archivos pueden ser individuales o comprimidos

## RF3. Plantillas/Templates con variables

- El sistema debe soportar plantillas de documento para ciertos tipos de solicitud (ej. constancias).
- Las plantillas contienen variables sustituibles (ej. `{{nombre}}`, `{{matricula}}`, `{{programa}}`, `{{fecha}}`).
- Al generar el documento, el sistema reemplaza las variables con los datos del solicitante y de la solicitud, y genera un **PDF**.
- No todos los tipos requieren plantilla; es opcional por tipo.

## RF4. Creacion de solicitudes

- Un usuario autenticado (alumno o docente) puede crear una solicitud seleccionando un tipo del catalogo.
- El sistema presenta el formulario dinamico correspondiente al tipo.
- El usuario llena los campos y adjunta los archivos requeridos.
- Si el tipo requiere pago, el usuario debe adjuntar comprobante de pago (excepto si es alumno mentor, ver RF11).
- Al crear, se genera un folio unico para seguimiento.
- La solicitud se crea con estado **"Creada"**.

## RF5. Ciclo de vida de la solicitud (estados)

- **Creada**: estado inicial al enviar la solicitud.
- **En proceso**: el responsable la toma y comienza a atenderla.
- **Finalizada**: el responsable la resuelve.
- **Cancelada**: se cancela por el responsable o por el propio solicitante.
- Cada cambio de estado se registra con fecha, observaciones y quien lo realizo (seguimiento/historial).

## RF6. Enrutamiento por roles

- Las solicitudes se dirigen automaticamente al rol correspondiente segun el tipo de solicitud.
- Roles del sistema:
  - **Alumno**: crea solicitudes (constancias, kardex, convalidacion, apoyos, movilidad).
  - **Docente**: crea solicitudes (listas, constancias, SNI, estimulos).
  - **Departamento escolar (control escolar)**: atiende solicitudes asignadas a su rol.
  - **Responsable de programa**: atiende solicitudes asignadas a su rol.
  - **Administrador**: gestiona catalogo, usuarios, mentores, y tiene visibilidad total.
- El personal solo ve las solicitudes asignadas a su rol.

## RF7. Notificaciones por correo electronico

- Al crear una solicitud, se envia correo al responsable (o al grupo de usuarios con ese rol) notificando que hay una solicitud nueva.
- Se notifica al solicitante cuando cambie el estado de su solicitud (en proceso, finalizada, cancelada).

## RF8. Consulta y seguimiento de solicitudes

- El solicitante puede ver sus solicitudes y su estado actual.
- El solicitante puede ver el historial de seguimiento (cambios de estado con observaciones).
- El personal puede listar solicitudes con filtros: estado, tipo, fecha, folio, nombre del solicitante.

## RF9. Atencion de solicitudes

- El responsable puede ver el detalle completo: datos del formulario, archivos adjuntos, historial.
- El responsable puede cambiar el estado y agregar observaciones.
- Si el tipo tiene plantilla, el responsable puede generar el documento PDF resultante.

## RF10. Gestion de archivos adjuntos

- Soporte para subir archivos individuales y comprimidos (.zip).
- Los archivos se organizan por folio de solicitud.
- El personal puede descargar los archivos adjuntos.

## RF11. Gestion de alumnos mentores

- El administrador puede gestionar una lista de alumnos mentores activos.
- Se pueden agregar mentores de forma manual (por matricula) o mediante carga de archivo CSV.
- Los alumnos que esten en la lista de mentores quedan exentos de pago en los tipos de solicitud que lo requieran.
- La lista es pequena y se actualiza periodicamente.

---

## Requerimientos No Funcionales

### RNF1. Autenticacion externa

- El sistema no maneja autenticacion propia. Recibe un token (JWT) de un servicio externo (provider).
- Del token se extraen datos basicos: matricula, correo, rol.

### RNF2. Integracion con sistema externo (SIGA)

- El sistema puede consultar datos de alumnos/docentes a un servicio externo (SIGA) via API usando la matricula.
- Esto permite obtener informacion completa (nombre, programa, etc.) sin duplicar datos.

### RNF3. Servicio independiente

- Solicitudes es un microservicio. No depende de otros modulos para su logica de negocio, solo consume APIs externas para autenticacion y datos de usuarios.

### RNF4. Log de actividad

- Registrar acciones relevantes de los usuarios (creacion, cambios de estado, etc.) para auditoria.

### RNF5. Metricas y reportes

- Dashboard con estadisticas: solicitudes por tipo, por estado, por periodo.
- Exportacion de reportes (CSV/PDF).
