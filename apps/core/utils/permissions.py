from apps.core.models import Permission, Role
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def create_default_permissions():
    """Crée toutes les permissions par défaut"""
    
    modules = [
        'collaborateurs', 'ateliers', 'categories', 
        'affaires', 'lancements', 'rapports', 'administration'
    ]
    
    actions = ['create', 'read', 'update', 'delete', 'assign', 'export']
    
    permissions_created = []
    
    for module in modules:
        for action in actions:
            # Éviter les combinaisons qui n'ont pas de sens
            if not _is_valid_permission(module, action):
                continue
                
            permission, created = Permission.objects.get_or_create(
                module=module,
                action=action,
                defaults={
                    'name': f"{module}_{action}",
                    'description': f"Permission de {action} pour le module {module}"
                }
            )
            
            if created:
                permissions_created.append(permission)
    
    return permissions_created


def _is_valid_permission(module, action):
    """Vérifie si une combinaison module/action est valide"""
    
    # Règles métier pour éviter des permissions inutiles
    invalid_combinations = [
        ('administration', 'assign'),  # Pas d'assignation en administration
        ('rapports', 'assign'),        # Pas d'assignation pour les rapports
        ('rapports', 'delete'),        # Pas de suppression des rapports
    ]
    
    return (module, action) not in invalid_combinations


def create_default_roles():
    """Crée les rôles par défaut du système"""
    
    roles_config = {
        'Super Administrateur': {
            'description': 'Accès complet à toutes les fonctionnalités',
            'permissions': 'all',
            'is_system_role': True
        },
        'Responsable Affaire': {
            'description': 'Gestion des affaires et consultation des lancements',
            'permissions': [
                ('affaires', ['create', 'read', 'update', 'assign']),
                ('lancements', ['read', 'update']),
                ('collaborateurs', ['read']),
                ('rapports', ['read', 'export']),
            ]
        },
        'Responsable Atelier': {
            'description': 'Gestion de son atelier et des collaborateurs assignés',
            'permissions': [
                ('ateliers', ['read', 'update']),
                ('collaborateurs', ['read', 'assign']),
                ('lancements', ['create', 'read', 'update']),
                ('categories', ['read']),
                ('rapports', ['read', 'export']),
            ]
        },
        'Collaborateur': {
            'description': 'Consultation limitée et modification de ses propres données',
            'permissions': [
                ('collaborateurs', ['read']),  # Ses propres données seulement
                ('lancements', ['read']),      # Ses lancements seulement
                ('ateliers', ['read']),        # Lecture seule
                ('categories', ['read']),      # Lecture seule
            ]
        },
        'Opérateur': {
            'description': 'Saisie des lancements et consultation restreinte',
            'permissions': [
                ('lancements', ['create', 'read', 'update']),
                ('collaborateurs', ['read']),
                ('ateliers', ['read']),
                ('categories', ['read']),
                ('affaires', ['read']),
            ]
        }
    }
    
    created_roles = []
    
    for role_name, config in roles_config.items():
        role, created = Role.objects.get_or_create(
            name=role_name,
            defaults={
                'description': config['description'],
                'is_system_role': config.get('is_system_role', False)
            }
        )
        
        if created or not role.permissions.exists():
            # Assigner les permissions
            if config['permissions'] == 'all':
                # Toutes les permissions pour le super admin
                role.permissions.set(Permission.objects.all())
            else:
                # Permissions spécifiques
                permissions_to_assign = []
                for module, actions in config['permissions']:
                    for action in actions:
                        try:
                            perm = Permission.objects.get(module=module, action=action)
                            permissions_to_assign.append(perm)
                        except Permission.DoesNotExist:
                            pass
                
                role.permissions.set(permissions_to_assign)
        
        if created:
            created_roles.append(role)
    
    return created_roles


def get_permission_matrix():
    """Retourne la matrice des permissions pour l'interface admin"""
    
    # Vous devrez adapter ceci selon vos modèles
    # En supposant que vous avez des choices dans votre modèle Permission
    modules = [
        ('collaborateurs', 'Collaborateurs'),
        ('ateliers', 'Ateliers'),
        ('categories', 'Catégories'),
        ('affaires', 'Affaires'),
        ('lancements', 'Lancements'),
        ('rapports', 'Rapports'),
        ('administration', 'Administration'),
    ]
    
    actions = [
        ('create', 'Créer'),
        ('read', 'Lire'),
        ('update', 'Modifier'),
        ('delete', 'Supprimer'),
        ('assign', 'Assigner'),
        ('export', 'Exporter'),
    ]
    
    matrix = {}
    
    for module_code, module_name in modules:
        matrix[module_code] = {
            'name': module_name,
            'actions': {}
        }
        
        for action_code, action_name in actions:
            try:
                permission = Permission.objects.get(module=module_code, action=action_code)
                matrix[module_code]['actions'][action_code] = {
                    'name': action_name,
                    'permission_id': permission.id,
                    'exists': True
                }
            except Permission.DoesNotExist:
                matrix[module_code]['actions'][action_code] = {
                    'name': action_name,
                    'permission_id': None,
                    'exists': False
                }
    
    return matrix


def permission_required(module, action, ajax_support=True):
    """Décorateur pour vérifier les permissions"""
    
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.has_permission(module, action):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and ajax_support:
                    return JsonResponse({
                        'error': True,
                        'message': 'Permissions insuffisantes'
                    }, status=403)
                
                messages.error(request, "Vous n'avez pas les permissions nécessaires pour cette action.")
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    return decorator