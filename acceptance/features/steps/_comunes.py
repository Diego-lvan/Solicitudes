"""Pasos comunes reutilizables por todas las características.

Login vía el picker de desarrollo (``/auth/dev-login``), navegación y
aserciones de contenido/URL. Los pasos específicos de cada feature viven en su
propio archivo de steps.
"""
from __future__ import annotations

from behave import given, then, when  # type: ignore[import]
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def _login_as(context, role: str) -> None:
    """Inicia sesión por rol usando el ingreso rápido de /auth/dev-login."""
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
    # Tras el POST el sistema redirige al destino del rol.
    context.wait.until(lambda d: "/auth/dev-login" not in d.current_url)


@given('que inicié sesión como "{role}"')
def step_login(context, role: str) -> None:
    _login_as(context, role)


@given("que no he iniciado sesión")
def step_anonimo(context) -> None:
    context.browser.get(f"{context.base_url}/auth/dev-login")
    context.browser.delete_all_cookies()


@when('navego a "{path}"')
def step_navego(context, path: str) -> None:
    context.browser.get(f"{context.base_url}{path}")


@then('veo el texto "{texto}"')
def step_veo_texto(context, texto: str) -> None:
    context.wait.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), texto)
    )


@then('no veo el texto "{texto}"')
def step_no_veo_texto(context, texto: str) -> None:
    cuerpo = context.browser.find_element(By.TAG_NAME, "body").text
    assert texto not in cuerpo, f"No esperaba encontrar «{texto}» en la página."


@then('la URL contiene "{fragmento}"')
def step_url_contiene(context, fragmento: str) -> None:
    context.wait.until(EC.url_contains(fragmento))
