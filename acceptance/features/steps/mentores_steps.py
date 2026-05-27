"""Pasos específicos de la característica MENTORES (importación CSV).

Pruebas de navegador (Selenium): el administrador entra a la pantalla de
importar mentores, sube un archivo CSV escrito en disco y observa el resumen o
el error en pantalla. Reutiliza ``context.browser``, ``context.wait`` y
``context.base_url`` provistos por ``environment.py``.
"""
from __future__ import annotations

import os
import random
import tempfile

from behave import then, when  # type: ignore[import]
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

IMPORT_PATH = "/mentores/importar/"


def _escribir_csv(contenido: str) -> str:
    """Escribe ``contenido`` en un .csv temporal y devuelve su ruta absoluta."""
    fd, ruta = tempfile.mkstemp(suffix=".csv", prefix="mentores_acc_")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
        fh.write(contenido)
    return os.path.abspath(ruta)


def _subir_csv(context, contenido: str) -> None:
    """Localiza el <input type=file>, adjunta el CSV y envía el formulario."""
    ruta = _escribir_csv(contenido)
    file_input = context.wait.until(
        EC.presence_of_element_located((By.NAME, "archivo"))
    )
    file_input.send_keys(ruta)
    boton = context.browser.find_element(
        By.XPATH, "//form//button[@type='submit']"
    )
    boton.click()


@when("el administrador abre la pantalla de importar mentores")
def step_abre_import(context) -> None:
    context.browser.get(f"{context.base_url}{IMPORT_PATH}")


@when("el administrador sube un CSV de mentores con filas válidas y una inválida")
def step_sube_csv_mixto(context) -> None:
    # Sufijo aleatorio de 4 dígitos para que las matrículas (8 dígitos) sean
    # únicas entre corridas y no choquen con sembrados u otras ejecuciones.
    sufijo = f"{random.randint(0, 9999):04d}"
    contenido = (
        "matricula\n"
        f"3210{sufijo}\n"   # válida (8 dígitos)
        f"3211{sufijo}\n"   # válida (8 dígitos)
        "abc\n"             # inválida (no son 8 dígitos)
        f"3212{sufijo}\n"   # válida (8 dígitos)
    )
    _subir_csv(context, contenido)


@when("el administrador sube un CSV de mentores con encabezado incorrecto")
def step_sube_csv_encabezado_malo(context) -> None:
    contenido = "alumno\n32100001\n32100002\n"
    _subir_csv(context, contenido)


@then("el administrador ve el resumen de la importación de mentores")
def step_ve_resumen(context) -> None:
    context.wait.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"), "Resultado de la importación"
        )
    )


@then("el administrador ve el error de encabezado de mentores")
def step_ve_error_encabezado(context) -> None:
    context.wait.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            "El archivo CSV tiene un formato inválido.",
        )
    )


@then("el alumno recibe negación de acceso a la importación de mentores")
def step_alumno_negado(context) -> None:
    # ``Unauthorized`` (403) → se renderiza la página de error compartida con el
    # mensaje del rol sin permiso y el código "unauthorized". El encabezado
    # "Error 403" se muestra en mayúsculas por CSS, así que afirmamos sobre el
    # mensaje (en mayúsculas/minúsculas mixtas) que sí coincide tal cual.
    context.wait.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            "No tienes permiso para realizar esta acción.",
        )
    )
    cuerpo = context.browser.find_element(By.TAG_NAME, "body").text
    assert "unauthorized" in cuerpo, (
        "Se esperaba el código de error 'unauthorized' para el alumno; "
        f"cuerpo:\n{cuerpo}"
    )
