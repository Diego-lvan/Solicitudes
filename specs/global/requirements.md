# Requirements — Sistema de Solicitudes

## Visión

Sistema web para gestionar solicitudes académicas y administrativas de la Universidad Autónoma de Zacatecas. Reemplaza procesos manuales (papel, correo) con un flujo digital trazable.

## Usuarios

| Rol | Crea solicitudes | Atiende solicitudes | Administra |
|-----|-----------------|--------------------:|:----------:|
| Alumno | Sí (constancias, kardex, convalidación, apoyos, movilidad) | No | No |
| Docente | Sí (listas, constancias, SNI, estímulos) | No | No |
| Control Escolar | No | Sí (las asignadas a su rol) | No |
| Responsable de Programa | No | Sí (las asignadas a su rol) | No |
| Administrador | No | No (visibilidad total) | Sí (catálogo, usuarios, mentores) |

## Requerimientos Funcionales

### RF-01: Catálogo dinámico de tipos de solicitud
El administrador crea/edita/elimina tipos de solicitud sin tocar código. Cada tipo define: nombre, descripción, rol responsable, si requiere pago, roles creadores (alumno/docente/ambos), y plantilla opcional.

### RF-02: Formularios dinámicos
Cada tipo tiene campos configurables: texto, textarea, número, fecha, select, archivo. Cada campo: etiqueta, tipo, requerido, opciones, orden.

### RF-03: Plantillas con variables
Plantillas de documento con variables (`{{nombre}}`, `{{matricula}}`, etc.). El sistema genera PDF sustituyendo variables. Opcional por tipo.

### RF-04: Creación de solicitudes
Usuario autenticado selecciona tipo → ve formulario dinámico → llena y adjunta archivos → se genera folio único → estado "Creada". Si requiere pago y no es mentor, adjunta comprobante.

### RF-05: Ciclo de vida (estados)
Creada → En proceso → Finalizada. Creada → Cancelada. En proceso → Cancelada. Solicitante cancela solo en "Creada". Cada transición: fecha + responsable + observaciones.

### RF-06: Enrutamiento por roles
Solicitudes se dirigen automáticamente al rol responsable definido en el tipo. Personal solo ve sus asignadas. Admin ve todo.

### RF-07: Notificaciones por correo
Correo al responsable al crear solicitud. Correo al solicitante al cambiar estado. Si SMTP falla, la operación no se afecta.

### RF-08: Consulta y seguimiento
Solicitante: lista con folio/tipo/fecha/estado + filtros. Personal: lista asignadas con filtros. Ambos: historial de seguimiento.

### RF-09: Atención de solicitudes
Personal ve detalle completo (formulario, archivos, historial). Cambia estado, agrega observaciones, genera PDF si aplica.

### RF-10: Gestión de archivos adjuntos
Carga individual y .zip. Organizados por folio. Personal descarga desde detalle.

### RF-11: Gestión de alumnos mentores
Admin gestiona lista de mentores. Alta manual por matrícula o CSV. Mentores exentos de comprobante de pago.

## Requerimientos No Funcionales

### RNF-01: Autenticación externa
No maneja auth propia. Recibe JWT de proveedor externo. Del token: matrícula, correo, rol.

### RNF-02: Integración con SIGA
Consulta datos de usuario por matrícula vía API REST. Fallback a datos del JWT si SIGA no responde (5s timeout).

### RNF-03: Servicio independiente
Microservicio con DB propia. Sin dependencias de código con otros módulos.

### RNF-04: Log de actividad
Registrar acciones relevantes para auditoría.

### RNF-05: Métricas y reportes
Dashboard con estadísticas por tipo/estado/periodo. Exportación CSV/PDF.

## Interfaces Externas

| ID | Sistema | Dirección | Protocolo | Datos |
|----|---------|-----------|-----------|-------|
| IE-01 | Proveedor JWT | Entrada | HTTPS | matrícula, correo, rol |
| IE-02 | SIGA | Salida | REST/HTTPS | nombre, programa, semestre, correo |
| IE-03 | SMTP | Salida | SMTP/TLS | Notificaciones por evento |

## Restricciones

- RT-01: Auth delegada (no login/registro propio)
- RT-02: Microservicio independiente
- RT-03: DB propia (no accede a DBs externas)
- RT-04: HTTPS obligatorio (TLS 1.2+)
- RT-05: Chrome, Firefox, Edge, Safari actuales
- RT-06: No procesa pagos (solo adjunta comprobante)
- RT-07: Max 10MB por archivo
- RT-08: Interfaz en español (México)
