"""
Tests para funciones auxiliares de validación en views
"""
from django.test import TestCase
from solicitudes_app.models import Usuario
from solicitudes_app.views import (
    _validar_edicion_propio_usuario,
    _validar_ultimo_admin,
    _verificar_admin_predeterminado,
    _procesar_form_invalido
)
from solicitudes_app.forms import LoginForm


class ValidarEdicionPropioUsuarioTest(TestCase):
    """Tests para _validar_edicion_propio_usuario"""

    def setUp(self):
        self.admin1 = Usuario.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='TestPass123',
            rol='administrador',
            perfil_completo=True
        )
        self.admin2 = Usuario.objects.create_user(
            username='admin2',
            email='admin2@test.com',
            password='TestPass123',
            rol='administrador',
            perfil_completo=True
        )

    def test_validar_usuario_diferente_retorna_none(self):
        """Validar usuario diferente retorna None"""
        form_data = {'rol': 'alumno', 'is_active': True}
        result = _validar_edicion_propio_usuario(
            self.admin2, self.admin1, form_data)
        self.assertIsNone(result)

    def test_validar_propio_usuario_con_rol_valido_retorna_none(self):
        """Validar propio usuario con rol administrador válido retorna None"""
        form_data = {'rol': 'administrador', 'is_active': True}
        result = _validar_edicion_propio_usuario(
            self.admin1, self.admin1, form_data)
        self.assertIsNone(result)

    def test_validar_propio_usuario_cambiando_rol_retorna_error(self):
        """Validar propio usuario cambiando rol retorna error"""
        form_data = {'rol': 'alumno', 'is_active': True}
        result = _validar_edicion_propio_usuario(
            self.admin1, self.admin1, form_data)
        self.assertIsNotNone(result)
        self.assertIn('propio rol', result)

    def test_validar_propio_usuario_desactivando_cuenta_retorna_error(self):
        """Validar propio usuario desactivando cuenta retorna error"""
        form_data = {'rol': 'administrador', 'is_active': False}
        result = _validar_edicion_propio_usuario(
            self.admin1, self.admin1, form_data)
        self.assertIsNotNone(result)
        self.assertIn('desactivar', result)


class ValidarUltimoAdminTest(TestCase):
    """Tests para _validar_ultimo_admin"""

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username='admin_unico',
            email='admin@test.com',
            password='TestPass123',
            rol='administrador',
            is_active=True,
            perfil_completo=True
        )
        self.alumno = Usuario.objects.create_user(
            username='alumno1',
            email='alumno1@test.com',
            password='TestPass123',
            rol='alumno',
            perfil_completo=True
        )

    def test_validar_usuario_no_admin_retorna_none(self):
        """Validar usuario no admin retorna None"""
        form_data = {'rol': 'alumno', 'is_active': True}
        result = _validar_ultimo_admin(self.alumno, form_data)
        self.assertIsNone(result)

    def test_validar_admin_inactivo_retorna_none(self):
        """Validar admin inactivo retorna None"""
        self.admin.is_active = False
        self.admin.save()
        form_data = {'rol': 'administrador', 'is_active': False}
        result = _validar_ultimo_admin(self.admin, form_data)
        self.assertIsNone(result)

    def test_validar_ultimo_admin_cambiando_rol_retorna_error(self):
        """Validar último admin cambiando rol retorna error"""
        form_data = {'rol': 'alumno', 'is_active': True}
        result = _validar_ultimo_admin(self.admin, form_data)
        self.assertIsNotNone(result)
        self.assertIn('último administrador', result)

    def test_validar_ultimo_admin_desactivando_retorna_error(self):
        """Validar último admin desactivando cuenta retorna error"""
        form_data = {'rol': 'administrador', 'is_active': False}
        result = _validar_ultimo_admin(self.admin, form_data)
        self.assertIsNotNone(result)
        self.assertIn('último administrador', result)

    def test_validar_multiples_admins_permite_cambio(self):
        """Con múltiples admins permite cambio de rol"""
        # Crear segundo admin
        Usuario.objects.create_user(
            username='admin2',
            email='admin2@test.com',
            password='TestPass123',
            rol='administrador',
            is_active=True,
            perfil_completo=True
        )
        form_data = {'rol': 'alumno', 'is_active': True}
        result = _validar_ultimo_admin(self.admin, form_data)
        self.assertIsNone(result)


class VerificarAdminPredeterminadoTest(TestCase):
    """Tests para _verificar_admin_predeterminado"""

    def test_sin_admin_predeterminado_retorna_false(self):
        """Sin admin predeterminado retorna False"""
        result = _verificar_admin_predeterminado()
        self.assertFalse(result)

    def test_admin_predeterminado_con_debe_cambiar_password_retorna_true(self):
        """Admin predeterminado con debe_cambiar_password=True retorna True"""
        admin = Usuario.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='admin',
            rol='administrador',
            perfil_completo=True
        )
        admin.debe_cambiar_password = True
        admin.save()
        result = _verificar_admin_predeterminado()
        self.assertTrue(result)

    def test_admin_predeterminado_sin_debe_cambiar_password_retorna_false(self):
        """Admin predeterminado con debe_cambiar_password=False retorna False"""
        Usuario.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='admin',
            rol='administrador',
            perfil_completo=True,
            debe_cambiar_password=False
        )
        result = _verificar_admin_predeterminado()
        self.assertFalse(result)


class ProcesarFormInvalidoTest(TestCase):
    """Tests para _procesar_form_invalido"""

    def test_form_con_error_all_retorna_mensaje_credenciales(self):
        """Form con error __all__ retorna mensaje de credenciales incorrectas"""
        # Crear form inválido simulando error de credenciales
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/login/')
        
        form = LoginForm(request, data={
            'username': 'noexiste',
            'password': 'wrongpass'
        })
        form.is_valid()  # Esto genera errores
        
        result = _procesar_form_invalido(form)
        self.assertIn('Usuario o contraseña', result)

    def test_form_sin_error_all_retorna_mensaje_generico(self):
        """Form sin error __all__ retorna mensaje genérico"""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/login/')
        
        # Form con datos vacíos genera errores de campo requerido
        form = LoginForm(request, data={})
        form.is_valid()
        
        result = _procesar_form_invalido(form)
        self.assertIn('corrige los errores', result)
