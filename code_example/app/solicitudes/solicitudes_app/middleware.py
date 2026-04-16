from django.shortcuts import redirect
from django.urls import reverse


class CompletarPerfilMiddleware:
    """
    Middleware que redirige a los usuarios que deben cambiar su contraseña
    o completar su perfil
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # URLs que no requieren redirección
        # (permitir acceso sin perfil completo)
        self.urls_permitidas = [
            '/auth/logout/',
            '/auth/perfil/',
            '/auth/cambiar-password/',
            '/admin/',
            '/static/',
            '/media/',
        ]

    def _es_url_permitida(self, ruta):
        """Verifica si la ruta actual está en URLs permitidas"""
        return any(ruta.startswith(url) for url in self.urls_permitidas)

    def _obtener_url_destino(self, user):
        """Obtiene URL de destino según estado del usuario"""
        if user.debe_cambiar_password:
            return reverse('solicitudes_app:cambiar_password')
        if not user.perfil_completo:
            return reverse('solicitudes_app:perfil')
        return None

    def _obtener_redireccion_necesaria(self, user, ruta_actual):
        """Determina si el usuario necesita ser redirigido"""
        if self._es_url_permitida(ruta_actual):
            return None

        url_destino = self._obtener_url_destino(user)
        if url_destino and ruta_actual != url_destino:
            return url_destino

        return None

    def __call__(self, request):
        if request.user.is_authenticated:
            url_redireccion = self._obtener_redireccion_necesaria(
                request.user, request.path)
            if url_redireccion:
                return redirect(url_redireccion)

        response = self.get_response(request)
        return response
