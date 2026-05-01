# language: es
Característica: Catálogo de mentores con importación CSV y desactivación por periodo
  Como administrador
  Quiero gestionar el catálogo de mentores subiendo un CSV
  Para mantener actualizado el listado activo del periodo

  Antecedentes:
    Dado un usuario administrador autenticado

  Escenario: Importación CSV de mentores con filas válidas e inválidas (happy path)
    Cuando el administrador sube un CSV con encabezado "matricula" y filas "44444444|55555555|bad"
    Entonces la respuesta tiene código 200
    Y el resumen reporta 3 filas totales
    Y el resumen reporta 2 filas insertadas
    Y el resumen reporta 1 fila inválida

  Escenario: CSV con encabezado incorrecto se rechaza (alterno)
    Cuando el administrador sube un CSV con encabezado "alumno" y filas "44444444"
    Entonces la respuesta tiene código 422
    Y el formulario muestra error en el campo "archivo"

  Escenario: Usuario no administrador no puede acceder al import (alterno)
    Dado un usuario alumno autenticado
    Cuando el alumno consulta la pantalla de importación CSV
    Entonces la respuesta tiene código 403
