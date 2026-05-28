"""Pasos específicos de la característica REVISIÓN (cola del personal).

Frases propias de la cola de revisión para no colisionar con los pasos comunes
(`_comunes.py`) ni con los del intake. El login por rol y las aserciones
genéricas de texto/URL se reutilizan de los pasos comunes; aquí vive lo
exclusivo: sembrar (vía la UI del alumno) una solicitud cuyo rol responsable es
Control Escolar, entrar a la cola como personal, leer columnas/encabezado, abrir
el detalle, pulsar "Atender" y verificar la negación de acceso para un alumno.
"""
from __future__ import annotations

import re
import time

from behave import given, then, when  # type: ignore[import]
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from _comunes import _login_as  # type: ignore[import]

# La cola de revisión se monta bajo la app de solicitudes.
_QUEUE_PATH = "/solicitudes/revision/"
_FOLIO_RE = re.compile(r"SOL-\d{4}-\d+")


def _crear_solicitud_alumno(context, slug: str) -> str:
    """Crea, como ALUMNO, una solicitud del tipo indicado vía la UI y
    devuelve su folio. El tipo ``constancia-de-estudios`` tiene
    ``responsible_role = CONTROL_ESCOLAR`` (ver app/solicitudes/seeders.py),
    de modo que la solicitud aterriza en la cola de Control Escolar.
    """
    _login_as(context, "ALUMNO")
    context.browser.get(f"{context.base_url}/solicitudes/crear/{slug}/")
    formulario = context.wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "form[method='post']"))
    )

    # Marca única por corrida para los campos de texto.
    marca = f"Rev {int(time.time() * 1000)}"
    context.revision_marca = marca

    for campo in formulario.find_elements(
        By.CSS_SELECTOR,
        "input[name^='field_'][type='text'], textarea[name^='field_']",
    ):
        campo.clear()
        campo.send_keys(marca)

    for campo in formulario.find_elements(
        By.CSS_SELECTOR, "input[name^='field_'][type='number']"
    ):
        campo.clear()
        campo.send_keys("1")

    for campo in formulario.find_elements(
        By.CSS_SELECTOR, "input[name^='field_'][type='date']"
    ):
        context.browser.execute_script(
            "arguments[0].value = arguments[1];", campo, "2026-06-01"
        )

    for elemento in formulario.find_elements(
        By.CSS_SELECTOR, "select[name^='field_']"
    ):
        select = Select(elemento)
        for opcion in select.options:
            if opcion.get_attribute("value"):
                select.select_by_value(opcion.get_attribute("value"))
                break

    boton = context.wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "form[method='post'] button[type='submit']")
        )
    )
    boton.click()
    context.wait.until(EC.url_contains("/solicitudes/SOL-"))
    coincidencia = _FOLIO_RE.search(context.browser.current_url)
    assert coincidencia, (
        "No se encontró un folio en la URL tras crear la solicitud: "
        f"{context.browser.current_url}"
    )
    return coincidencia.group(0)


@given('que un alumno registró una solicitud de "{slug}" para revisión')
def step_alumno_registra_para_revision(context, slug: str) -> None:
    context.revision_folio = _crear_solicitud_alumno(context, slug)


@when("ingresa Control Escolar a la cola de revisión")
def step_ce_entra_cola(context) -> None:
    _login_as(context, "CONTROL_ESCOLAR")
    context.browser.get(f"{context.base_url}{_QUEUE_PATH}")
    context.wait.until(EC.url_contains("/solicitudes/revision"))


@when("ingreso a la cola de revisión sin permisos")
def step_entra_cola_sin_permisos(context) -> None:
    context.browser.get(f"{context.base_url}{_QUEUE_PATH}")


@then("se muestra el encabezado de la cola de revisión")
def step_ve_encabezado_cola(context) -> None:
    encabezado = context.wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//h1[contains(., 'Cola de revisión')]")
        )
    )
    assert "Cola de revisión" in encabezado.text


@then(
    "la cola de revisión muestra las columnas de folio, solicitante y estado"
)
def step_ve_columnas(context) -> None:
    encabezados = context.wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table thead th"))
    )
    textos = {th.text.strip().lower() for th in encabezados}
    for esperado in ("folio", "solicitante", "estado"):
        assert any(esperado in t for t in textos), (
            f"No encontré la columna «{esperado}» en la cola. "
            f"Columnas presentes: {sorted(textos)}"
        )


@then("la cola de revisión incluye la solicitud recién registrada")
def step_cola_incluye_solicitud(context) -> None:
    folio = context.revision_folio
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), folio)
    )


@when("Control Escolar abre el detalle de la solicitud registrada")
def step_ce_abre_detalle(context) -> None:
    _login_as(context, "CONTROL_ESCOLAR")
    folio = context.revision_folio
    context.browser.get(f"{context.base_url}{_QUEUE_PATH}{folio}/")
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), folio)
    )


@when("Control Escolar pulsa el botón de atender la solicitud")
def step_ce_atiende(context) -> None:
    boton = context.wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//form[contains(@action, '/atender/')]//button[@type='submit']",
            )
        )
    )
    boton.click()
    context.wait.until(EC.url_contains("/solicitudes/revision"))


@then('el detalle de revisión muestra el estado "{etiqueta}"')
def step_detalle_muestra_estado(context, etiqueta: str) -> None:
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), etiqueta)
    )


@then("se muestra la negación de acceso a la revisión")
def step_negacion_acceso(context) -> None:
    # `Unauthorized` se renderiza en _shared/error.html con "Error 403"
    # y el mensaje del rol. Aseguramos por el código de estado visible.
    cuerpo = context.wait.until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    texto = cuerpo.text
    assert "403" in texto or "no tiene acceso" in texto.lower(), (
        "Esperaba una negación de acceso (403) para el alumno, pero la "
        f"página mostró:\n{texto[:500]}"
    )
    # La cola NO debe haberse renderizado para el alumno.
    assert "Cola de revisión" not in texto, (
        "El alumno no debería ver la cola de revisión."
    )
