"""Pasos específicos de la característica de archivos adjuntos.

Cubren el flujo real de navegador: un alumno crea una solicitud de constancia
adjuntando un archivo PDF, lo ve y lo descarga en el detalle; y un usuario sin
relación recibe acceso denegado al intentar abrir la URL de descarga.

Reutiliza los pasos comunes de ``_comunes.py`` (login por rol, etc.). Las frases
aquí son específicas de archivos para evitar colisiones con otras features.
"""
from __future__ import annotations

import os
import tempfile
import time

from behave import given, then, when  # type: ignore[import]
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# PDF mínimo y válido (cabecera %PDF-…). El campo "Comprobante" de la constancia
# acepta solo ``.pdf``; usamos esa extensión.
_MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n"
    b"%%EOF\n"
)


def _make_temp_pdf() -> tuple[str, str]:
    """Crea un PDF temporal único en disco y devuelve (ruta_absoluta, nombre)."""
    unique = f"comprobante_{int(time.time() * 1000)}.pdf"
    path = os.path.join(tempfile.gettempdir(), unique)
    with open(path, "wb") as fh:
        fh.write(_MINIMAL_PDF)
    return os.path.abspath(path), unique


def _crear_constancia_con_archivo(context) -> tuple[str, str]:
    """Crea una constancia adjuntando un PDF. Deja al navegador en el detalle.

    Devuelve (folio_url_fragmento, nombre_archivo). Asume sesión de ALUMNO ya
    iniciada.
    """
    pdf_path, pdf_name = _make_temp_pdf()
    context.browser.get(
        f"{context.base_url}/solicitudes/crear/constancia-de-estudios/"
    )

    # Campos de texto requeridos: rellenar todos los <input type=text>.
    for inp in context.browser.find_elements(
        By.CSS_SELECTOR, "form input[type='text']"
    ):
        inp.clear()
        inp.send_keys("Alumno de Prueba Aceptacion")

    # Selects requeridos: elegir la primera opción no vacía.
    from selenium.webdriver.support.ui import Select

    for sel_el in context.browser.find_elements(By.CSS_SELECTOR, "form select"):
        select = Select(sel_el)
        for option in select.options:
            if option.get_attribute("value"):
                select.select_by_visible_text(option.text)
                break

    # Adjuntar el PDF en el (único) input de archivo del formulario.
    file_input = context.wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "form input[type='file']")
        )
    )
    file_input.send_keys(pdf_path)

    # Enviar.
    submit = context.browser.find_element(
        By.CSS_SELECTOR, "form button[type='submit']"
    )
    submit.click()

    # Éxito => redirección al detalle /solicitudes/<FOLIO>/ (no a /crear/).
    context.wait.until(
        lambda d: "/crear/" not in d.current_url
        and "/solicitudes/" in d.current_url
    )
    detalle_url = context.browser.current_url
    context.archivo_nombre = pdf_name
    context.detalle_url = detalle_url
    return detalle_url, pdf_name


@when("creo una solicitud de constancia con un archivo adjunto")
def step_crear_constancia(context) -> None:
    _crear_constancia_con_archivo(context)


@then("veo el archivo adjunto en el detalle de mi solicitud")
def step_veo_archivo(context) -> None:
    # El detalle lista los adjuntos bajo "Tus archivos adjuntos".
    context.wait.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"), "Tus archivos adjuntos"
        )
    )
    cuerpo = context.browser.find_element(By.TAG_NAME, "body").text
    assert context.archivo_nombre in cuerpo, (
        f"Esperaba ver el archivo «{context.archivo_nombre}» en el detalle; "
        f"cuerpo: {cuerpo[:400]}"
    )


def _enlace_descarga(context):
    """Devuelve el primer <a> que apunta a la URL de descarga de archivos."""
    enlaces = context.browser.find_elements(
        By.CSS_SELECTOR, "a[href*='/solicitudes/archivos/']"
    )
    assert enlaces, "No se encontró ningún enlace de descarga en el detalle."
    return enlaces[0]


@then("veo el enlace de descarga del archivo adjunto")
def step_veo_enlace_descarga(context) -> None:
    enlace = _enlace_descarga(context)
    assert enlace.is_displayed(), "El enlace de descarga no está visible."
    href = enlace.get_attribute("href")
    assert href and "/solicitudes/archivos/" in href, (
        f"Href de descarga inesperado: {href!r}"
    )
    context.download_url = href


@then(
    "al abrir el enlace de descarga no soy enviado al login ni a una página de error"
)
def step_abrir_descarga(context) -> None:
    download_url = getattr(context, "download_url", None) or _enlace_descarga(
        context
    ).get_attribute("href")
    # La respuesta de descarga es ``Content-Disposition: attachment``, por lo que
    # navegar con el navegador dispararía una descarga (no una página). En su
    # lugar usamos la sesión autenticada del navegador para hacer un ``fetch``
    # y comprobar el código HTTP: el dueño debe obtener 200 (no 302 al login
    # ni 403). ``fetch`` sigue redirecciones, así que una redirección al login
    # acabaría en la página de login (otra URL); lo detectamos por la URL final.
    script = """
        const cb = arguments[arguments.length - 1];
        fetch(arguments[0], {credentials: 'same-origin'})
          .then(r => cb({status: r.status, url: r.url}))
          .catch(e => cb({status: -1, url: String(e)}));
    """
    context.browser.set_script_timeout(20)
    result = context.browser.execute_async_script(script, download_url)
    assert result["status"] == 200, (
        f"El dueño debía poder descargar (200); obtuvo {result}."
    )
    assert "/auth/dev-login" not in result["url"], (
        f"La descarga del dueño terminó en el login: {result}"
    )


# --- Escenario alterno: acceso denegado ------------------------------------


@given("que un alumno tiene una solicitud de constancia con un archivo adjunto")
def step_alumno_con_archivo(context) -> None:
    # Iniciar sesión como ALUMNO usando el flujo común de login.
    context.browser.get(f"{context.base_url}/auth/dev-login")
    boton = context.wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//form[.//input[@name='role' and @value='ALUMNO']]"
                "//button[@type='submit']",
            )
        )
    )
    boton.click()
    context.wait.until(lambda d: "/auth/dev-login" not in d.current_url)

    _crear_constancia_con_archivo(context)
    enlace = _enlace_descarga(context)
    context.download_url = enlace.get_attribute("href")
    assert context.download_url, "No se capturó la URL de descarga del alumno."


@when('inicio sesión como "{role}" e intento abrir la descarga de ese archivo')
def step_otro_usuario_descarga(context, role: str) -> None:
    # Cerrar la sesión del alumno y entrar con el otro rol.
    context.browser.delete_all_cookies()
    context.browser.get(f"{context.base_url}/auth/dev-login")
    boton = context.wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                f"//form[.//input[@name='role' and @value='{role}']]"
                "//button[@type='submit']",
            )
        )
    )
    boton.click()
    context.wait.until(lambda d: "/auth/dev-login" not in d.current_url)

    # Intentar abrir la URL de descarga capturada del alumno.
    context.browser.get(context.download_url)


@then("se me niega el acceso al archivo")
def step_acceso_denegado(context) -> None:
    url_actual = context.browser.current_url
    cuerpo = context.browser.find_element(By.TAG_NAME, "body").text
    # No debe haberse descargado el archivo: la app muestra su página de error
    # de acceso denegado (Unauthorized -> 403, "No tienes permiso...").
    assert "/auth/dev-login" not in url_actual, (
        "Se redirigió al login en vez de denegar el acceso a un usuario autenticado."
    )
    assert (
        "No tienes permiso" in cuerpo
        or "Error 403" in cuerpo
        or "unauthorized" in cuerpo
    ), (
        "Esperaba una página de acceso denegado (403) para el usuario sin "
        f"relación; cuerpo: {cuerpo[:400]}"
    )
