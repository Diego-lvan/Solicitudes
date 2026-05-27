"""Behave + Selenium environment hooks.

Las pruebas de aceptación corren contra el stack de desarrollo en ejecución
(``make up`` + ``make seed``), accediendo por nginx en ``https://localhost`` con
certificado autofirmado. Cada escenario arranca con una sesión limpia (se
borran las cookies) y se autentica vía el picker de ``/auth/dev-login``.
"""
from __future__ import annotations

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


def _str2bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "si", "sí"}


def before_all(context) -> None:
    userdata = context.config.userdata
    context.base_url = userdata.get("base_url", "https://localhost").rstrip("/")
    headless = _str2bool(userdata.get("headless", "true"))

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    # El stack dev usa un certificado autofirmado para localhost.
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.set_capability("acceptInsecureCerts", True)

    context.browser = webdriver.Chrome(options=options)
    context.browser.implicitly_wait(5)
    context.wait = WebDriverWait(context.browser, 15)


def after_all(context) -> None:
    browser = getattr(context, "browser", None)
    if browser is not None:
        browser.quit()


def before_scenario(context, scenario) -> None:
    # Sesión limpia por escenario: navega al origen y borra cookies.
    context.browser.get(f"{context.base_url}/auth/dev-login")
    context.browser.delete_all_cookies()
