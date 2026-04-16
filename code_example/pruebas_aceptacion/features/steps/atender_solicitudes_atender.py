from behave import when, then, step
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import time

ESTADO_A_ESTATUS = {
    'Creada': '1',
    'En proceso': '2',
    'Terminada': '3',
    'Cancelada': '4',
}

ESTATUS_A_ESTADO = {
    '1': 'Creada',
    '2': 'En proceso',
    '3': 'Terminada',
    '4': 'Cancelada',
}


@when('empiezo a revisar la solicitud')
def step_empezar_revisar_solicitud(context):
    boton_revisar = context.driver.find_element(By.ID, "btn-revisar-solicitud")
    boton_revisar.click()
    time.sleep(2)


@then('selecciona el estado "{estado}"')
def step_seleccionar_estado(context, estado):
    select_element = context.driver.find_element(By.ID, "estatus")
    select = Select(select_element)
    estado_id = ESTADO_A_ESTATUS.get(estado, '1')
    select.select_by_value(estado_id)
    time.sleep(1)


@then('escribe "{texto}" en el campo de observaciones')
def step_escribir_observaciones(context, texto):
    textarea = context.driver.find_element(By.ID, "observaciones")
    textarea.clear()
    textarea.send_keys(texto)
    time.sleep(1)


@step('hace clic en el botón "Guardar"')
def step_clic_guardar(context):
    boton = context.driver.find_element(By.ID, "btn-guardar-solicitud")
    boton.click()
    time.sleep(2)


@then('hace clic en el botón "Cancelar"')
def step_clic_cancelar(context):
    boton = context.driver.find_element(By.ID, "btn-cancelar-solicitud")
    context.driver.execute_script("arguments[0].scrollIntoView(true);", boton)
    time.sleep(2)
    boton.click()
    time.sleep(2)


@then('debe ver un mensaje "{mensaje}"')
def step_verificar_mensaje_confirmacion(context, mensaje):
    messages_cont = context.driver.find_element(By.ID, "mensajes-solicitud")
    messages_divs = messages_cont.find_elements(By.CLASS_NAME, "alert")
    messages = []
    for div in messages_divs:
        messages.append(div.text.lower())

    encontrado = mensaje.lower() in messages
    assert encontrado, f"No se encontró mensaje {mensaje}. Contenido: {messages}"
    time.sleep(1)


@step('la solicitud "{folio}" debe tener el estado "{estado}"')
def step_verificar_estado_solicitud(context, folio, estado):
    status = context.driver.find_element(
        By.ID, "estatus-solicitud").text.strip()

    assert status == estado, (
        f"Se esperaba estado '{estado}' pero la solicitud tiene estado '{status}'"
    )


@then('debe regresar a la página de "{pagina}"')
def step_verificar_regreso_pagina(context, pagina):
    time.sleep(1)
    current_url = context.driver.current_url.lower()

    if pagina == "Solicitudes a Atender":
        assert "listar" in current_url or "solicitudes" in current_url, (
            f"No se regresó a la página de solicitudes. URL actual: {current_url}"
        )
    else:
        body = context.driver.find_element(By.TAG_NAME, "body").text.lower()
        assert pagina.lower() in body, f"No se encontró la página '{pagina}'"
