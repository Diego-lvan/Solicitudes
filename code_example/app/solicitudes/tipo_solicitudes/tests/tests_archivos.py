from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, datetime
from solicitudes_app.models import Usuario
from tipo_solicitudes.models import TipoSolicitud, Solicitud
from tipo_solicitudes.views import _crear_grafico


class VistaTresGraficasTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username='testuser1',
            password='test123'
        )
        self.user.perfil_completo = True
        self.user.debe_cambiar_password = False
        self.user.save()

        self.client.login(username='testuser1', password='test123')

        # Crear tipo de solicitud de prueba
        self.tiposDeSolicitud = []
        for i in range(7):
            tipos = TipoSolicitud.objects.create(
                nombre=f'Tipo Soli {i}',
                descripcion=f'Des {i}',
                responsable=str(i)
            )
            self.tiposDeSolicitud.append(tipos)

        hoy = datetime.now()
        semana_pasada = hoy - timedelta(days=5)
        mes_pasado = hoy - timedelta(days=30)

        Solicitud.objects.create(
            usuario=self.user,
            tipo_solicitud=self.tiposDeSolicitud[0],
            folio='Grafica-001',
            fecha_creacion=hoy
        )

        Solicitud.objects.create(
            usuario=self.user,
            tipo_solicitud=self.tiposDeSolicitud[1],
            folio='Grafica-002',
            fecha_creacion=hoy
        )

        Solicitud.objects.create(
            usuario=self.user,
            tipo_solicitud=self.tiposDeSolicitud[2],
            folio='Grafica-003',
            fecha_creacion=semana_pasada
        )

        Solicitud.objects.create(
            usuario=self.user,
            tipo_solicitud=self.tiposDeSolicitud[3],
            folio='Grafica-004',
            fecha_creacion=mes_pasado
        )

    def test_pagina_graficas(self):
        url = reverse("grafica_solicitudes")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_template_graficas(self):
        url = reverse("grafica_solicitudes")
        response = self.client.get(url)
        self.assertTemplateUsed(response, "grafica.html")

    def test_vista_tres_graficas_context(self):
        url = reverse("grafica_solicitudes")
        response = self.client.get(url)

        self.assertIn("hoy", response.context)
        self.assertIn("semana", response.context)
        self.assertIn("mes", response.context)

        self.assertGreaterEqual(len(response.context["hoy"]), 1)
        self.assertGreaterEqual(len(response.context["semana"]), 1)
        self.assertGreaterEqual(len(response.context["mes"]), 1)


class TestDescargas(TestCase):

    def setUp(self):
        self.user = Usuario.objects.create_user(
            username='testuser',
            password='test123'
        )
        self.user.perfil_completo = True
        self.user.debe_cambiar_password = False
        self.user.save()

        self.client.login(username='testuser', password='test123')

        # Crear tipo de solicitud de prueba
        self.tiposDeSolicitud = []
        for i in range(7):
            tipos = TipoSolicitud.objects.create(
                nombre=f'Tipo Solicitud {i}',
                descripcion=f'Descripción {i}',
                responsable=str(i)
            )
            self.tiposDeSolicitud.append(tipos)

        self.tipoSolicitudGrande = TipoSolicitud.objects.create(
            nombre='Solicitud de cambio de programa academico',
            descripcion='Descripción grande',
            responsable='9'
        )
        self.tipoSolicitudGrandeTresPalabras = TipoSolicitud.objects.create(
            nombre='Solicitud de matriculacion',
            descripcion='Descripción mediana',
            responsable='8'
        )
        self.tipoSolicitudPalabrota = TipoSolicitud.objects.create(
            nombre='Paranguaricutirimicuaro',
            descripcion='Descripciónsotaaaaaa',
            responsable='7'
        )
        self.tipoSolicitudLargota = TipoSolicitud.objects.create(
            nombre='ParanguaricutirimicuaroParanguaricutirimicuaro',
            descripcion='DescripciónsotaaaaaaDescripciónsotaaaaaa',
            responsable='7'
        )
        self.tiposDeSolicitud.append(self.tipoSolicitudGrande)
        self.tiposDeSolicitud.append(self.tipoSolicitudGrandeTresPalabras)
        self.tiposDeSolicitud.append(self.tipoSolicitudPalabrota)
        self.tiposDeSolicitud.append(self.tipoSolicitudLargota)

    # -------------------------------------------------
    # TEST 1: Descarga de PDF funciona sin datos
    # -------------------------------------------------
    def test_descarga_pdf_sin_datos(self):
        url = reverse("generar_pdf_graficas")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("graficas_solicitudes.pdf",
                      response["Content-Disposition"])

    # -------------------------------------------------
    # TEST 2: Descarga de PDF funciona con menos de 5 solicitudes
    # -------------------------------------------------
    def test_descarga_pdf_con_datos(self):
        # Crear varias solicitudes de prueba
        for i in range(3):
            Solicitud.objects.create(
                usuario=self.user,
                tipo_solicitud=self.tiposDeSolicitud[i],
                folio=f'TEST-{i:03d}',
                fecha_creacion=timezone.now() - timedelta(days=i)
            )

        url = reverse("generar_pdf_graficas")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        # Verificar que el PDF no esté vacío
        self.assertGreater(len(response.content), 1000)

    # -------------------------------------------------
    # TEST 3: Descarga de CSV funciona sin datos
    # -------------------------------------------------
    def test_descarga_csv_sin_datos(self):
        url = reverse("generar_csv_graficas")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("solicitudes.csv", response["Content-Disposition"])

        # Verificar que contenga al menos los encabezados
        content = response.content.decode('utf-8')
        self.assertIn('ID', content)
        self.assertIn('Usuario', content)
        self.assertIn('Tipo de Solicitud', content)

    # -------------------------------------------------
    # TEST 4: Descarga de CSV funciona con datos
    # -------------------------------------------------
    def test_descarga_csv_con_datos(self):
        # Crear solicitudes de prueba
        Solicitud.objects.create(
            usuario=self.user,
            tipo_solicitud=self.tiposDeSolicitud[0],
            folio='CSV-001',
            fecha_creacion=timezone.now()
        )
        Solicitud.objects.create(
            usuario=self.user,
            tipo_solicitud=self.tiposDeSolicitud[1],
            folio='CSV-002',
            fecha_creacion=timezone.now()
        )

        url = reverse("generar_csv_graficas")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

        content = response.content.decode('utf-8')
        # Verificar que contenga los datos de las solicitudes
        self.assertIn('CSV-001', content)
        self.assertIn('CSV-002', content)
        self.assertIn('testuser', content)
        self.assertIn('Tipo Solicitud 1', content)

    # -------------------------------------------------
    # TEST 5: PDF con mas de 5 tipos de solicitudes
    # -------------------------------------------------
    def test_pdf_multiples_tipos_solicitudes(self):
        # Crear varias solicitudes de prueba
        for i in range(7):
            Solicitud.objects.create(
                usuario=self.user,
                tipo_solicitud=self.tiposDeSolicitud[i],
                folio=f'TEST-{i:03d}',
                fecha_creacion=timezone.now() - timedelta(days=i)
            )

        url = reverse("generar_pdf_graficas")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        # Verificar que el PDF no esté vacío
        self.assertGreater(len(response.content), 1000)

    # -------------------------------------------------
    # TEST 6: CSV con caracteres especiales
    # -------------------------------------------------
    def test_csv_caracteres_especiales(self):
        # Crear tipo con caracteres especiales
        tipo_especial = TipoSolicitud.objects.create(
            nombre='Solicitud con áéíóú ñ',
            descripcion='Descripción especial',
            responsable='3'
        )

        Solicitud.objects.create(
            usuario=self.user,
            tipo_solicitud=tipo_especial,
            folio='ESPECIAL-001',
        )

        url = reverse("generar_csv_graficas")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('ESPECIAL-001', content)

    # -------------------------------------------------
    # TEST 7: Crear grafico sin datos
    # -------------------------------------------------
    def test_crear_grafico_sin_datos(self):
        resultado = _crear_grafico([], "Titulo Prueba")
        self.assertIsNone(resultado)

    # -------------------------------------------------
    # TEST 8: Crear grafico con varias palabras por etiqueta
    # -------------------------------------------------
    def test_pdf_varias_palabras(self):
        Solicitud.objects.create(
            usuario=self.user,
            tipo_solicitud=self.tipoSolicitudPalabrota,
            folio='TEST-001',
            fecha_creacion=timezone.now() - timedelta(days=1)
        )
        Solicitud.objects.create(
            usuario=self.user,
            tipo_solicitud=self.tipoSolicitudGrande,
            folio='TEST-002',
            fecha_creacion=timezone.now() - timedelta(days=2)
        )
        Solicitud.objects.create(
            usuario=self.user,
            tipo_solicitud=self.tipoSolicitudGrandeTresPalabras,
            folio='TEST-007',
            fecha_creacion=timezone.now() - timedelta(days=3)
        )
        Solicitud.objects.create(
            usuario=self.user,
            tipo_solicitud=self.tipoSolicitudLargota,
            folio='TEST-666',
            fecha_creacion=timezone.now() - timedelta(days=3)
        )

        url = reverse("generar_pdf_graficas")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        # Verificar que el PDF no esté vacío
        self.assertGreater(len(response.content), 1000)
