# app/solicitudes/atender_solicitudes/tests/test_forms.py
from django.test import TestCase
from atender_solicitudes.forms import CerrarSolicitudForm


class SmokeAtenderSolicitudesTests(TestCase):
    def test_smoke(self):
        self.assertTrue(True)


class CerrarSolicitudFormTests(TestCase):
    def test_form_valido_con_datos_correctos(self):
        data = {
            "estatus": "3",
            "observaciones": "La solicitud fue atendida correctamente."
        }
        form = CerrarSolicitudForm(data=data)
        self.assertTrue(form.is_valid())
        # Se normalizan espacios
        self.assertEqual(form.cleaned_data["estatus"], "3")
        self.assertEqual(
            form.cleaned_data["observaciones"],
            "La solicitud fue atendida correctamente."
        )

    def test_form_valido_con_estatus_cancelada(self):
        """Prueba que el estatus 4 (Cancelada) también es válido."""
        data = {
            "estatus": "4",
            "observaciones": "Solicitud cancelada por el usuario."
        }
        form = CerrarSolicitudForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["estatus"], "4")

    def test_falla_si_estatus_invalido(self):
        data = {
            "estatus": "5",   # valor no permitido
            "observaciones": "Texto cualquiera"
        }
        form = CerrarSolicitudForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("estatus", form.errors)
        # Validar mensaje específico de error
        self.assertIn(
            "Estatus inválido. Use 3 (Terminada) o 4 (Cancelada)",
            str(form.errors["estatus"])
        )

    def test_falla_si_estatus_vacio(self):
        """Prueba que falla si no se proporciona estatus."""
        data = {
            "observaciones": "Texto cualquiera"
        }
        form = CerrarSolicitudForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("estatus", form.errors)
        self.assertIn("obligatorio", str(form.errors["estatus"]))

    def test_falla_si_observaciones_vacias(self):
        data = {
            "estatus": "3",
            "observaciones": "   ",  # solo espacios
        }
        form = CerrarSolicitudForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("observaciones", form.errors)
        # Validar mensaje específico de error
        self.assertIn(
            "Las observaciones son obligatorias",
            str(form.errors["observaciones"])
        )

    def test_falla_si_observaciones_no_proporcionadas(self):
        data = {
            "estatus": "3"
        }
        form = CerrarSolicitudForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("observaciones", form.errors)
        self.assertIn("obligatorias", str(form.errors["observaciones"]))

    def test_clean_estatus_valida_valor_no_permitido(self):
        form = CerrarSolicitudForm(data={
            "estatus": "3",
            "observaciones": "Texto"
        })

        form.is_valid()
        form.cleaned_data['estatus'] = '5'
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            form.clean_estatus()
        self.assertIn("Estatus inválido", str(ctx.exception))

    def test_clean_observaciones_valida_valor_vacio(self):
        form = CerrarSolicitudForm(data={
            "estatus": "3",
            "observaciones": "Texto"
        })
        form.is_valid()
        form.cleaned_data['observaciones'] = ''
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            form.clean_observaciones()
        self.assertIn("obligatorias", str(ctx.exception))
