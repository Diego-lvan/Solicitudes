from behave import given, then
from selenium.webdriver.common.by import By
from django.utils import timezone
from datetime import datetime, timedelta

from tipo_solicitudes.models import (
    TipoSolicitud, FormularioSolicitud, CampoFormulario,
    Solicitud, RespuestaCampo, SeguimientoSolicitud
)

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

TIPOS_SOLICITUD_DATA = {
    'Constancia de Estudios': {
        'descripcion': 'Solicitud de constancia que acredita que el alumno está inscrito',
        'responsable': '1',
        'campos': [
            {
                'nombre': 'motivo',
                'etiqueta': 'Motivo de la solicitud',
                'tipo': 'textarea',
                'requerido': True
            },
            {
                'nombre': 'semestre',
                'etiqueta': 'Semestre actual',
                'tipo': 'select',
                'opciones': '1,2,3,4,5,6,7,8,9',
                'requerido': True
            },
            {
                'nombre': 'fecha_necesaria',
                'etiqueta': 'Fecha en que necesita el documento',
                'tipo': 'date',
                'requerido': True
            },
        ],
        'respuestas_ejemplo': {
            'motivo': 'Necesito la constancia para trámite de beca',
            'semestre': '5',
            'fecha_necesaria': lambda: (
                timezone.now() + timedelta(days=15)
            ).strftime('%Y-%m-%d'),
        }
    },
}


def crear_tipo_solicitud_con_formulario(tipo_nombre, responsable):
    tipo_data = TIPOS_SOLICITUD_DATA.get(tipo_nombre)

    if tipo_data:
        descripcion = tipo_data['descripcion']
        campos_data = tipo_data['campos']
    else:
        descripcion = f'Tipo de solicitud: {tipo_nombre}'
        campos_data = [
            {'nombre': 'motivo', 'etiqueta': 'Motivo',
                'tipo': 'textarea', 'requerido': True},
        ]

    tipo, created = TipoSolicitud.objects.get_or_create(
        nombre=tipo_nombre,
        defaults={
            'descripcion': descripcion,
            'responsable': responsable
        }
    )

    if not created and tipo.responsable != responsable:
        tipo.responsable = responsable
        tipo.save()

    formulario, form_created = FormularioSolicitud.objects.get_or_create(
        tipo_solicitud=tipo,
        defaults={
            'nombre': f'Formulario {tipo_nombre}',
            'descripcion': f'Formulario para {descripcion.lower()}',
        }
    )

    if form_created:
        for i, campo_data in enumerate(campos_data):
            CampoFormulario.objects.create(
                formulario=formulario,
                nombre=campo_data['nombre'],
                etiqueta=campo_data['etiqueta'],
                tipo=campo_data['tipo'],
                requerido=campo_data.get('requerido', True),
                opciones=campo_data.get('opciones', ''),
                orden=i + 1
            )

    return tipo, formulario


def crear_respuestas_solicitud(solicitud, tipo_nombre):
    tipo_data = TIPOS_SOLICITUD_DATA.get(tipo_nombre)
    if not tipo_data:
        return

    respuestas_ejemplo = tipo_data.get('respuestas_ejemplo', {})

    try:
        formulario = solicitud.tipo_solicitud.formulario
        campos = formulario.campos.all()

        for campo in campos:
            if campo.tipo != 'file':
                valor = respuestas_ejemplo.get(campo.nombre, '')
                if callable(valor):
                    valor = valor()

                RespuestaCampo.objects.create(
                    solicitud=solicitud,
                    campo=campo,
                    valor=valor
                )
    except Exception:
        pass


@given('existen las siguientes solicitudes con historial asignadas a "{rol}":')
def step_crear_solicitudes_con_historial(context, rol):
    responsable = ROL_A_RESPONSABLE.get(rol, '1')

    for row in context.table:
        folio = row['folio']
        tipo_nombre = row['tipo_solicitud']
        estado = row['estado']

        tipo, formulario = crear_tipo_solicitud_con_formulario(
            tipo_nombre, responsable)

        estatus = ESTADO_A_ESTATUS.get(estado, '1')

        Solicitud.objects.filter(folio=folio).delete()

        solicitud = Solicitud.objects.create(
            usuario=context.usuario,
            tipo_solicitud=tipo,
            folio=folio,
            estatus=estatus
        )

        crear_respuestas_solicitud(solicitud, tipo_nombre)

        # Siempre crear seguimiento inicial "Creada"
        SeguimientoSolicitud.objects.create(
            solicitud=solicitud,
            estatus='1',
            observaciones='Solicitud creada por el usuario'
        )

        # Si el estado es "En proceso" o superior, agregar seguimiento
        if estatus in ['2', '3', '4']:
            SeguimientoSolicitud.objects.create(
                solicitud=solicitud,
                estatus='2',
                observaciones='La solicitud está siendo revisada'
            )

        # Si el estado es "Terminada", agregar seguimiento final
        if estatus == '3':
            SeguimientoSolicitud.objects.create(
                solicitud=solicitud,
                estatus='3',
                observaciones='Solicitud aprobada y procesada'
            )

        # Si el estado es "Cancelada", agregar seguimiento de cancelación
        if estatus == '4':
            SeguimientoSolicitud.objects.create(
                solicitud=solicitud,
                estatus='4',
                observaciones='Solicitud cancelada'
            )


@then('debe ver el historial de seguimiento con las siguientes entradas:')
def step_verificar_historial_entradas(context):
    seguimientos_table = context.driver.find_element(
        By.ID, "seguimientos-table")
    table_body = seguimientos_table.find_element(By.TAG_NAME, "tbody")
    filas = table_body.find_elements(By.TAG_NAME, "tr")
    filas_esperadas = [row for row in context.table]
    assert len(filas_esperadas) == len(filas), (
        f"Número de entradas en el historial ({len(filas)}) "
        f"no coincide con lo esperado ({len(filas_esperadas)})"
    )
    for i, row in enumerate(filas_esperadas):
        estado_esperado = row['Estado'].lower()
        observaciones_esperadas = row['Observaciones'].lower()

        celdas = filas[i].find_elements(By.TAG_NAME, "td")

        assert estado_esperado in celdas[1].text.lower(), (
            f"No se encontró el estado '{row['Estado']}' en el historial"
        )

        assert observaciones_esperadas in celdas[2].text.lower(), (
            f"No se encontró la observación '{row['Observaciones']}' en el historial "
            f"se encontraron: {celdas[2].text}"
        )


@then('cada entrada del historial debe mostrar una fecha')
def step_verificar_fechas_historial(context):
    seguimientos_table = context.driver.find_element(
        By.ID, "seguimientos-table")
    table_body = seguimientos_table.find_element(By.TAG_NAME, "tbody")
    filas = table_body.find_elements(By.TAG_NAME, "tr")
    for fila in filas:
        celdas = fila.find_elements(By.TAG_NAME, "td")
        fecha_texto = celdas[0].text.strip()
        assert fecha_texto != "", "Una entrada del historial no tiene fecha"


@then('el historial debe estar ordenado cronológicamente')
def step_verificar_orden_cronologico(context):
    seguimientos_table = context.driver.find_element(
        By.ID, "seguimientos-table")
    table_body = seguimientos_table.find_element(By.TAG_NAME, "tbody")
    filas = table_body.find_elements(By.TAG_NAME, "tr")
    for i, fila in enumerate(filas):
        celdas_actual = fila.find_elements(By.TAG_NAME, "td")
        if i == 0:
            estatus = celdas_actual[1].text.strip()
            assert estatus == "Creada", (
                f"La primera entrada del historial debe ser 'Creada', pero es '{estatus}'"
            )
            continue
        fecha_actual_texto = celdas_actual[0].text.strip()
        estatus_actual = celdas_actual[1].text.strip()

        fila_anterior = filas[i - 1]
        celdas_anterior = fila_anterior.find_elements(By.TAG_NAME, "td")
        estatus_anterior = celdas_anterior[1].text.strip()
        fecha_anterior_texto = celdas_anterior[0].text.strip()

        fecha_actual = datetime.strptime(fecha_actual_texto, '%d/%m/%Y %H:%M')
        fecha_anterior = datetime.strptime(
            fecha_anterior_texto, '%d/%m/%Y %H:%M')

        assert fecha_actual >= fecha_anterior, (
            f"El historial no está en orden cronológico: {fecha_actual_texto} "
            f"viene antes que {fecha_anterior_texto}"
        )
        if estatus_anterior == "Creada":
            assert estatus_actual == "En proceso", (
                f"Después de 'Creada' debe venir 'En proceso', pero viene '{estatus_actual}'"
            )
        elif estatus_anterior == "En proceso":
            assert estatus_actual in ["Terminada", "Cancelada"], (
                f"Después de 'En proceso' debe venir 'Terminada' o 'Cancelada', "
                f"pero viene '{estatus_actual}'"
            )
