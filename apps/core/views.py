# apps/core/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import Role, Permission
from .forms import RoleForm, RolePermissionForm
from .utils.permissions import permission_required, get_permission_matrix
import json
from django.http import JsonResponse
from django.db import transaction


def dashboard(request):
    """Vue principale du tableau de bord"""
    context = {
        'title': 'Tableau de bord',
        'user': request.user,
    }
    return render(request, 'dashboard/dashboard.html', context)

def home(request):
    """Page d'accueil qui redirige vers le dashboard"""
    return dashboard(request) 


@permission_required('administration', 'read')
def roles_list(request):
    """Vue liste des rôles avec filtres et recherche"""
    
    # Récupération des paramètres de recherche et filtrage
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Construction de la requête
    roles = Role.objects.annotate(
        users_count=Count('collaborateur')
    ).order_by('name')
    
    # Filtrage par recherche
    if search:
        roles = roles.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Filtrage par statut
    if status_filter:
        if status_filter == 'active':
            roles = roles.filter(is_active=True)
        elif status_filter == 'inactive':
            roles = roles.filter(is_active=False)
        elif status_filter == 'system':
            roles = roles.filter(is_system_role=True)
    
    # Pagination
    paginator = Paginator(roles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'total_roles': roles.count(),
    }
    
    return render(request, 'core/roles/list.html', context)


@permission_required('administration', 'create')
def role_create(request):
    """Vue création d'un nouveau rôle"""
    
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()
            messages.success(request, f'Rôle "{role.name}" créé avec succès.')
            return redirect('core:role_permissions', role_id=role.id)
    else:
        form = RoleForm()
    
    context = {
        'form': form,
        'action': 'Créer',
        'submit_text': 'Créer le rôle'
    }
    
    return render(request, 'core/roles/form.html', context)


@permission_required('administration', 'read')
def role_detail(request, role_id):
    """Vue détail d'un rôle"""
    
    role = get_object_or_404(Role, id=role_id)
    
    # Statistiques du rôle
    users_count = role.collaborateur_set.count()
    permissions_count = role.permissions.count()
    permissions_by_module = role.get_permissions_by_module()
    
    context = {
        'role': role,
        'users_count': users_count,
        'permissions_count': permissions_count,
        'permissions_by_module': permissions_by_module,
    }
    
    return render(request, 'core/roles/detail.html', context)


@permission_required('administration', 'update')
def role_edit(request, role_id):
    """Vue modification d'un rôle"""
    
    role = get_object_or_404(Role, id=role_id)
    
    # Protection des rôles système
    if role.is_system_role and not request.user.is_superuser:
        messages.error(request, 'Vous ne pouvez pas modifier un rôle système.')
        return redirect('core:role_detail', role_id=role.id)
    
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, f'Rôle "{role.name}" modifié avec succès.')
            return redirect('core:role_detail', role_id=role.id)
    else:
        form = RoleForm(instance=role)
    
    context = {
        'form': form,
        'role': role,
        'action': 'Modifier',
        'submit_text': 'Sauvegarder les modifications'
    }
    
    return render(request, 'core/roles/form.html', context)


@permission_required('administration', 'update')
def role_toggle_status(request, role_id):
    """Activer/Désactiver un rôle"""
    
    role = get_object_or_404(Role, id=role_id)
    
    if role.is_system_role and not request.user.is_superuser:
        messages.error(request, 'Vous ne pouvez pas modifier le statut d\'un rôle système.')
        return redirect('core:roles_list')
    
    role.is_active = not role.is_active
    role.save()
    
    status = "activé" if role.is_active else "désactivé"
    messages.success(request, f'Rôle "{role.name}" {status} avec succès.')
    
    return redirect('core:roles_list')


@permission_required('administration', 'create')
def role_duplicate(request, role_id):
    """Dupliquer un rôle existant"""
    
    original_role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            # Créer le nouveau rôle
            new_role = form.save(commit=False)
            new_role.is_system_role = False  # Les duplications ne sont jamais des rôles système
            new_role.save()
            
            # Copier les permissions
            new_role.permissions.set(original_role.permissions.all())
            
            messages.success(request, f'Rôle "{new_role.name}" créé par duplication avec succès.')
            return redirect('core:role_permissions', role_id=new_role.id)
    else:
        # Pré-remplir le formulaire avec les données du rôle original
        form = RoleForm(initial={
            'name': f"{original_role.name} - Copie",
            'description': original_role.description,
            'is_active': True
        })
    
    context = {
        'form': form,
        'original_role': original_role,
        'action': 'Dupliquer',
        'submit_text': 'Créer la copie'
    }
    
    return render(request, 'core/roles/duplicate.html', context)
@permission_required('administration', 'update')
def role_permissions(request, role_id):
    """Interface de gestion des permissions d'un rôle (matrice interactive)"""
    
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Récupérer les permissions sélectionnées
                selected_permissions = request.POST.getlist('permissions')
                permission_ids = [int(id) for id in selected_permissions if id.isdigit()]
                
                # Assigner les nouvelles permissions
                permissions = Permission.objects.filter(id__in=permission_ids)
                role.permissions.set(permissions)
                
                messages.success(request, f'Permissions du rôle "{role.name}" mises à jour avec succès.')
                return redirect('core:role_detail', role_id=role.id)
                
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour : {str(e)}')
    
    # Préparer la matrice des permissions
    permission_matrix = get_permission_matrix()
    current_permissions = set(role.permissions.values_list('id', flat=True))
    
    context = {
        'role': role,
        'permission_matrix': permission_matrix,
        'current_permissions': current_permissions,
    }
    
    return render(request, 'core/roles/permissions.html', context)


@permission_required('administration', 'read')
def role_users(request, role_id):
    """Gestion des utilisateurs assignés à un rôle"""
    
    role = get_object_or_404(Role, id=role_id)
    
    # Utilisateurs actuels avec ce rôle
    current_users = role.collaborateur_set.all().order_by('nom_collaborateur', 'prenom_collaborateur')
    
    # Utilisateurs disponibles (sans rôle ou avec un autre rôle)
    from apps.collaborateurs.models import Collaborateur
    available_users = Collaborateur.objects.exclude(user_role=role).order_by('nom_collaborateur', 'prenom_collaborateur')
    
    context = {
        'role': role,
        'current_users': current_users,
        'available_users': available_users,
    }
    
    return render(request, 'core/roles/users.html', context)


@permission_required('administration', 'update')
def assign_role_to_user(request):
    """AJAX : Assigner un rôle à un utilisateur"""
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role_id = request.POST.get('role_id')
        
        try:
            from apps.collaborateurs.models import Collaborateur
            user = get_object_or_404(Collaborateur, id=user_id)
            role = get_object_or_404(Role, id=role_id)
            
            old_role = user.user_role
            user.user_role = role
            user.save()
            
            # Enregistrer l'historique si nécessaire
            if hasattr(user, 'rolehistory_set'):
                from .models import RoleHistory
                RoleHistory.objects.create(
                    collaborateur=user,
                    old_role=old_role,
                    new_role=role,
                    change_reason="Assignation via interface admin"
                )
            
            return JsonResponse({
                'success': True,
                'message': f'Rôle "{role.name}" assigné à {user.prenom_collaborateur} {user.nom_collaborateur}'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur : {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


@permission_required('administration', 'create')
def role_templates(request):
    """Templates de rôles prédéfinis"""
    
    templates = {
        'manager': {
            'name': 'Manager Général',
            'description': 'Accès étendu pour la gestion opérationnelle',
            'modules': ['affaires', 'lancements', 'collaborateurs', 'rapports']
        },
        'supervisor': {
            'name': 'Superviseur',
            'description': 'Supervision d\'équipe et suivi des activités',
            'modules': ['lancements', 'collaborateurs', 'rapports']
        },
        'operator': {
            'name': 'Opérateur Standard',
            'description': 'Accès limité aux opérations courantes',
            'modules': ['lancements']
        },
        'viewer': {
            'name': 'Consultation Seule',
            'description': 'Accès en lecture uniquement',
            'modules': []
        }
    }
    
    if request.method == 'POST':
        template_key = request.POST.get('template')
        custom_name = request.POST.get('custom_name', '')
        
        if template_key in templates:
            template = templates[template_key]
            
            # Créer le rôle basé sur le template
            role_name = custom_name if custom_name else template['name']
            
            try:
                role = Role.objects.create(
                    name=role_name,
                    description=template['description'],
                    is_active=True
                )
                
                # Assigner les permissions selon le template
                permissions_to_assign = []
                for module in template['modules']:
                    # Actions par défaut selon le type de template
                    if template_key == 'manager':
                        actions = ['create', 'read', 'update', 'assign']
                    elif template_key == 'supervisor':
                        actions = ['read', 'update']
                    elif template_key == 'operator':
                        actions = ['create', 'read', 'update']
                    else:  # viewer
                        actions = ['read']
                    
                    for action in actions:
                        try:
                            perm = Permission.objects.get(module=module, action=action)
                            permissions_to_assign.append(perm)
                        except Permission.DoesNotExist:
                            pass
                
                role.permissions.set(permissions_to_assign)
                
                messages.success(request, f'Rôle "{role.name}" créé à partir du template avec succès.')
                return redirect('core:role_permissions', role_id=role.id)
                
            except Exception as e:
                messages.error(request, f'Erreur lors de la création : {str(e)}')
    
    context = {
        'templates': templates
    }
    
    return render(request, 'core/roles/templates.html', context)


@permission_required('administration', 'export')
def export_role_config(request, role_id):
    """Exporter la configuration d'un rôle"""
    
    role = get_object_or_404(Role, id=role_id)
    
    # Préparer les données d'export
    config = {
        'name': role.name,
        'description': role.description,
        'is_active': role.is_active,
        'permissions': []
    }
    
    for permission in role.permissions.all():
        config['permissions'].append({
            'module': permission.module,
            'action': permission.action,
            'name': permission.name
        })
    
    # Retourner en JSON
    response = JsonResponse(config, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="role_{role.name.lower().replace(" ", "_")}.json"'
    
    return response


@permission_required('administration', 'create')
def import_role_config(request):
    """Importer une configuration de rôle"""
    
    if request.method == 'POST' and request.FILES.get('config_file'):
        try:
            config_file = request.FILES['config_file']
            config_data = json.load(config_file)
            
            # Créer le rôle
            role = Role.objects.create(
                name=config_data['name'],
                description=config_data.get('description', ''),
                is_active=config_data.get('is_active', True)
            )
            
            # Assigner les permissions
            permissions_to_assign = []
            for perm_data in config_data.get('permissions', []):
                try:
                    permission = Permission.objects.get(
                        module=perm_data['module'],
                        action=perm_data['action']
                    )
                    permissions_to_assign.append(permission)
                except Permission.DoesNotExist:
                    pass
            
            role.permissions.set(permissions_to_assign)
            
            messages.success(request, f'Rôle "{role.name}" importé avec succès.')
            return redirect('core:role_detail', role_id=role.id)
            
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'import : {str(e)}')
    
    return render(request, 'core/roles/import.html')
