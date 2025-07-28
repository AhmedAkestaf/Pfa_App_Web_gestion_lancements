def user_permissions(request):
    """Ajoute les permissions de l'utilisateur au contexte de tous les templates"""
    if request.user.is_authenticated:
        permissions = {}
        for perm in request.user.get_all_permissions():
            if perm.module not in permissions:
                permissions[perm.module] = []
            permissions[perm.module].append(perm.action)
        
        return {
            'user_permissions': permissions,
            'user_role': request.user.user_role,
        }
    return {}