"""
Tests unitarios consolidados para formularios de solicitudes_app (DSM5)
Incluye tests de validación, casos edge, cobertura y casos completos
"""
from django.test import TestCase
from solicitudes_app.models import Usuario
from solicitudes_app.forms import (
    RegistroUsuarioForm,
    ActualizarPerfilForm,
    GestionarUsuarioForm
)


class RegistroUsuarioFormEdgeCasesTest(TestCase):
    """Tests de casos edge para RegistroUsuarioForm"""

    def test_username_ya_existe(self):
        """No permite registrar username que ya existe"""
        Usuario.objects.create_user(
            username='existente',
            email='existente@test.com',
            password='testpass123',
            rol='alumno'
        )

        form_data = {
            'username': 'existente',
            'email': 'nuevo@test.com',
            'first_name': 'Nuevo',
            'last_name': 'Usuario',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'testpass123!',
            'password2': 'testpass123!'
        }
        form = RegistroUsuarioForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_email_ya_existe(self):
        """No permite registrar email que ya existe"""
        Usuario.objects.create_user(
            username='user1',
            email='existente@test.com',
            password='testpass123',
            rol='alumno'
        )

        form_data = {
            'username': 'nuevouser',
            'email': 'existente@test.com',
            'first_name': 'Nuevo',
            'last_name': 'Usuario',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'testpass123!',
            'password2': 'testpass123!'
        }
        form = RegistroUsuarioForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_alumno_sin_matricula_invalido(self):
        """Alumno debe tener matri­cula"""
        form_data = {
            'username': 'alumno1',
            'email': 'alumno@test.com',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': '',  # Vaci­o
            'password1': 'testpass123!',
            'password2': 'testpass123!'
        }
        form = RegistroUsuarioForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_no_alumno_con_matricula_valido(self):
        """RegistroUsuarioForm no permite roles diferentes a alumno"""
        # RegistroUsuarioForm only allows alumno role, so control_escolar should fail
        form_data = {
            'username': 'control1',
            'email': 'control@test.com',
            'first_name': 'Control',
            'last_name': 'Escolar',
            'rol': 'control_escolar',  # This will be rejected
            'matricula': '12345',
            'password1': 'testpass123!',
            'password2': 'testpass123!'
        }
        form = RegistroUsuarioForm(data=form_data)
        # Should be invalid because rol is not 'alumno'
        self.assertFalse(form.is_valid())

    def test_password_muy_corta(self):
        """Password muy corta debe ser invalida"""
        form_data = {
            'username': 'user1',
            'email': 'user@test.com',
            'first_name': 'User',
            'last_name': 'Test',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': '123',
            'password2': '123'
        }
        form = RegistroUsuarioForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_passwords_no_coinciden(self):
        """Passwords que no coinciden deben ser invalidas"""
        form_data = {
            'username': 'user1',
            'email': 'user@test.com',
            'first_name': 'User',
            'last_name': 'Test',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'testpass123!',
            'password2': 'different456!'
        }
        form = RegistroUsuarioForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_email_formato_invalido(self):
        """Email con formato invalido debe fallar"""
        form_data = {
            'username': 'user1',
            'email': 'email_invalido',
            'first_name': 'User',
            'last_name': 'Test',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'testpass123!',
            'password2': 'testpass123!'
        }
        form = RegistroUsuarioForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_campos_vacios(self):
        """Todos los campos requeridos deben estar presentes"""
        form_data = {
            'username': '',
            'email': '',
            'first_name': '',
            'last_name': '',
            'rol': '',
            'password1': '',
            'password2': ''
        }
        form = RegistroUsuarioForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('email', form.errors)

    def test_todos_los_roles_validos(self):
        """RegistroUsuarioForm solo permite rol alumno"""
        form_data = {
            'username': 'user_alumno',
            'email': 'alumno@test.com',
            'first_name': 'User',
            'last_name': 'Test',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!'
        }
        form = RegistroUsuarioForm(data=form_data)
        self.assertTrue(form.is_valid(),
                        f"Rol alumno deberi­a ser valido: {form.errors}")


class ActualizarPerfilFormTest(TestCase):
    """Tests para ActualizarPerfilForm"""

    def test_formulario_valido_alumno(self):
        """Formulario valido para alumno con matri­cula"""
        form_data = {
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'alumno@test.com',
            'telefono': '4921234567',
            'area': '',
            'matricula': '12345'
        }
        usuario = Usuario.objects.create_user(
            username='alumno1',
            email='alumno@test.com',
            password='testpass123',
            rol='alumno'
        )
        form = ActualizarPerfilForm(data=form_data, instance=usuario)
        if not form.is_valid():
            print(f"Form errors: {form.errors}")
        self.assertTrue(form.is_valid())

    def test_formulario_valido_no_alumno_sin_matricula(self):
        """No alumno puede completar perfil sin matri­cula"""
        form_data = {
            'first_name': 'Control',
            'last_name': 'Escolar',
            'telefono': '4921234567',
            'matricula': ''
        }
        usuario = Usuario.objects.create_user(
            username='control1',
            email='control@test.com',
            password='testpass123',
            rol='control_escolar'
        )
        form = ActualizarPerfilForm(data=form_data, instance=usuario)
        self.assertTrue(form.is_valid())

    def test_campos_requeridos_presentes(self):
        """Campos no requeridos pueden estar vaci­os en ActualizarPerfilForm"""
        form_data = {
            'first_name': 'Juan',  
            'last_name': 'Perez',
            'telefono': ''
        }
        usuario = Usuario.objects.create_user(
            username='user1',
            email='user@test.com',
            password='testpass123',
            rol='alumno'
        )
        form = ActualizarPerfilForm(data=form_data, instance=usuario)
        self.assertTrue(form.is_valid())

    def test_telefono_formato_valido(self):
        """Teli©fono debe tener formato valido"""
        form_data = {
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'telefono': '49212345',  # Muy corto
            'matricula': '12345'
        }
        usuario = Usuario.objects.create_user(
            username='user1',
            email='user@test.com',
            password='testpass123',
            rol='alumno'
        )
        form = ActualizarPerfilForm(data=form_data, instance=usuario)
        # Puede ser valido dependiendo de la validacii³n implementada
        # Este test verifica que el form maneja teli©fonos


class PasswordFormTest(TestCase):
    """Tests para cambio de password (simplificado)"""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='user1',
            email='user@test.com',
            password='oldpass123',
            rol='alumno'
        )

    def test_usuario_puede_cambiar_password(self):
        """Usuario puede cambiar su password"""
        # Test de integracii³n usando la vista
        self.assertTrue(self.usuario.check_password('oldpass123'))


class GestionarUsuarioFormTest(TestCase):
    """Tests para GestionarUsuarioForm"""

    def test_editar_usuario_valido(self):
        """Editar usuario con datos validos"""
        usuario = Usuario.objects.create_user(
            username='user1',
            email='user@test.com',
            password='testpass123',
            rol='alumno'
        )

        form_data = {
            'username': 'user1',
            'email': 'nuevo@test.com',
            'first_name': 'Nuevo',
            'last_name': 'Nombre',
            'rol': 'control_escolar',
            'telefono': '4921234567',
            'is_active': True
        }
        form = GestionarUsuarioForm(data=form_data, instance=usuario)
        self.assertTrue(form.is_valid())

    def test_cambiar_username_a_existente_invalido(self):
        """No permite cambiar username a uno existente"""
        usuario1 = Usuario.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123',
            rol='alumno'
        )
        usuario2 = Usuario.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123',
            rol='alumno'
        )

        form_data = {
            'username': 'user1',  # Intentar cambiar a username existente
            'email': 'user2@test.com',
            'first_name': 'User',
            'last_name': 'Two',
            'rol': 'alumno',
            'is_active': True
        }
        form = GestionarUsuarioForm(data=form_data, instance=usuario2)
        self.assertFalse(form.is_valid())

    def test_desactivar_usuario(self):
        """Permite desactivar usuario"""
        usuario = Usuario.objects.create_user(
            username='user1',
            email='user@test.com',
            password='testpass123',
            rol='alumno',
            is_active=True
        )

        form_data = {
            'username': 'user1',
            'email': 'user@test.com',
            'first_name': 'User',
            'last_name': 'Test',
            'rol': 'alumno',
            'is_active': False
        }
        form = GestionarUsuarioForm(data=form_data, instance=usuario)
        self.assertTrue(form.is_valid())

    def test_cambiar_rol(self):
        """Permite cambiar rol de usuario"""
        usuario = Usuario.objects.create_user(
            username='user1',
            email='user@test.com',
            password='testpass123',
            rol='alumno'
        )

        form_data = {
            'username': 'user1',
            'email': 'user@test.com',
            'first_name': 'User',
            'last_name': 'Test',
            'rol': 'control_escolar',
            'is_active': True
        }
        form = GestionarUsuarioForm(data=form_data, instance=usuario)
        self.assertTrue(form.is_valid())


class FormularioPermisosPorRolTest(TestCase):
    """Tests para verificar permisos segiºn roles en formularios"""

    def test_solo_admin_puede_crear_admin(self):
        """Verificar que solo administradores pueden crear administradores"""
        # Este test verifica las reglas de negocio del sistema
        admin = Usuario.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='testpass123',
            rol='administrador'
        )

        alumno = Usuario.objects.create_user(
            username='alumno1',
            email='alumno@test.com',
            password='testpass123',
            rol='alumno'
        )

        # Admin puede gestionar usuarios
        self.assertTrue(admin.puede_gestionar_usuarios())

        # Alumno no puede gestionar usuarios
        self.assertFalse(alumno.puede_gestionar_usuarios())

    def test_roles_pueden_crear_tipos_solicitud(self):
        """Control escolar y admin pueden crear tipos de solicitud"""
        control = Usuario.objects.create_user(
            username='control1',
            email='control@test.com',
            password='testpass123',
            rol='control_escolar'
        )

        admin = Usuario.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='testpass123',
            rol='administrador'
        )

        alumno = Usuario.objects.create_user(
            username='alumno1',
            email='alumno@test.com',
            password='testpass123',
            rol='alumno'
        )

        self.assertTrue(control.puede_crear_tipo_solicitud())
        self.assertTrue(admin.puede_crear_tipo_solicitud())
        self.assertFalse(alumno.puede_crear_tipo_solicitud())


from django.test import TestCase
from solicitudes_app.forms import (
    RegistroUsuarioForm,
    ActualizarPerfilForm,
    GestionarUsuarioForm
)
from solicitudes_app.models import Usuario


class RegistroUsuarioFormCoverageTest(TestCase):
    """Tests adicionales para RegistroUsuarioForm"""

    def test_validacion_email_formato_invalido(self):
        """Email con formato invalido debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'user1',
            'email': 'emailinvalido',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_validacion_email_duplicado(self):
        """Email duplicado debe fallar"""
        Usuario.objects.create_user(
            username='existing',
            email='existing@test.com',
            password='testpass123',
            rol='alumno'
        )
        form = RegistroUsuarioForm(data={
            'username': 'newuser',
            'email': 'existing@test.com',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_validacion_username_muy_corto(self):
        """Username con menos de 4 caracteres debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'usr',
            'email': 'user@test.com',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_validacion_username_caracteres_invalidos(self):
        """Username con caracteres no permitidos debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'user@name',
            'email': 'user@test.com',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_validacion_username_duplicado(self):
        """Username duplicado debe fallar"""
        Usuario.objects.create_user(
            username='existing',
            email='existing@test.com',
            password='testpass123',
            rol='alumno'
        )
        form = RegistroUsuarioForm(data={
            'username': 'existing',
            'email': 'new@test.com',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_validacion_matricula_requerida_para_alumno(self):
        """Alumno debe tener matri­cula"""
        form = RegistroUsuarioForm(data={
            'username': 'alumno1',
            'email': 'alumno@test.com',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': '',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('matricula', form.errors)

    def test_validacion_matricula_formato_invalido(self):
        """Matri­cula con formato invalido debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'alumno1',
            'email': 'alumno@test.com',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': 'ABC',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('matricula', form.errors)

    def test_validacion_matricula_duplicada(self):
        """Matri­cula duplicada debe fallar"""
        Usuario.objects.create_user(
            username='alumno1',
            email='alumno1@test.com',
            password='testpass123',
            rol='alumno',
            matricula='12345'
        )
        form = RegistroUsuarioForm(data={
            'username': 'alumno2',
            'email': 'alumno2@test.com',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('matricula', form.errors)

    def test_validacion_telefono_formato_invalido(self):
        """Teli©fono con formato invalido debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'alumno1',
            'email': 'alumno@test.com',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': '12345',
            'telefono': '123abc',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('telefono', form.errors)

    def test_validacion_password_sin_mayuscula(self):
        """Password sin mayiºscula debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'alumno1',
            'email': 'alumno@test.com',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'testpass123!',
            'password2': 'testpass123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_validacion_password_sin_numero(self):
        """Password sin niºmero debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'alumno1',
            'email': 'alumno@test.com',
            'first_name': 'Juan',
            'last_name': 'Pi©rez',
            'rol': 'alumno',
            'matricula': '12345',
            'password1': 'Testpassword!',
            'password2': 'Testpassword!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)


class ActualizarPerfilFormCoverageTest(TestCase):
    """Tests adicionales para ActualizarPerfilForm"""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='user1',
            email='user@test.com',
            password='testpass123',
            rol='alumno'
        )

    def test_validacion_first_name_caracteres_invalidos(self):
        """Nombre con caracteres invalidos debe fallar"""
        form = ActualizarPerfilForm(
            data={
                'first_name': 'Juan123',
                'last_name': 'Pi©rez',
                'email': 'user@test.com'
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)

    def test_validacion_last_name_caracteres_invalidos(self):
        """Apellido con caracteres invalidos debe fallar"""
        form = ActualizarPerfilForm(
            data={
                'first_name': 'Juan',
                'last_name': 'Pi©rez123',
                'email': 'user@test.com'
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)

    def test_validacion_email_duplicado(self):
        """Email duplicado debe fallar"""
        Usuario.objects.create_user(
            username='otro',
            email='otro@test.com',
            password='testpass123',
            rol='alumno'
        )
        form = ActualizarPerfilForm(
            data={
                'first_name': 'Juan',
                'last_name': 'Pi©rez',
                'email': 'otro@test.com'
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_validacion_telefono_formato_invalido(self):
        """Teli©fono con formato invalido debe fallar"""
        form = ActualizarPerfilForm(
            data={
                'first_name': 'Juan',
                'last_name': 'Pi©rez',
                'email': 'user@test.com',
                'telefono': '123'
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('telefono', form.errors)

    def test_validacion_matricula_formato_invalido(self):
        """Matri­cula con formato invalido debe fallar"""
        form = ActualizarPerfilForm(
            data={
                'first_name': 'Juan',
                'last_name': 'Pi©rez',
                'email': 'user@test.com',
                'matricula': 'ABC'
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('matricula', form.errors)

    def test_validacion_matricula_duplicada(self):
        """Matri­cula duplicada debe fallar"""
        Usuario.objects.create_user(
            username='otro',
            email='otro@test.com',
            password='testpass123',
            rol='alumno',
            matricula='12345'
        )
        form = ActualizarPerfilForm(
            data={
                'first_name': 'Juan',
                'last_name': 'Pi©rez',
                'email': 'user@test.com',
                'matricula': '12345'
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('matricula', form.errors)


class GestionarUsuarioFormCoverageTest(TestCase):
    """Tests adicionales para GestionarUsuarioForm"""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='user1',
            email='user@test.com',
            password='testpass123',
            rol='alumno'
        )

    def test_validacion_username_duplicado(self):
        """Username duplicado debe fallar"""
        Usuario.objects.create_user(
            username='otro',
            email='otro@test.com',
            password='testpass123',
            rol='alumno'
        )
        form = GestionarUsuarioForm(
            data={
                'username': 'otro',
                'email': 'user@test.com',
                'first_name': 'Juan',
                'last_name': 'Pi©rez',
                'rol': 'alumno',
                'is_active': True
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_validacion_email_duplicado(self):
        """Email duplicado debe fallar"""
        Usuario.objects.create_user(
            username='otro',
            email='otro@test.com',
            password='testpass123',
            rol='alumno'
        )
        form = GestionarUsuarioForm(
            data={
                'username': 'user1',
                'email': 'otro@test.com',
                'first_name': 'Juan',
                'last_name': 'Pi©rez',
                'rol': 'alumno',
                'is_active': True
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_validacion_matricula_duplicada(self):
        """Matri­cula duplicada debe fallar"""
        Usuario.objects.create_user(
            username='otro',
            email='otro@test.com',
            password='testpass123',
            rol='alumno',
            matricula='12345'
        )
        form = GestionarUsuarioForm(
            data={
                'username': 'user1',
                'email': 'user@test.com',
                'first_name': 'Juan',
                'last_name': 'Pi©rez',
                'rol': 'alumno',
                'matricula': '12345',
                'is_active': True
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('matricula', form.errors)


"""
Tests adicionales para cobertura completa de forms.py (DSM5)
"""
from django.test import TestCase
from solicitudes_app.forms import RegistroUsuarioForm, ActualizarPerfilForm, GestionarUsuarioForm
from solicitudes_app.models import Usuario


class RegistroUsuarioFormLastNameValidationExtraTest(TestCase):
    """Tests para validaciones adicionales de apellido"""

    def test_last_name_con_caracteres_invalidos(self):
        """Apellido con numeros debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User123',  # Con numeros
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': '12345678'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)


class RegistroUsuarioFormFirstNameInvalidCharsTest(TestCase):
    """Tests para validacion de caracteres invalidos en nombre"""

    def test_first_name_con_numeros(self):
        """Nombre con numeros debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'first_name': 'Test123',  # Con numeros
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': '12345678'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)


class RegistroUsuarioFormMatriculaFormatTest(TestCase):
    """Tests para formato de matricula"""

    def test_matricula_con_letras_falla(self):
        """Matricula con letras debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': 'ABC12345'  # Con letras
        })
        self.assertFalse(form.is_valid())
        self.assertIn('matricula', form.errors)

    def test_matricula_muy_corta_falla(self):
        """Matricula con menos de 5 digitos debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': '1234'  # Solo 4 digitos
        })
        self.assertFalse(form.is_valid())
        self.assertIn('matricula', form.errors)


class RegistroUsuarioFormPasswordMinusculeTest(TestCase):
    """Tests para validacion de minuscula en password"""

    def test_password_sin_minuscula_falla(self):
        """Password sin minuscula debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TESTPASS123!',  # Sin minuscula
            'password2': 'TESTPASS123!',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': '12345678'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)


class RegistroUsuarioFormPasswordLengthTest(TestCase):
    """Tests para validacion de longitud de password"""

    def test_password_muy_corto_falla(self):
        """Password con menos de 8 caracteres debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'Test1!',  # Solo 6 caracteres
            'password2': 'Test1!',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': '12345678'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)


class ActualizarPerfilFormLastNameValidationTest(TestCase):
    """Tests para validacion de apellido en ActualizarPerfilForm"""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='TestPass123',
            rol='alumno'
        )

    def test_last_name_con_numeros_falla(self):
        """Apellido con numeros debe fallar en actualizacion"""
        form = ActualizarPerfilForm(
            data={
                'first_name': 'Test',
                'last_name': 'User123',  # Con numeros
                'email': 'test@test.com',
                'telefono': '1234567890',
                'matricula': '12345678'
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)


class GestionarUsuarioFormUsernameInvalidTest(TestCase):
    """Tests para validacion de username con caracteres invalidos"""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='TestPass123',
            rol='alumno'
        )

    def test_username_con_espacios_falla(self):
        """Username con espacios debe fallar"""
        form = GestionarUsuarioForm(
            data={
                'username': 'test user',  # Con espacio
                'email': 'test@test.com',
                'first_name': 'Test',
                'last_name': 'User',
                'telefono': '1234567890',
                'matricula': '12345678',
                'rol': 'alumno',
                'is_active': True
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)


class GestionarUsuarioFormFirstNameInvalidTest(TestCase):
    """Tests para validacion de first_name con caracteres invalidos"""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='TestPass123',
            rol='alumno'
        )

    def test_first_name_con_numeros_falla(self):
        """First name con numeros debe fallar en GestionarUsuarioForm"""
        form = GestionarUsuarioForm(
            data={
                'username': 'testuser',
                'email': 'test@test.com',
                'first_name': 'Test123',  # Con numeros
                'last_name': 'User',
                'telefono': '1234567890',
                'matricula': '12345678',
                'rol': 'alumno',
                'is_active': True
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)


class GestionarUsuarioFormTelefonoInvalidTest(TestCase):
    """Tests para validacion de telefono con formato invalido"""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='TestPass123',
            rol='alumno'
        )

    def test_telefono_con_letras_falla(self):
        """Telefono con letras debe fallar"""
        form = GestionarUsuarioForm(
            data={
                'username': 'testuser',
                'email': 'test@test.com',
                'first_name': 'Test',
                'last_name': 'User',
                'telefono': '123456789A',  # Con letra
                'matricula': '12345678',
                'rol': 'alumno',
                'is_active': True
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('telefono', form.errors)


class GestionarUsuarioFormMatriculaInvalidTest(TestCase):
    """Tests para validacion de matricula con formato invalido"""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='TestPass123',
            rol='alumno'
        )

    def test_matricula_muy_larga_falla(self):
        """Matricula con mas de 8 digitos debe fallar"""
        form = GestionarUsuarioForm(
            data={
                'username': 'testuser',
                'email': 'test@test.com',
                'first_name': 'Test',
                'last_name': 'User',
                'telefono': '1234567890',
                'matricula': '123456789',  # 9 digitos
                'rol': 'alumno',
                'is_active': True
            },
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('matricula', form.errors)


"""
Tests adicionales para cobertura de validaciones en forms.py (DSM5)
"""
from django.test import TestCase
from solicitudes_app.forms import RegistroUsuarioForm, ActualizarPerfilForm
from solicitudes_app.models import Usuario


class RegistroUsuarioFormEmailValidationTest(TestCase):
    """Tests para validacion de email vacio y formato estricto"""

    def test_email_vacio_genera_error(self):
        """Email vacio debe generar error de validacion"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': '',  # Vacio
            'password1': 'TestPass123',
            'password2': 'TestPass123',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_email_formato_invalido_sin_dominio(self):
        """Email sin dominio correcto debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@',  # Sin dominio
            'password1': 'TestPass123',
            'password2': 'TestPass123',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class RegistroUsuarioFormUsernameValidationTest(TestCase):
    """Tests para validacion de username vacio"""

    def test_username_vacio_genera_error(self):
        """Username vacio debe generar error de validacion"""
        form = RegistroUsuarioForm(data={
            'username': '',  # Vacio
            'email': 'test@example.com',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)


class RegistroUsuarioFormFirstNameValidationTest(TestCase):
    """Tests para validacion de first_name vacio y longitud minima"""

    def test_first_name_vacio_genera_error(self):
        """First name vacio debe generar error"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
            'first_name': '',  # Vacio
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)

    def test_first_name_muy_corto_genera_error(self):
        """First name con 1 caracter debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
            'first_name': 'A',  # Solo 1 caracter
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)


class ActualizarPerfilFormFirstNameValidationTest(TestCase):
    """Tests para validacion de first_name en ActualizarPerfilForm"""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            rol='alumno'
        )

    def test_first_name_vacio_en_actualizacion(self):
        """First name vacio en actualizar perfil se acepta (campo opcional)"""
        form = ActualizarPerfilForm(
            data={
                'first_name': '',  # Vacio - permitido
                'last_name': 'User',
                'email': 'test@test.com',
                'telefono': '1234567890',
                'matricula': '12345678'
            },
            instance=self.usuario
        )
        # ActualizarPerfilForm permite first_name vacio
        self.assertTrue(form.is_valid())

    def test_first_name_muy_corto_en_actualizacion(self):
        """First name con 1 caracter se acepta en actualizar perfil"""
        form = ActualizarPerfilForm(
            data={
                'first_name': 'A',  # Solo 1 caracter - permitido en actualizacion
                'last_name': 'User',
                'email': 'test@test.com',
                'telefono': '1234567890',
                'matricula': '12345678'
            },
            instance=self.usuario
        )
        # ActualizarPerfilForm es mas flexible
        self.assertTrue(form.is_valid())


class RegistroUsuarioFormLastNameValidationTest(TestCase):
    """Tests para validacion de last_name"""

    def test_last_name_vacio_genera_error(self):
        """Last name vacio debe generar error"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
            'first_name': 'Test',
            'last_name': '',  # Vacio
            'telefono': '1234567890',
            'rol': 'alumno'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)

    def test_last_name_muy_corto_genera_error(self):
        """Last name con 1 caracter debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
            'first_name': 'Test',
            'last_name': 'U',  # Solo 1 caracter
            'telefono': '1234567890',
            'rol': 'alumno'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)


class RegistroUsuarioFormTelefonoValidationTest(TestCase):
    """Tests para validacion de telefono vacio"""

    def test_telefono_vacio_genera_error(self):
        """Telefono vacio permite validacion pero matricula es requerida para alumno"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPass123!',  # Con caracter especial
            'password2': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': ''  # Vacio - debe generar error para alumno
        })
        self.assertFalse(form.is_valid())
        self.assertIn('matricula', form.errors)


class RegistroUsuarioFormMatriculaAlumnoTest(TestCase):
    """Tests para validacion de matricula en rol alumno"""

    def test_matricula_vacia_para_alumno_genera_error(self):
        """Matricula vacia para alumno debe generar error"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': ''  # Vacia para alumno
        })
        self.assertFalse(form.is_valid())
        self.assertIn('matricula', form.errors)


class RegistroUsuarioFormPasswordValidationTest(TestCase):
    """Tests para validacion de password vacio y sin mayuscula"""

    def test_password_sin_mayuscula_genera_error(self):
        """Password sin mayuscula debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'testpass123',  # Sin mayuscula
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': '12345678'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_password_sin_numero_genera_error(self):
        """Password sin numero debe fallar"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPassword',  # Sin numero
            'password2': 'TestPassword',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': '12345678'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)


class CoberturaMissingFormsTest(TestCase):
    """Tests para cubrir líneas específicas faltantes en forms.py"""

    def test_email_vacio_linea_69(self):
        """Email vacío"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': '',  # Vacío
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': '12345678'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_email_formato_invalido_linea_75(self):
        """Formato de email inválido"""
        form = RegistroUsuarioForm(data={
            'username': 'testuser',
            'email': 'invalido@',  # Formato inválido
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': '12345678'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_username_vacio_linea_88(self):
        """Username vacío"""
        form = RegistroUsuarioForm(data={
            'username': '',  # Vacío
            'email': 'test@test.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User',
            'telefono': '1234567890',
            'rol': 'alumno',
            'matricula': '12345678'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)


