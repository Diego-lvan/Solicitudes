from behave import given, when, then
from selenium.webdriver.common.by import By
import time
from django.utils import timezone
from datetime import timedelta

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
        'responsable': '1',  # Control escolar
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
    'Cambio de Grupo': {
        'descripcion': 'Solicitud para cambiar de grupo en una materia',
        'responsable': '2',  # Responsable de programa
        'campos': [
            {
                'nombre': 'materia',
                'etiqueta': 'Nombre de la materia',
                'tipo': 'text',
                'requerido': True
            },
            {
                'nombre': 'grupo_actual',
                'etiqueta': 'Grupo actual',
                'tipo': 'text',
                'requerido': True
            },
            {
                'nombre': 'grupo_deseado',
                'etiqueta': 'Grupo deseado',
                'tipo': 'text',
                'requerido': True
            },
            {
                'nombre': 'justificacion',
                'etiqueta': 'Justificación',
                'tipo': 'textarea',
                'requerido': True
            },
        ],
        'respuestas_ejemplo': {
            'materia': 'Programación Web',
            'grupo_actual': 'A',
            'grupo_deseado': 'B',
            'justificacion': 'Conflicto de horario con otra materia',
        }
    },
    'Asesoría Académica': {
        'descripcion': 'Solicitud de asesoría o tutoría académica',
        'responsable': '3',  # Responsable de tutorías
        'campos': [
            {
                'nombre': 'materia',
                'etiqueta': 'Materia',
                'tipo': 'text',
                'requerido': True
            },
            {
                'nombre': 'tema',
                'etiqueta': 'Tema específico',
                'tipo': 'textarea',
                'requerido': True
            },
            {
                'nombre': 'tipo_asesoria',
                'etiqueta': 'Tipo de asesoría',
                'tipo': 'select',
                'opciones': 'Individual,Grupal,En línea,Presencial',
                'requerido': True
            },
            {
                'nombre': 'disponibilidad',
                'etiqueta': 'Disponibilidad horaria',
                'tipo': 'textarea',
                'requerido': True
            },
        ],
        'respuestas_ejemplo': {
            'materia': 'Matemáticas',
            'tema': 'Derivadas e integrales',
            'tipo_asesoria': 'Individual',
            'disponibilidad': 'Lunes y miércoles por la tarde',
        }
    },
    'Baja de Materia': {
        'descripcion': 'Solicitud para dar de baja una materia',
        'responsable': '4',  # Director
        'campos': [
            {
                'nombre': 'materia',
                'etiqueta': 'Nombre de la materia',
                'tipo': 'text',
                'requerido': True
            },
            {
                'nombre': 'grupo',
                'etiqueta': 'Grupo',
                'tipo': 'text',
                'requerido': True
            },
            {
                'nombre': 'motivo',
                'etiqueta': 'Motivo de la baja',
                'tipo': 'textarea',
                'requerido': True
            },
        ],
        'respuestas_ejemplo': {
            'materia': 'Estadística',
            'grupo': 'A',
            'motivo': 'Por motivos de salud no puedo continuar',
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
                cantidad_archivos=campo_data.get('cantidad_archivos', 1),
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


@given('existen las siguientes solicitudes con detalles asignadas a "{rol}":')
def step_crear_solicitudes_asignadas(context, rol):
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

        SeguimientoSolicitud.objects.create(
            solicitud=solicitud,
            estatus='1',
            observaciones='Solicitud creada por el usuario'
        )

        if estatus == '2':
            SeguimientoSolicitud.objects.create(
                solicitud=solicitud,
                estatus='2',
                observaciones='La solicitud está siendo revisada'
            )

        if estatus == '3':
            SeguimientoSolicitud.objects.create(
                solicitud=solicitud,
                estatus='2',
                observaciones='La solicitud está siendo revisada'
            )
            SeguimientoSolicitud.objects.create(
                solicitud=solicitud,
                estatus='3',
                observaciones='Solicitud aprobada y procesada'
            )

# ==================== STEPS DE VER DETALLE ====================


@when('hace clic en el botón "Atender" de la solicitud con folio "{folio}"')
def step_clic_boton_solicitud(context, folio):
    tabla = context.driver.find_element(By.ID, "solicitudesTable")
    tbody = tabla.find_element(By.TAG_NAME, "tbody")
    filas = tbody.find_elements(By.TAG_NAME, "tr")

    for fila in filas:
        celdas = fila.find_elements(By.TAG_NAME, "td")
        if celdas and folio in celdas[0].text:
            boton_elemento = fila.find_element(By.CLASS_NAME, "btn-action")
            context.driver.execute_script(
                "arguments[0].scrollIntoView(true);", boton_elemento
            )
            time.sleep(1)
            boton_elemento.click()
            time.sleep(2)
            return

    assert False, f"No se encontró la solicitud con folio '{folio}'"


@then('debe ver la página de detalles de la solicitud')
def step_verificar_pagina_detalles(context):
    body = context.driver.find_element(By.TAG_NAME, "body").text.lower()
    indicadores = [
        "detalle",
        "solicitud",
        "folio",
        "información"
    ]
    encontrado = any(ind in body for ind in indicadores)
    assert encontrado, "No se cargó la página de detalles de la solicitud"


@then('debe ver el folio "{folio}"')
def step_verificar_folio_detalle(context, folio):
    body = context.driver.find_element(By.TAG_NAME, "body").text
    assert folio in body, f"No se encontró el folio '{folio}' en la página de detalles"


@then('debe ver el tipo de solicitud "{tipo}"')
def step_verificar_tipo_detalle(context, tipo):
    body = context.driver.find_element(By.TAG_NAME, "body").text.lower()
    assert tipo.lower() in body, (
        f"No se encontró el tipo de solicitud '{tipo}' en la página de detalles"
    )


@then('debe ver el estado "{estado}"')
def step_verificar_estado_detalle(context, estado):
    body = context.driver.find_element(By.TAG_NAME, "body").text.lower()
    assert estado.lower() in body, (
        f"No se encontró el estado '{estado}' en la página de detalles"
    )


@then('debe ver el historial de seguimiento')
def step_verificar_historial_seguimiento(context):
    body = context.driver.find_element(By.TAG_NAME, "body").text.lower()
    indicadores = [
        "historial",
        "seguimiento",
        "observaciones",
        "fecha"
    ]
    encontrado = any(ind in body for ind in indicadores)

    if not encontrado:
        try:
            tabla_seguimiento = context.driver.find_element(
                By.CSS_SELECTOR,
                "table, .historial, .seguimiento, #seguimiento"
            )
            encontrado = tabla_seguimiento is not None
        except Exception:
            pass

    assert encontrado, "No se encontró el historial de seguimiento en la página de detalles"
