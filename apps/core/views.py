# apps/core/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import Role, Permission , Affaire
from apps.collaborateurs.models import Collaborateur
from .forms import RoleForm, AffaireForm
from .utils.permissions import permission_required, get_permission_matrix
import json
from django.http import JsonResponse
from django.db import transaction , models


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
    
    # Pour les administrateurs : tous les utilisateurs et tous les rôles
    all_users = None
    all_roles = None
    
    if hasattr(request.user, 'collaborateur') and request.user.collaborateur.user_role and request.user.collaborateur.user_role.name == 'Admin':
        all_users = Collaborateur.objects.all().order_by('nom_collaborateur', 'prenom_collaborateur')
        all_roles = Role.objects.filter(is_active=True).order_by('name')
    
    context = {
        'role': role,
        'current_users': current_users,
        'available_users': available_users,
        'all_users': all_users,
        'all_roles': all_roles,
    }
    
    return render(request, 'core/roles/users.html', context)


@permission_required('administration', 'update')
def assign_role_to_user(request):
    """AJAX : Assigner un rôle à un utilisateur"""
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role_id = request.POST.get('role_id')
        
        try:
            from apps.collaborateurs.models import Collaborateur, RoleHistory
            user = get_object_or_404(Collaborateur, id=user_id)
            role = get_object_or_404(Role, id=role_id) if role_id else None
            
            old_role = user.user_role
            user.user_role = role
            user.save()
            
            # Enregistrer l'historique
            RoleHistory.objects.create(
                collaborateur=user,
                old_role=old_role,
                new_role=role,
                changed_by=request.user.collaborateur if hasattr(request.user, 'collaborateur') else None,
                change_reason="Assignation via interface admin"
            )
            
            if role:
                message = f'Rôle "{role.name}" assigné à {user.prenom_collaborateur} {user.nom_collaborateur}'
            else:
                message = f'Rôle retiré pour {user.prenom_collaborateur} {user.nom_collaborateur}'
            
            return JsonResponse({
                'success': True,
                'message': message
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

# ========== VUES POUR LA GESTION DES AFFAIRES ==========

@permission_required('affaires', 'read')
def affaires_list(request):
    """Vue liste des affaires avec filtres et recherche"""
    
    # Récupération des paramètres de recherche et filtrage
    search = request.GET.get('search', '')
    statut_filter = request.GET.get('statut', '')
    responsable_filter = request.GET.get('responsable', '')
    
    # Construction de la requête
    affaires = Affaire.objects.select_related('responsable_affaire').annotate(
        nb_lancements=Count('lancements')
    ).order_by('-date_debut')
    
    # Filtrage par recherche
    if search:
        affaires = affaires.filter(
            Q(code_affaire__icontains=search) | 
            Q(client__icontains=search) |
            Q(livrable__icontains=search)
        )
    
    # Filtrage par statut
    if statut_filter:
        affaires = affaires.filter(statut=statut_filter)
    
    # Filtrage par responsable
    if responsable_filter:
        affaires = affaires.filter(responsable_affaire_id=responsable_filter)
    
    # Pagination
    paginator = Paginator(affaires, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    statuts_choices = Affaire._meta.get_field('statut').choices
    responsables = Collaborateur.objects.filter(
        affaires_responsable__isnull=False
    ).distinct().order_by('nom_collaborateur', 'prenom_collaborateur')
    
    context = {
        'page_obj': page_obj,
        'search_query': search,
        'statut_filter': statut_filter,
        'responsable_filter': int(responsable_filter) if responsable_filter.isdigit() else '',
        'statuts_choices': statuts_choices,
        'responsables': responsables,
        'total_affaires': affaires.count(),
        'can_create': request.user.has_perm('affaires.create'),
        'can_update': request.user.has_perm('affaires.update'),
        'can_delete': request.user.has_perm('affaires.delete'),
    }
    
    return render(request, 'affaires/list.html', context)


@permission_required('affaires', 'read')
def affaire_detail(request, affaire_id):
    """Vue détail d'une affaire"""
    
    affaire = get_object_or_404(Affaire, id=affaire_id)
    
    # Récupérer les lancements liés à cette affaire
    lancements = affaire.lancements.select_related(
        'atelier', 'categorie', 'collaborateur'
    ).order_by('-date_lancement')
    
    # Statistiques de l'affaire
    lancements_stats = {
        'total': lancements.count(),
        'en_cours': lancements.filter(statut='en_cours').count(),
        'termines': lancements.filter(statut='termine').count(),
        'suspendus': lancements.filter(statut='suspendu').count(),
    }
    
    # Calcul du poids total
    poids_total = lancements.aggregate(
        debitage=models.Sum('poids_debitage'),
        assemblage=models.Sum('poids_assemblage')
    )
    
    # Durée prévue vs réalisée - GESTION DES VALEURS NULL
    from datetime import date
    today = date.today()
    
    # Initialiser les variables
    duree_prevue = 0
    duree_ecoulee = 0
    progression = 0
    
    # Calcul seulement si les dates sont présentes
    if affaire.date_debut and affaire.date_fin_prevue:
        duree_prevue = (affaire.date_fin_prevue - affaire.date_debut).days
        if affaire.date_debut <= today:
            duree_ecoulee = (today - affaire.date_debut).days
        
        if duree_prevue > 0:
            progression = min(100, (duree_ecoulee / duree_prevue * 100))
    elif affaire.date_debut:
        # Si on a seulement la date de début
        if affaire.date_debut <= today:
            duree_ecoulee = (today - affaire.date_debut).days
        duree_prevue = "Non définie"
    elif affaire.date_fin_prevue:
        # Si on a seulement la date de fin
        duree_prevue = "Date de début manquante"
    else:
        # Aucune date définie
        duree_prevue = "Dates non définies"
    
    context = {
        'affaire': affaire,
        'lancements': lancements[:10],  # Derniers 10 lancements
        'lancements_stats': lancements_stats,
        'poids_total': poids_total,
        'duree_prevue': duree_prevue,
        'duree_ecoulee': duree_ecoulee,
        'progression': progression,
        'today': today,  # Ajout pour le template
        'can_update': request.user.has_perm('affaires.update'),
        'can_delete': request.user.has_perm('affaires.delete'),
    }
    
    return render(request, 'affaires/detail.html', context)


@permission_required('affaires', 'create')
def affaire_create(request):
    """Vue création d'une nouvelle affaire"""
    
    if request.method == 'POST':
        form = AffaireForm(request.POST)
        if form.is_valid():
            affaire = form.save()
            messages.success(request, f'Affaire "{affaire.code_affaire}" créée avec succès.')
            return redirect('core:affaire_detail', affaire_id=affaire.id)
    else:
        form = AffaireForm()
    
    context = {
        'form': form,
        'action': 'Créer',
        'submit_text': 'Créer l\'affaire',
        'cancel_url': 'core:affaires_list'
    }
    
    return render(request, 'affaires/form.html', context)


@permission_required('affaires', 'update')
def affaire_edit(request, affaire_id):
    """Vue modification d'une affaire"""
    
    affaire = get_object_or_404(Affaire, id=affaire_id)
    
    if request.method == 'POST':
        form = AffaireForm(request.POST, instance=affaire)
        if form.is_valid():
            form.save()
            messages.success(request, f'Affaire "{affaire.code_affaire}" modifiée avec succès.')
            return redirect('core:affaire_detail', affaire_id=affaire.id)
    else:
        form = AffaireForm(instance=affaire)
    
    context = {
        'form': form,
        'affaire': affaire,
        'action': 'Modifier',
        'submit_text': 'Sauvegarder les modifications',
        'cancel_url': 'core:affaire_detail',
        'cancel_url_args': [affaire.id]
    }
    
    return render(request, 'affaires/form.html', context)


@permission_required('affaires', 'delete')
def affaire_delete(request, affaire_id):
    """Vue suppression d'une affaire"""
    
    affaire = get_object_or_404(Affaire, id=affaire_id)
    
    # Vérifier s'il y a des lancements liés
    nb_lancements = affaire.lancements.count()
    
    if request.method == 'POST':
        if nb_lancements > 0:
            messages.error(request, 
                f'Impossible de supprimer l\'affaire "{affaire.code_affaire}" : '
                f'{nb_lancements} lancement(s) y sont associés.')
            return redirect('core:affaire_detail', affaire_id=affaire.id)
        
        code_affaire = affaire.code_affaire
        affaire.delete()
        messages.success(request, f'Affaire "{code_affaire}" supprimée avec succès.')
        return redirect('core:affaires_list')
    
    context = {
        'affaire': affaire,
        'nb_lancements': nb_lancements,
        'can_delete': nb_lancements == 0,
    }
    
    return render(request, 'affaires/delete_confirm.html', context)


@permission_required('affaires', 'update')
def affaire_toggle_statut(request, affaire_id):
    """Changer rapidement le statut d'une affaire (AJAX)"""
    
    if request.method == 'POST':
        affaire = get_object_or_404(Affaire, id=affaire_id)
        nouveau_statut = request.POST.get('statut')
        
        # Vérifier que le statut est valide
        statuts_valides = [choice[0] for choice in affaire._meta.get_field('statut').choices]
        
        if nouveau_statut in statuts_valides:
            ancien_statut = affaire.get_statut_display()
            affaire.statut = nouveau_statut
            affaire.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Statut changé de "{ancien_statut}" vers "{affaire.get_statut_display()}"',
                'nouveau_statut': nouveau_statut,
                'nouveau_statut_display': affaire.get_statut_display()
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Statut invalide'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


@permission_required('affaires', 'read')
def affaires_export(request):
    """Export des affaires en CSV/Excel"""
    import csv
    from django.http import HttpResponse
    from datetime import datetime
    
    # Filtres optionnels
    statut_filter = request.GET.get('statut', '')
    responsable_filter = request.GET.get('responsable', '')
    
    affaires = Affaire.objects.select_related('responsable_affaire')
    
    if statut_filter:
        affaires = affaires.filter(statut=statut_filter)
    if responsable_filter:
        affaires = affaires.filter(responsable_affaire_id=responsable_filter)
    
    # Créer la réponse CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="affaires_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Code Affaire', 'Client', 'Livrable', 'Responsable', 
        'Date Début', 'Date Fin Prévue', 'Statut', 'Nb Lancements'
    ])
    
    for affaire in affaires:
        writer.writerow([
            affaire.code_affaire,
            affaire.client or '',
            affaire.livrable or '',
            affaire.responsable_affaire.get_full_name() if affaire.responsable_affaire else '',
            affaire.date_debut.strftime('%d/%m/%Y') if affaire.date_debut else '',
            affaire.date_fin_prevue.strftime('%d/%m/%Y') if affaire.date_fin_prevue else '',
            affaire.get_statut_display(),
            affaire.lancements.count()
        ])
    
    return response