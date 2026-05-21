# Plantilla Editor & Asset Library — Requirements

## Purpose

El editor actual de plantillas PDF (admin) es un formulario plano con dos textareas (HTML y CSS) y una lista textual de variables disponibles. Para insertar una variable el admin debe leerla, copiarla y pegarla; el preview vive solo en la página de detail (después de guardar), por lo que iterar requiere un ciclo guardar → navegar → revisar. Además no hay forma de subir imágenes propias: solo URLs públicas externas funcionan, lo que vuelve impráctico embeber el logo institucional, sellos o firmas que no están publicados en internet.

Esta iniciativa rediseña la experiencia para que crear y mantener plantillas sea intuitivo: variables y campos disponibles se insertan con un click en la posición del cursor, el preview se actualiza en vivo mientras se edita, el admin puede ver el PDF real renderizado bajo demanda, y una biblioteca de imágenes (globales para activos institucionales y por-plantilla para específicas) permite subir y referenciar imágenes propias del servidor sin depender de hosts externos. Es estrictamente una mejora de UX y de capacidades del admin: no cambia el contrato de generación de PDF por solicitud ni la autorización para descargarlos.

## User stories

- Como **admin**, quiero ver las variables, campos del tipo asociado e imágenes disponibles en un panel lateral del editor, para no tener que memorizar nombres ni copiarlos manualmente.
  - **Acceptance:** Al abrir el editor, un panel agrupa los snippets disponibles en pestañas legibles (variables del solicitante/solicitud, campos del tipo si hay tipo asociado, imágenes globales y de la plantilla).
  - **Acceptance:** Cada item del panel muestra el snippet exacto que se insertará y un nombre humano (e.g. "Nombre del solicitante" junto a su forma como variable).

- Como **admin**, quiero que al hacer click en un item del panel el snippet se inserte en la posición exacta del cursor del editor HTML, para no romper mi flujo escribiendo.
  - **Acceptance:** Click con cursor entre dos caracteres inserta el snippet ahí; click sin foco previo inserta al final del HTML.
  - **Acceptance:** Tras insertar, el cursor queda inmediatamente después del snippet insertado.

- Como **admin**, quiero ver un preview que se actualice automáticamente conforme edito el HTML/CSS, para iterar sin tener que guardar.
  - **Acceptance:** Tras una pausa breve de escritura, el preview muestra el render con datos sintéticos sin guardar la plantilla.
  - **Acceptance:** Errores de sintaxis del template no rompen el editor: se muestran inline en el preview con suficiente información para corregir.

- Como **admin**, quiero un botón explícito para ver el PDF real (renderizado por el motor de PDF), para validar que el output final es el esperado antes de publicar.
  - **Acceptance:** Un botón abre el PDF generado por el motor de renderizado real en una pestaña nueva, usando el HTML/CSS actual sin necesidad de guardar primero.

- Como **admin**, quiero subir imágenes al servidor (logo, sellos, firmas) y referenciarlas desde cualquier plantilla, para no depender de hosts externos públicos.
  - **Acceptance:** Existe una biblioteca de imágenes globales gestionable por admin con upload, listado y borrado.
  - **Acceptance:** Las imágenes globales aparecen como items insertables en el panel de cualquier editor de plantilla.

- Como **admin**, quiero también subir imágenes específicas a una plantilla individual, para casos donde una imagen solo aplica a un tipo de documento.
  - **Acceptance:** Desde el editor de una plantilla puedo subir imágenes que solo aparecen en el panel de esa plantilla.

- Como **admin**, quiero subir una imagen sin salir del editor, para no perder el contexto de lo que estoy escribiendo.
  - **Acceptance:** Un modal de upload dentro del editor permite agregar una imagen y refleja el resultado en el panel sin recargar la página.
  - **Acceptance:** Opcionalmente al terminar el upload la imagen se inserta automáticamente en la posición del cursor.

- Como **admin**, quiero que las imágenes embebidas en plantillas no rompan el contrato de PDF estable que ya existe, para que la determinística del documento se mantenga.
  - **Acceptance:** Generar el mismo PDF dos veces bajo reloj congelado produce bytes idénticos aunque la plantilla contenga imágenes propias.

- Como **admin**, quiero que borrar una imagen no rompa el sistema aunque alguna plantilla la siga referenciando, para poder limpiar la biblioteca sin auditar manualmente cada plantilla.
  - **Acceptance:** Borrar una imagen referenciada en una plantilla resulta en un PDF donde la imagen no aparece, pero la generación no falla con error.
  - **Acceptance:** El modal de confirmación de borrado advierte que la imagen podría estar en uso.

## Constraints

- **Autorización**: toda la superficie nueva (editor rediseñado, biblioteca de imágenes, endpoints de preview, modal de upload) es exclusiva de admin. Cualquier otro rol recibe 403. La autorización para descargar PDFs por solicitud no cambia (RF-PDF-07 se preserva).
- **Determinismo del PDF**: el output binario del PDF por solicitud debe seguir siendo byte-idéntico bajo reloj congelado y misma data fuente, aunque la plantilla referencie imágenes propias. Esto implica que la representación de la imagen en el PDF no puede depender de URLs ni de archivos servidos por la app en tiempo de render.
- **Validación de imágenes**: solo formatos bitmap o vectoriales que el motor de PDF pueda embeber. Tamaño máximo por imagen acotado (no inflar PDFs ni saturar storage). El contenido se valida más allá de la extensión (no basta `.png` en el nombre).
- **Seguridad del preview**: el preview se renderiza en un iframe aislado sin permitir ejecución de scripts del HTML escrito por el admin. Los errores de sintaxis del template no derivan en 500 ni filtran stack traces al usuario.
- **Spanish UI** end-to-end (labels, errores, modales, tooltips). Identificadores y código en inglés.
- **Accesibilidad**: el panel y los chips clickeables son navegables por teclado. Tabs siguen el patrón ARIA estándar. Errores de preview se anuncian a tecnologías asistivas.
- **No rompe plantillas existentes**: una plantilla que hoy renderiza correctamente debe seguir renderizando idéntico tras esta iniciativa, sin ninguna migración de contenido. Las nuevas capacidades (referencia a imágenes propias) solo aplican donde el admin las agregue.
- **Sin dependencias JS pesadas**: el editor sigue el stack actual (Alpine.js + Tailwind v4 + Lucide). No se introducen editores de código tipo CodeMirror/Monaco ni bundlers.
- **Almacenamiento local**: las imágenes residen en el filesystem montado del servicio, bajo el patrón existente de media, sin CDN ni servicios externos.

## Non-goals

- Editor WYSIWYG / drag-and-drop visual del HTML. La edición sigue siendo de código.
- Versionado o historial de plantillas. Las plantillas se editan in-place; no se almacenan revisiones.
- Caching o almacenamiento de PDFs renderizados. El contrato existente de render-on-demand se mantiene.
- Compartir/exportar/importar bibliotecas de imágenes entre instancias o entornos.
- Redimensionado, compresión automática o thumbnails generados de imágenes subidas. El admin sube imágenes con el tamaño que ya quiere usar.
- Detección automática del conjunto de plantillas que referencian una imagen (buscar el slug en cada `html`). Borrar una imagen advierte que podría estar en uso pero no enumera dónde.
- Búsqueda full-text sobre el catálogo de imágenes. Si el catálogo crece a tamaños que la justifiquen, será iniciativa futura.
- Sanitización avanzada o restricciones especiales para SVG. Decisión específica (aceptar SVG con sanitización o rechazar SVG) queda como open question para `/plan`.
- Detección de tipo asociado más allá del query param explícito al abrir el editor. Persistir un "tipo por defecto" en la plantilla queda como open question.
- Cambios en el contrato de variables existente (`solicitante.*`, `solicitud.*`, `valores.*`, `now`, `firma_lugar_fecha`). Esta iniciativa solo agrega `assets.*`; no renombra ni quita keys existentes.
- Compartir un upload entre múltiples plantillas más allá del scope global. La separación es solo "global" vs "de una plantilla".

## Related modules

- → `apps/solicitudes/pdf` — extiende el editor admin, agrega endpoints de preview en borrador (HTML y PDF), y agrega resolver de imágenes al contexto de render.
- → `apps/solicitudes/tipos` — el tab "Campos" del panel se alimenta de los `FieldDefinition` del tipo cuando el editor se abre con un tipo asociado.
- → `apps/solicitudes/lifecycle` — sin cambios funcionales; el render por solicitud sigue invocándose igual.
- → `apps/_shared` — el resolver de imágenes a `data:` URI puede vivir en `_shared/pdf` si se considera infraestructura, o en el nuevo feature; `/plan` decide.
- → `specs/flows/pdf-generation.md` — sin cambios en el flujo end-to-end por solicitud; documentar como nota que el contexto ahora incluye `assets.*`.

## Open questions

- **OQ-1**: ¿Cómo identificar el "draft session" para abrir el PDF real (botón "Ver PDF") cuando el admin tiene múltiples pestañas del editor abiertas simultáneamente? Posible solución: una key de sesión por `plantilla_id` con last-write-wins. `/plan` decide.
- **OQ-2**: ¿Aceptar SVG (con sanitización para que el preview HTML no ejecute scripts inline) o restringir uploads a formatos bitmap solamente? `/plan` decide con base en el costo de la sanitización.
- **OQ-3**: ¿Cómo se pobla el tab "Campos" del panel: solo cuando el editor se abre con `?tipo_id=N` en el querystring, o también persistiendo un "tipo asociado por defecto" en la plantilla para futuras visitas sin querystring? `/plan` decide.
- **OQ-4**: ¿Mostrar metadatos de auditoría (quién subió, cuándo) en la galería de imágenes globales? Útil para limpieza pero agrega ruido visual.
- **OQ-5**: ¿Imponer un límite máximo de imágenes globales (e.g. 50) o dejarlo abierto con UI scrollable? Depende del volumen esperado en producción.
