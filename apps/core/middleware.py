from django.shortcuts import redirect
from django.urls import resolve
from django.contrib import messages

class PermissionMiddleware:
    """Middleware pour vérifier les permissions automatiquement"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs qui nécessitent des permissions spécifiques
        self.protected_urls = {
            'collaborateurs:list': ('collaborateurs', 'read'),
            'collaborateurs:create': ('collaborateurs', 'create'),
            'collaborateurs:edit': ('collaborateurs', 'update'),
            'collaborateurs:delete': ('collaborateurs', 'delete'),
            'ateliers:list': ('ateliers', 'read'),
            'ateliers:create': ('ateliers', 'create'),
            
            # Ajoutez d'autres URLs selon vos besoins
        }

    def __call__(self, request):
        # Vérifier les permissions avant la vue
        if request.user.is_authenticated:
            resolved = resolve(request.path_info)
            url_name = f"{resolved.namespace}:{resolved.url_name}" if resolved.namespace else resolved.url_name
            
            if url_name in self.protected_urls:
                module, action = self.protected_urls[url_name]
                if not request.user.has_permission(module, action):
                    messages.error(request, "Vous n'avez pas les permissions nécessaires.")
                    return redirect('dashboard')
        
        response = self.get_response(request)
        return response
    