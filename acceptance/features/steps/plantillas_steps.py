"""Pasos específicos de la característica PLANTILLAS (catálogo admin de PDF).

Frases propias del catálogo administrativo de plantillas PDF para no colisionar
con los pasos comunes (`_comunes.py`). Login/aserciones de texto/URL se
reutilizan de los pasos comunes; aquí sólo vive lo exclusivo: abrir el catálogo,
abrir el editor de una plantilla concreta, validar el editor con preview en vivo
y verificar la negación de acceso para un rol sin permisos.

Referencias de capturas: ``docs/screenshots/11-admin-plantillas-list.png`` y
``docs/screenshots/12-admin-plantilla-editor.png``.
"""
from __future__ import annotations

from behave import then, when  # type: ignore[import]
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# El catálogo administrativo de plantillas se monta bajo la app de solicitudes.
_CATALOGO_PLANTILLAS_PATH = "/solicitudes/admin/plantillas/"


@when("el administrador abre el catálogo de plantillas")
def step_abre_catalogo_plantillas(context) -> None:
    context.browser.get(f"{context.base_url}{_CATALOGO_PLANTILLAS_PATH}")


@when('el administrador edita la plantilla "{nombre}"')
def step_edita_plantilla(context, nombre: str) -> None:
    """Abre el editor de la plantilla cuyo nombre aparece en el listado.

    Descubrimos el enlace «Editar» del renglón cuyo nombre coincide, sin
    depender de UUIDs concretos: localizamos el enlace de detalle por su texto
    y, desde su renglón, hacemos clic en «Editar».
    """
    # Esperamos a que el listado esté presente con la plantilla buscada.
    enlace_nombre = context.wait.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//table//a[normalize-space(text())='{nombre}']")
        )
    )
    fila = enlace_nombre.find_element(By.XPATH, "./ancestor::tr")
    boton_editar = fila.find_element(
        By.XPATH, ".//a[normalize-space(text())='Editar']"
    )
    boton_editar.click()
    # El editor es la vista de formulario; esperamos su URL de edición.
    context.wait.until(EC.url_contains("/editar/"))


@then('el administrador ve el editor de la plantilla "{nombre}"')
def step_ve_editor(context, nombre: str) -> None:
    # El encabezado del editor es «Editar «<nombre>»» y existe un botón
    # de guardado; ambos confirman que el editor cargó para esa plantilla.
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), f"Editar «{nombre}»")
    )
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Guardar cambios")
    )


@then("el alumno recibe negación de acceso al catálogo de plantillas")
def step_negacion_acceso(context) -> None:
    """Un rol sin permisos recibe la página de error 403 del sistema.

    El mixin de administrador lanza ``Unauthorized``, que el middleware
    traduce a la página de error genérica (HTTP 403) con el código
    ``unauthorized``. El encabezado «Error 403» se muestra en mayúsculas por
    CSS, por lo que Selenium lo reporta como «ERROR 403».
    """
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "ERROR 403")
    )
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "unauthorized")
    )
