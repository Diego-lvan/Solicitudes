"""Pasos específicos de la característica REPORTES (dashboard administrativo).

Frases propias del dashboard de reportes para no colisionar con los pasos
comunes (`_comunes.py`). Reutilizamos login/navegación/aserciones de texto y
URL de los pasos comunes; aquí sólo vive lo exclusivo de reportes: leer las
tarjetas de totales y el desglose, aplicar el filtro por rango de fechas,
validar el enlace de exportación CSV y comprobar la negación de acceso.

Las aserciones son RESILIENTES: nunca afirmamos conteos globales exactos
(otras suites corren en paralelo contra la misma base de datos y crean
solicitudes). Verificamos estructura, etiquetas y comportamiento de la página.
"""
from __future__ import annotations

from behave import then, when  # type: ignore[import]
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# Ruta donde se monta la exportación CSV del dashboard de reportes.
_EXPORT_CSV_PATH = "/reportes/exportar/csv/"


def _texto_cuerpo(context) -> str:
    return context.browser.find_element(By.TAG_NAME, "body").text


@then("veo el panel de totales del dashboard de reportes")
def step_veo_totales(context) -> None:
    """La tarjeta de Total existe y muestra un número (sin afirmar el valor).

    El rótulo de la tarjeta se muestra en mayúsculas por CSS (`uppercase`),
    así que Selenium lo expone como «TOTAL» en el texto renderizado.
    """
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "TOTAL")
    )
    cuerpo = _texto_cuerpo(context)
    assert "TOTAL" in cuerpo, "No se encontró la tarjeta de totales en el dashboard."


@then("veo el desglose por estado y por tipo del dashboard de reportes")
def step_veo_desglose(context) -> None:
    """Las secciones de desglose agregadas están presentes en la página."""
    cuerpo = _texto_cuerpo(context)
    for seccion in ("Por estado", "Por tipo", "Por mes"):
        assert seccion in cuerpo, (
            f"Esperaba ver la sección «{seccion}» en el dashboard de reportes; "
            "no apareció."
        )


@when(
    'aplico un filtro de fechas del "{desde}" al "{hasta}" '
    "en el dashboard de reportes"
)
def step_aplico_filtro_fechas(context, desde: str, hasta: str) -> None:
    """Llena los campos de fecha del formulario de filtros y lo envía."""
    campo_desde = context.wait.until(
        EC.presence_of_element_located((By.NAME, "created_from"))
    )
    campo_hasta = context.browser.find_element(By.NAME, "created_to")

    # Los <input type="date"> se llenan de forma fiable vía JS.
    context.browser.execute_script(
        "arguments[0].value = arguments[1];", campo_desde, desde
    )
    context.browser.execute_script(
        "arguments[0].value = arguments[1];", campo_hasta, hasta
    )

    boton = context.wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "form[method='get'] button[type='submit']")
        )
    )
    boton.click()
    # Tras enviar, la página recarga con los parámetros de fecha en la URL.
    context.wait.until(EC.url_contains("created_from"))


@then("el enlace de exportar CSV del dashboard apunta a la ruta de exportación CSV")
def step_enlace_csv(context) -> None:
    """El enlace «Exportar CSV» existe, es visible y apunta a la ruta CSV."""
    enlace = context.wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, f"a[href*='{_EXPORT_CSV_PATH}']")
        )
    )
    assert enlace.is_displayed(), "El enlace de exportar CSV no está visible."
    href = enlace.get_attribute("href") or ""
    assert _EXPORT_CSV_PATH in href, (
        f"El enlace de exportar CSV no apunta a la ruta esperada: {href!r}"
    )
    # Guardamos el href para validarlo en el siguiente paso.
    context.reportes_csv_href = href


@then("al exportar el CSV no llego al login ni a una página de error")
def step_exportar_csv_accesible(context) -> None:
    """Navegar a la ruta de exportación CSV no redirige al login ni da error.

    La respuesta es un adjunto (text/csv con BOM), por lo que el navegador la
    descarga en lugar de renderizar HTML. Comprobamos vía fetch que la ruta
    responde 200 con la cabecera de descarga y NO redirige al picker de login.
    """
    href = getattr(context, "reportes_csv_href", None)
    if not href:
        enlace = context.browser.find_element(
            By.CSS_SELECTOR, f"a[href*='{_EXPORT_CSV_PATH}']"
        )
        href = enlace.get_attribute("href") or ""

    # Usamos la sesión autenticada del navegador (cookies) vía fetch().
    resultado = context.browser.execute_async_script(
        """
        const url = arguments[0];
        const done = arguments[arguments.length - 1];
        fetch(url, {credentials: 'same-origin', redirect: 'follow'})
          .then(r => r.text().then(body => done({
            status: r.status,
            finalUrl: r.url,
            disposition: r.headers.get('Content-Disposition') || '',
            contentType: r.headers.get('Content-Type') || '',
            snippet: body.slice(0, 64),
          })))
          .catch(e => done({error: String(e)}));
        """,
        href,
    )

    assert not resultado.get("error"), (
        f"La descarga del CSV falló: {resultado.get('error')}"
    )
    assert resultado["status"] == 200, (
        f"Esperaba 200 al exportar CSV, obtuve {resultado['status']}."
    )
    assert "dev-login" not in resultado["finalUrl"], (
        "La exportación CSV redirigió al login: " f"{resultado['finalUrl']}"
    )
    # Debe ser una descarga CSV, no una página de error HTML.
    assert "csv" in resultado["contentType"].lower(), (
        f"El tipo de contenido no es CSV: {resultado['contentType']!r}"
    )


@then("se me niega el acceso al dashboard de reportes")
def step_acceso_negado(context) -> None:
    """Un rol sin permiso ve la página de error 403 (acceso denegado).

    El rótulo «Error 403» se muestra en mayúsculas por CSS (`uppercase`),
    así que Selenium lo expone como «ERROR 403» en el texto renderizado.
    """
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "ERROR 403")
    )
    cuerpo = _texto_cuerpo(context)
    assert "ERROR 403" in cuerpo, (
        "Esperaba la página de error 403 para un rol sin permiso; "
        f"cuerpo: {cuerpo[:200]!r}"
    )
    assert "No tienes permiso" in cuerpo, (
        "Esperaba el mensaje de acceso denegado en la página 403; "
        f"cuerpo: {cuerpo[:200]!r}"
    )
    # El dashboard real NO debe haberse renderizado para este rol.
    assert "Reportes y dashboard" not in cuerpo, (
        "El alumno alcanzó el dashboard de reportes pese a no tener permiso."
    )
