from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import (
    login, logout, authenticate, update_session_auth_hash
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .models import Usuario
from .forms import (
    RegistroUsuarioForm, LoginForm, ActualizarPerfilForm,
    GestionarUsuarioForm
)


def _verificar_admin_predeterminado():
    """Verifica si existe admin predeterminado que debe cambiar contraseña"""
    try:
        admin_user = Usuario.objects.get(username='admin', rol='administrador')
        return admin_user.debe_cambiar_password
    except Usuario.DoesNotExist:
        return False


def _procesar_login_exitoso(request, user, remember_me):
    """Procesa el login exitoso configurando sesión y redirigiendo"""
    login(request, user)

    if not remember_me:
        request.session.set_expiry(0)

    messages.success(request, f'¡Bienvenido {user.get_full_name()}!')

    next_url = request.GET.get('next')
    return redirect(next_url) if next_url else redirect('bienvenida')


def _procesar_form_invalido(form):
    """Procesa errores de formulario de login"""
    if form.errors.get('__all__'):
        return 'Usuario o contraseña incorrectos.'
    return 'Por favor, corrige los errores en el formulario.'


def login_view(request):
    """Vista para login de usuarios"""
    if request.user.is_authenticated:
        return redirect('bienvenida')

    mostrar_credenciales_admin = _verificar_admin_predeterminado()

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')

            user = authenticate(username=username, password=password)
            if user is not None:
                return _procesar_login_exitoso(request, user, remember_me)
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            messages.error(request, _procesar_form_invalido(form))
    else:
        form = LoginForm()

    return render(request, 'solicitudes_app/login.html', {
        'form': form,
        'mostrar_credenciales_admin': mostrar_credenciales_admin
    })


def registro_view(request):
    """Vista para registro de nuevos usuarios"""
    if request.user.is_authenticated:
        return redirect('bienvenida')

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request, '¡Cuenta creada exitosamente! Bienvenido.')
            return redirect('bienvenida')
        else:
            messages.error(
                request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = RegistroUsuarioForm()

    return render(request, 'solicitudes_app/registro.html', {'form': form})


@login_required
def logout_view(request):
    """Vista para cerrar sesión"""
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('solicitudes_app:login')


@login_required
def perfil_view(request):
    """Vista para ver y editar el perfil del usuario"""
    if request.method == 'POST':
        form = ActualizarPerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            # Marcar perfil como completo
            user.perfil_completo = True
            user.save()
            messages.success(request, 'Perfil actualizado exitosamente.')
            return redirect('bienvenida')
        else:
            messages.error(
                request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = ActualizarPerfilForm(instance=request.user)

    return render(request, 'solicitudes_app/perfil.html', {
        'form': form,
        'usuario': request.user
    })


@login_required
def lista_usuarios_view(request):
    """Vista para listar usuarios (solo administradores)"""
    if not request.user.puede_gestionar_usuarios():
        messages.error(
            request, 'No tienes permiso para acceder a esta página.')
        return redirect('bienvenida')

    usuarios = Usuario.objects.all().order_by('-date_joined')
    return render(request, 'solicitudes_app/lista_usuarios.html', {
        'usuarios': usuarios
    })


def _validar_edicion_propio_usuario(usuario, request_user, form_data):
    """Valida que el admin no se quite su propio rol o desactive su cuenta"""
    if usuario.id != request_user.id:
        return None

    if form_data.get('rol') != 'administrador':
        return 'No puedes quitarte tu propio rol de administrador.'

    if not form_data.get('is_active', True):
        return 'No puedes desactivar tu propia cuenta.'

    return None


def _hay_cambio_critico_admin(form_data):
    """Verifica si hay cambios que afectarían el rol o estado de admin"""
    nuevo_rol = form_data.get('rol')
    nuevo_estado = form_data.get('is_active', True)
    return nuevo_rol != 'administrador' or not nuevo_estado


def _validar_ultimo_admin(usuario, form_data):
    """Valida que no se elimine o desactive el último admin del sistema"""
    if usuario.rol != 'administrador' or not usuario.is_active:
        return None

    admins_activos = Usuario.objects.filter(
        rol='administrador', is_active=True).count()

    if admins_activos <= 1 and _hay_cambio_critico_admin(form_data):
        return (
            'No se puede modificar este usuario porque es el último '
            'administrador activo del sistema. '
            'Crea otro administrador primero.'
        )

    return None


@login_required
def editar_usuario_view(request, usuario_id):
    """Vista para editar un usuario (solo administradores)"""
    if not request.user.puede_gestionar_usuarios():
        messages.error(
            request, 'No tienes permiso para acceder a esta página.')
        return redirect('bienvenida')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        form = GestionarUsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            # Validar edición de propio usuario
            error = _validar_edicion_propio_usuario(
                usuario, request.user, form.cleaned_data)
            if error:
                messages.error(request, error)
                return render(request, 'solicitudes_app/editar_usuario.html', {
                    'form': form,
                    'usuario': usuario
                })

            # Validar último admin
            error = _validar_ultimo_admin(usuario, form.cleaned_data)
            if error:
                messages.error(request, error)
                return render(request, 'solicitudes_app/editar_usuario.html', {
                    'form': form,
                    'usuario': usuario
                })

            form.save()
            messages.success(
                request,
                f'Usuario {form.instance.get_full_name()} actualizado '
                f'exitosamente.')
            return redirect('solicitudes_app:lista_usuarios')
        else:
            messages.error(
                request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = GestionarUsuarioForm(instance=usuario)

    return render(request, 'solicitudes_app/editar_usuario.html', {
        'form': form,
        'usuario': usuario
    })


def _validar_eliminacion_ultimo_admin(usuario):
    """Valida si no se puede eliminar el usuario sin admins"""
    if usuario.rol == 'administrador' and usuario.is_active:
        admins_activos = Usuario.objects.filter(
            rol='administrador', is_active=True).count()
        return admins_activos <= 1
    return False


@login_required
@require_http_methods(["POST"])
def eliminar_usuario_view(request, usuario_id):
    """Vista para eliminar un usuario (solo administradores)"""
    if not request.user.puede_gestionar_usuarios():
        messages.error(
            request, 'No tienes permiso para realizar esta acción.')
        return redirect('bienvenida')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if usuario.id == request.user.id:
        messages.error(request, 'No puedes eliminar tu propia cuenta.')
        return redirect('solicitudes_app:lista_usuarios')

    if _validar_eliminacion_ultimo_admin(usuario):
        messages.error(
            request,
            'No se puede eliminar el último administrador activo del '
            'sistema. Crea otro administrador primero.')
        return redirect('solicitudes_app:lista_usuarios')

    username = usuario.username
    usuario.delete()
    messages.success(request, f'Usuario {username} eliminado exitosamente.')
    return redirect('solicitudes_app:lista_usuarios')


@login_required
def cambiar_password_view(request):
    """Vista para cambiar la contraseña (obligatorio para usuarios)"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Mantener la sesión activa
            update_session_auth_hash(request, user)

            # Marcar que ya cambió la contraseña
            user.debe_cambiar_password = False
            user.save()

            messages.success(request, '¡Contraseña cambiada exitosamente!')

            # Si aún no tiene perfil completo, redirigir a perfil
            if not user.perfil_completo:
                messages.info(
                    request,
                    'Ahora completa tu perfil con tus datos personales.')
                return redirect('solicitudes_app:perfil')

            return redirect('bienvenida')
        else:
            messages.error(
                request,
                'Por favor, corrige los errores en el formulario.')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'solicitudes_app/cambiar_password.html', {
        'form': form,
        'obligatorio': request.user.debe_cambiar_password
    })
