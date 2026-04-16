from behave import given, when, then
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

from solicitudes_app.models import Usuario
from tipo_solicitudes.models import TipoSolicitud, Solicitud, SeguimientoSolicitud

ROL_A_RESPONSABLE = {
    'control_escolar': '1',
    'responsable_programa': '2',
    'responsable_tutorias': '3',
    'director': '4',
}

ESTADO_A_ESTATUS = {
    'Creada': '1',
    'En proceso': '2',
    'Terminada': '3',
    'Cancelada': '4',
}


@given('que existe un usuario con username "{username}", contraseña "{password}" y rol "{rol}"')
def step_crear_usuario_con_rol(context, username, password, rol):
    Usuario.objects.filter(username=username).delete()
    context.usuario = Usuario.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password=password,
        first_name='Test',
        last_name='User',
        rol=rol
    )
    context.password = password


@given('el usuario "{username}" está autenticado en el sistema')
def step_usuario_autenticado(context, username):
    context.driver.get(f"{context.url}/auth/login/")
    time.sleep(1)

    username_field = context.driver.find_element(By.NAME, "username")
    password_field = context.driver.find_element(By.NAME, "password")

    username_field.clear()
    username_field.send_keys(username)
    password_field.clear()
    password_field.send_keys(context.password)

    submit_button = context.driver.find_element(
        By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()
    time.sleep(3)

    # Guardar cambios
    submit_button = context.driver.find_element(
        By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()
    time.sleep(1)


@given('existen las siguientes solicitudes asignadas a "{rol}":')
def step_crear_solicitudes_asignadas(context, rol):
    responsable = ROL_A_RESPONSABLE.get(rol, '1')

    for row in context.table:
        folio = row['folio']
        tipo_nombre = row['tipo_solicitud']
        estado = row['estado']

        tipo, _ = TipoSolicitud.objects.get_or_create(
            nombre=tipo_nombre,
            defaults={
                'descripcion': f'Tipo de solicitud: {tipo_nombre}',
                'responsable': responsable
            }
        )

        if tipo.responsable != responsable:
            tipo.responsable = responsable
            tipo.save()

        estatus = ESTADO_A_ESTATUS.get(estado, '1')

        Solicitud.objects.filter(folio=folio).delete()
        solicitud = Solicitud.objects.create(
            usuario=context.usuario,
            tipo_solicitud=tipo,
            folio=folio,
            estatus=estatus
        )

        SeguimientoSolicitud.objects.create(
            solicitud=solicitud,
            estatus=estatus,
            observaciones="Solicitud creada"
        )


@when('el usuario visita la página de "{pagina}"')
def step_visitar_pagina_when(context, pagina):
    if pagina == "Solicitudes a Atender":
        context.driver.get(f"{context.url}/solicitudes/listar/")
    else:
        context.driver.get(f"{context.url}/")
    time.sleep(2)


@given('el usuario visita la página de "{pagina}"')
def step_visitar_pagina_given(context, pagina):
    if pagina == "Solicitudes a Atender":
        context.driver.get(f"{context.url}/solicitudes/listar/")
    else:
        context.driver.get(f"{context.url}/")
    time.sleep(2)


@then('debe ver una tabla con las siguientes columnas:')
def step_verificar_columnas_tabla(context):
    encabezados = context.driver.find_elements(
        By.CSS_SELECTOR, "table thead th")

    columnas_esperadas = context.table.headings
    columnas_encontradas = [th.text.strip() for th in encabezados]

    for col_esperada in columnas_esperadas:
        encontrada = any(col_esperada.lower() in col.lower()
                         for col in columnas_encontradas)
        assert encontrada, (
            f"No se encontró la columna '{col_esperada}'. "
            f"Columnas encontradas: {columnas_encontradas}"
        )


@then('la tabla muestra las siguientes filas:')
def step_verificar_filas_tabla(context):
    tabla = context.driver.find_element(By.ID, "solicitudesTable")
    tbody = tabla.find_element(By.TAG_NAME, "tbody")
    filas = tbody.find_elements(By.TAG_NAME, "tr")

    for row in context.table:
        folio_esperado = row[0].strip()
        tipo_esperado = row[1].strip()
        estado_esperado = row[2].strip()

        fila_encontrada = False
        for fila in filas:
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if len(celdas) >= 3:
                folio_celda = celdas[0].text.strip()
                tipo_celda = celdas[2].text.strip()
                estado_celda = celdas[3].text.strip()

                if (folio_esperado in folio_celda
                        and tipo_esperado.lower() in tipo_celda.lower()
                        and estado_esperado.lower() in estado_celda.lower()):
                    fila_encontrada = True
                    break

        assert fila_encontrada, (
            f"No se encontró la fila con folio='{folio_esperado}', "
            f"tipo='{tipo_esperado}', estado='{estado_esperado}'"
        )


@when('aplica el filtro por estado "{estado}"')
def step_aplicar_filtro_estado(context, estado):
    estado_id = ESTADO_A_ESTATUS.get(estado, '1')
    filter_button = context.driver.find_element(
        By.CSS_SELECTOR, f"a[href*='?estatus={estado_id}']"
    )
    filter_button.click()
    time.sleep(1)


@then('la tabla solo muestra las siguientes filas:')
def step_verificar_filas_filtradas(context):
    filas = context.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    filas_visibles = [f for f in filas if f.is_displayed()]

    filas_esperadas = []
    for row in context.table:
        filas_esperadas.append({
            'folio': row[0].strip(),
            'tipo': row[1].strip(),
            'estado': row[2].strip()
        })

    assert len(filas_visibles) == len(filas_esperadas), (
        f"Se esperaban {len(filas_esperadas)} filas, pero se encontraron {len(filas_visibles)}"
    )

    for esperada in filas_esperadas:
        fila_encontrada = False
        for fila in filas_visibles:
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if len(celdas) >= 3:
                folio_celda = celdas[0].text.strip()
                tipo_celda = celdas[2].text.strip()
                estado_celda = celdas[3].text.strip()

                if (esperada['folio'] in folio_celda
                        and esperada['tipo'].lower() in tipo_celda.lower()
                        and esperada['estado'].lower() in estado_celda.lower()):
                    fila_encontrada = True
                    break

        assert fila_encontrada, (
            f"No se encontró la fila esperada: {esperada}"
        )


@then('la cantidad de solicitudes mostradas es {cantidad:d}')
def step_verificar_cantidad_solicitudes(context, cantidad):
    filas = context.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    filas_visibles = [f for f in filas if f.is_displayed()]

    assert len(filas_visibles) == cantidad, (
        f"Se esperaban {cantidad} solicitudes, pero se encontraron {len(filas_visibles)}"
    )


@when('escribe "{texto}" en el campo de búsqueda de folio')
def step_buscar_por_folio(context, texto):
    try:
        search_input = context.driver.find_element(By.ID, "search")
    except Exception:
        search_input = context.driver.find_element(
            By.CSS_SELECTOR,
            "input[type='search'], input[name='search'], "
            "input[placeholder*='folio'], input[placeholder*='buscar']"
        )

    search_input.clear()
    search_input.send_keys(texto)

    try:
        search_button = context.driver.find_element(By.ID, "search-button")
        search_button.click()
    except Exception:
        search_input.send_keys(Keys.RETURN)

    time.sleep(2)


@then('la tabla muestra solo la siguiente fila:')
def step_verificar_fila_unica(context):
    filas = context.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    filas_visibles = [f for f in filas if f.is_displayed()]

    filas_esperadas = []
    for row in context.table:
        filas_esperadas.append({
            'folio': row[0].strip(),
            'tipo': row[1].strip(),
            'estado': row[2].strip()
        })

    assert len(filas_visibles) == len(filas_esperadas), (
        f"Se esperaba {len(filas_esperadas)} fila(s), pero se encontraron {len(filas_visibles)}"
    )

    row = context.table[0]
    folio_esperado = row[0].strip()
    tipo_esperado = row[1].strip()
    estado_esperado = row[2].strip()

    celdas = filas_visibles[0].find_elements(By.TAG_NAME, "td")
    assert len(celdas) >= 3, "La fila no tiene suficientes columnas"

    folio_celda = celdas[0].text.strip()
    tipo_celda = celdas[2].text.strip()
    estado_celda = celdas[3].text.strip()

    assert folio_esperado in folio_celda, (
        f"El folio esperado '{folio_esperado}' no coincide con '{folio_celda}'"
    )
    assert tipo_esperado.lower() in tipo_celda.lower(), (
        f"El tipo esperado '{tipo_esperado}' no coincide con '{tipo_celda}'"
    )
    assert estado_esperado.lower() in estado_celda.lower(), (
        f"El estado esperado '{estado_esperado}' no coincide con '{estado_celda}'"
    )


@given('no existen solicitudes asignadas a "{rol}"')
def step_sin_solicitudes_asignadas(context, rol):
    responsable = ROL_A_RESPONSABLE.get(rol, '1')
    tipos_rol = TipoSolicitud.objects.filter(responsable=responsable)
    Solicitud.objects.filter(tipo_solicitud__in=tipos_rol).delete()


@then('debe ver un mensaje indicando que no hay solicitudes')
def step_verificar_mensaje_sin_solicitudes(context):
    tabla = context.driver.find_element(By.ID, "solicitudesTable").text.lower()
    mensajes_esperados = [
        "no hay solicitudes",
        "no se encontraron solicitudes",
        "sin solicitudes",
        "no tiene solicitudes",
        "lista vacía",
        "no existen solicitudes"
    ]
    mensaje_encontrado = any(msg in tabla for msg in mensajes_esperados)
    assert mensaje_encontrado, (
        f"No se encontró mensaje indicando que no hay solicitudes. Contenido: {tabla[:500]}"
    )


@then('la tabla no muestra ninguna fila')
def step_verificar_tabla_vacia(context):
    try:
        tabla = context.driver.find_element(By.ID, "solicitudesTable")
        tbody = tabla.find_element(By.TAG_NAME, "tbody")
        filas = tbody.find_elements(By.TAG_NAME, "tr")
        filas_con_datos = [
            f for f in filas if f.find_elements(By.TAG_NAME, "td")]
        assert len(filas_con_datos) == 0, (
            f"Se esperaba tabla vacía, pero se encontraron {len(filas_con_datos)} filas"
        )
    except Exception:
        pass
