# Pruebas de aceptación — behave + Selenium

Pruebas de aceptación de extremo a extremo (navegador real) para el Sistema de
Solicitudes UAZ, escritas en **Gherkin (español)** con **behave** y ejecutadas
con **Selenium** sobre Google Chrome.

Cubren las historias de usuario de cada módulo del equipo:

| Feature | Módulo | Historia |
|---|---|---|
| `acceso.feature` | usuarios | Inicio de sesión por rol / bloqueo de anónimos |
| `intake.feature` | solicitudes/intake | Alta de solicitudes desde el alumno |
| `archivos.feature` | solicitudes/archivos | Adjuntar y descargar archivos (con autorización) |
| `revision.feature` | solicitudes/revision | Cola de revisión y atención del personal |
| `plantillas.feature` | solicitudes/pdf | Catálogo y editor de plantillas PDF |
| `mentores.feature` | mentores | Importación CSV de mentores |
| `reportes.feature` | reportes | Dashboard administrativo y export CSV |

## Requisitos

1. El stack de desarrollo en ejecución y con datos sembrados:
   ```sh
   make up && make seed     # o el equivalente docker compose
   ```
   La suite ataca `https://localhost` (nginx con certificado autofirmado; el
   driver lo ignora con `acceptInsecureCerts`).
2. Google Chrome instalado en la máquina (Selenium Manager descarga el driver).
3. Un entorno virtual con las dependencias:
   ```sh
   cd acceptance
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

## Ejecución

```sh
cd acceptance
.venv/bin/behave                       # toda la suite
.venv/bin/behave features/intake.feature   # una sola feature
.venv/bin/behave -D headless=false         # ver el navegador
.venv/bin/behave -D base_url=https://localhost   # apuntar a otro entorno
```

## Estructura

```
acceptance/
├── behave.ini                 # configuración (paths, idioma, userdata)
├── requirements.txt
└── features/
    ├── environment.py         # ciclo de vida del WebDriver + hooks
    ├── *.feature              # escenarios Gherkin (es)
    └── steps/
        ├── _comunes.py        # pasos reutilizables (login, navegación, aserciones)
        └── *_steps.py         # pasos por feature
```

Las aserciones se hacen siempre sobre lo que **ve el usuario** en el navegador
(textos, URLs, páginas de error), nunca sobre códigos HTTP crudos.
