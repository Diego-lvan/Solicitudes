"""Pasos específicos de la característica INTAKE (alta de solicitudes).

Frases propias del flujo de alta para no colisionar con los pasos comunes
(`_comunes.py`). La navegación de login/aserciones de texto/URL se reutiliza
de los pasos comunes; aquí sólo vive lo que es exclusivo del intake: abrir el
catálogo, abrir el formulario de un tipo, llenar el formulario dinámico,
enviarlo y verificar el folio recién creado.
"""
from __future__ import annotations

import re
import time

from behave import then, when  # type: ignore[import]
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# El catálogo de intake se monta en la raíz de la app de solicitudes.
_CATALOGO_PATH = "/solicitudes/"
_FOLIO_RE = re.compile(r"SOL-\d{4}-\d+")


@when("el alumno abre el catálogo de solicitudes")
def step_abre_catalogo(context) -> None:
    context.browser.get(f"{context.base_url}{_CATALOGO_PATH}")


@when('el alumno abre el formulario del tipo "{slug}"')
def step_abre_formulario(context, slug: str) -> None:
    context.browser.get(f"{context.base_url}/solicitudes/crear/{slug}/")
    # Esperamos a que el formulario dinámico esté presente.
    context.wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "form button[type='submit']"))
    )


@when("el alumno llena los campos del formulario dinámico")
def step_llena_formulario(context) -> None:
    """Llena cada campo de entrada del formulario dinámico.

    Los inputs se nombran ``field_<uuid>``; no dependemos de UUIDs concretos:
    recorremos los campos visibles y los llenamos según su tipo. Para datos
    únicos por corrida, el campo de texto recibe una marca con timestamp que
    luego usamos para localizar la solicitud (el folio real se captura de la
    URL tras enviar).
    """
    formulario = context.wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "form[method='post']"))
    )

    # Marca única por corrida para los campos de texto/área.
    marca = f"Acc {int(time.time() * 1000)}"
    context.intake_marca = marca

    # Campos de texto y área de texto que pertenecen al formulario dinámico.
    text_inputs = formulario.find_elements(
        By.CSS_SELECTOR,
        "input[name^='field_'][type='text'], textarea[name^='field_']",
    )
    for campo in text_inputs:
        campo.clear()
        campo.send_keys(marca)

    # Campos numéricos.
    for campo in formulario.find_elements(
        By.CSS_SELECTOR, "input[name^='field_'][type='number']"
    ):
        campo.clear()
        campo.send_keys("1")

    # Campos de fecha.
    for campo in formulario.find_elements(
        By.CSS_SELECTOR, "input[name^='field_'][type='date']"
    ):
        context.browser.execute_script(
            "arguments[0].value = arguments[1];", campo, "2026-06-01"
        )

    # Selects (choices): elegimos la primera opción no vacía.
    for elemento in formulario.find_elements(
        By.CSS_SELECTOR, "select[name^='field_']"
    ):
        select = Select(elemento)
        for opcion in select.options:
            if opcion.get_attribute("value"):
                select.select_by_value(opcion.get_attribute("value"))
                break


@when("el alumno envía el formulario de la solicitud")
def step_envia_formulario(context) -> None:
    boton = context.wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "form[method='post'] button[type='submit']")
        )
    )
    boton.click()
    # Tras enviar, el sistema redirige al detalle con folio en la URL.
    context.wait.until(EC.url_contains("/solicitudes/SOL-"))
    coincidencia = _FOLIO_RE.search(context.browser.current_url)
    assert coincidencia, (
        "No se encontró un folio en la URL tras enviar: "
        f"{context.browser.current_url}"
    )
    context.intake_folio = coincidencia.group(0)


@then("el alumno ve el folio de su nueva solicitud")
def step_ve_folio(context) -> None:
    folio = context.intake_folio
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), folio)
    )


@when("el alumno abre la lista de mis solicitudes")
def step_abre_mis_solicitudes(context) -> None:
    context.browser.get(f"{context.base_url}/solicitudes/mis/")


@then("el alumno ve el folio de su nueva solicitud en la lista")
def step_ve_folio_en_lista(context) -> None:
    folio = context.intake_folio
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), folio)
    )
