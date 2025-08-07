from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Collaborateur, RoleHistory
from apps.core.models import Role
from apps.ateliers.models import Atelier, CollaborateurAtelier , CollaborateurCategorie
from apps.lancements.models import Categorie
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if email and password:
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenue {user}!')
                
                # Redirection selon le rôle
                next_url = request.GET.get('next', 'core/dashboard/')
                return redirect(next_url)
            else:
                messages.error(request, 'Email ou mot de passe incorrect.')
        else:
            messages.error(request, 'Veuillez renseigner tous les champs.')
    
    return render(request, 'auth/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'Vous avez été déconnecté avec succès.')
    return render(request, 'auth/logout.html')

@login_required
def collaborateur_list(request):
    """Vue pour lister tous les collaborateurs"""
    # Vérifier les permissions
    if not request.user.has_permission('collaborateurs', 'read'):
        messages.error(request, 'Vous n\'avez pas les permissions pour accéder à cette page.')
        return redirect('core:dashboard')
    
    # Récupérer les paramètres de recherche et filtrage
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    # Construire la requête
    collaborateurs = Collaborateur.objects.select_related('user_role').all()
    
    if search_query:
        collaborateurs = collaborateurs.filter(
            Q(nom_collaborateur__icontains=search_query) |
            Q(prenom_collaborateur__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if role_filter:
        collaborateurs = collaborateurs.filter(user_role_id=role_filter)
    
    if status_filter:
        is_active = status_filter == 'active'
        collaborateurs = collaborateurs.filter(is_active=is_active)
    
    # Pagination
    paginator = Paginator(collaborateurs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Récupérer les rôles pour le filtre
    roles = Role.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': roles,
        'can_create': request.user.has_permission('collaborateurs', 'create'),
        'can_update': request.user.has_permission('collaborateurs', 'update'),
        'can_delete': request.user.has_permission('collaborateurs', 'delete'),
    }
    
    return render(request, 'collaborateurs/list.html', context)

@login_required
def collaborateur_detail(request, pk):
    """Vue pour afficher les détails d'un collaborateur"""
    if not request.user.has_permission('collaborateurs', 'read'):
        messages.error(request, 'Vous n\'avez pas les permissions pour accéder à cette page.')
        return redirect('core:dashboard')
    
    collaborateur = get_object_or_404(Collaborateur, pk=pk)
    
    # Récupérer les informations complémentaires
    affectations_ateliers = CollaborateurAtelier.objects.filter(
        collaborateur=collaborateur
    ).select_related('atelier').order_by('-date_affectation')
    
    competences = CollaborateurCategorie.objects.filter(
        collaborateur=collaborateur
    ).select_related('categorie').order_by('categorie__nom_categorie')
    
    historique_roles = RoleHistory.objects.filter(
        collaborateur=collaborateur
    ).select_related('old_role', 'new_role', 'changed_by').order_by('-changed_at')
    

    
    context = {
        'collaborateur': collaborateur,
        'affectations_ateliers': affectations_ateliers,
        'competences': competences,
        'historique_roles': historique_roles,
        'can_update': request.user.has_permission('collaborateurs', 'update'),
        'can_delete': request.user.has_permission('collaborateurs', 'delete'),
    }
    
    return render(request, 'collaborateurs/detail.html', context)

@login_required
def collaborateur_create(request):
    """Vue pour créer un nouveau collaborateur"""
    if not request.user.has_permission('collaborateurs', 'create'):
        messages.error(request, 'Vous n\'avez pas les permissions pour créer un collaborateur.')
        return redirect('collaborateurs:list')
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        nom = request.POST.get('nom_collaborateur')
        prenom = request.POST.get('prenom_collaborateur')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_role_id = request.POST.get('user_role')
        
        # Validation basique
        if not all([nom, prenom, email, password]):
            messages.error(request, 'Tous les champs obligatoires doivent être remplis.')
        elif Collaborateur.objects.filter(email=email).exists():
            messages.error(request, 'Un collaborateur avec cet email existe déjà.')
        else:
            try:
                # Créer le collaborateur
                collaborateur = Collaborateur.objects.create_user(
                    email=email,
                    nom_collaborateur=nom,
                    prenom_collaborateur=prenom,
                    password=password
                )
                
                # Assigner le rôle si fourni
                if user_role_id:
                    role = Role.objects.get(pk=user_role_id)
                    collaborateur.user_role = role
                    collaborateur.save()
                    
                    # Enregistrer dans l'historique
                    RoleHistory.objects.create(
                        collaborateur=collaborateur,
                        new_role=role,
                        changed_by=request.user,
                        change_reason="Attribution initiale du rôle"
                    )
                
                messages.success(request, f'Collaborateur {collaborateur} créé avec succès.')
                return redirect('collaborateurs:detail', pk=collaborateur.pk)
                
            except Exception as e:
                messages.error(request, f'Erreur lors de la création : {str(e)}')
    
    # Récupérer les rôles actifs pour le formulaire
    roles = Role.objects.filter(is_active=True)
    
    context = {
        'roles': roles,
        'action': 'create',
        'title': 'Créer un collaborateur'
    }
    
    return render(request, 'collaborateurs/form.html', context)

@login_required
def collaborateur_edit(request, pk):
    """Vue pour modifier un collaborateur avec réinitialisation de mot de passe"""
    if not request.user.has_permission('collaborateurs', 'update'):
        messages.error(request, 'Vous n\'avez pas les permissions pour modifier un collaborateur.')
        return redirect('collaborateurs:list')
    
    collaborateur = get_object_or_404(Collaborateur, pk=pk)
    
    # Gérer la réinitialisation du mot de passe via AJAX
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            import json
            data = json.loads(request.body)
            
            if 'reset_password' in data and data['reset_password']:
                new_password = data.get('new_password')
                confirm_password = data.get('confirm_password')
                force_change = data.get('force_password_change', False)
                
                # Validation
                if not new_password or not confirm_password:
                    return JsonResponse({'success': False, 'error': 'Tous les champs sont requis'})
                
                if new_password != confirm_password:
                    return JsonResponse({'success': False, 'error': 'Les mots de passe ne correspondent pas'})
                
                if len(new_password) < 8:
                    return JsonResponse({'success': False, 'error': 'Le mot de passe doit contenir au moins 8 caractères'})
                
                # Réinitialiser le mot de passe
                collaborateur.set_password(new_password)
                
                # Si force_change est activé et que votre modèle le supporte
                if force_change and hasattr(collaborateur, 'must_change_password'):
                    collaborateur.must_change_password = True
                
                collaborateur.save()
                
                # Log de l'action (optionnel - vous pouvez créer un modèle PasswordResetHistory)
                messages.success(request, f'Mot de passe réinitialisé pour {collaborateur}')
                
                return JsonResponse({
                    'success': True, 
                    'message': f'Mot de passe réinitialisé avec succès pour {collaborateur}'
                })
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Données invalides'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Erreur: {str(e)}'})
    
    # Traitement normal du formulaire d'édition
    if request.method == 'POST':
        # Récupérer les données du formulaire
        nom = request.POST.get('nom_collaborateur')
        prenom = request.POST.get('prenom_collaborateur')
        email = request.POST.get('email')
        user_role_id = request.POST.get('user_role')
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation basique
        if not all([nom, prenom, email]):
            messages.error(request, 'Tous les champs obligatoires doivent être remplis.')
        elif Collaborateur.objects.filter(email=email).exclude(pk=pk).exists():
            messages.error(request, 'Un autre collaborateur avec cet email existe déjà.')
        else:
            try:
                # Sauvegarder l'ancien rôle pour l'historique
                old_role = collaborateur.user_role
                
                # Mettre à jour les informations
                collaborateur.nom_collaborateur = nom
                collaborateur.prenom_collaborateur = prenom
                collaborateur.email = email
                collaborateur.is_active = is_active
                
                # Gérer le changement de rôle
                new_role = None
                if user_role_id:
                    new_role = Role.objects.get(pk=user_role_id)
                    collaborateur.user_role = new_role
                else:
                    collaborateur.user_role = None
                
                collaborateur.save()
                
                # Enregistrer le changement de rôle dans l'historique
                if old_role != new_role:
                    RoleHistory.objects.create(
                        collaborateur=collaborateur,
                        old_role=old_role,
                        new_role=new_role,
                        changed_by=request.user,
                        change_reason=request.POST.get('change_reason', 'Modification du rôle')
                    )
                
                messages.success(request, f'Collaborateur {collaborateur} modifié avec succès.')
                return redirect('collaborateurs:detail', pk=collaborateur.pk)
                
            except Exception as e:
                messages.error(request, f'Erreur lors de la modification : {str(e)}')
    
    # Récupérer les rôles actifs pour le formulaire
    roles = Role.objects.filter(is_active=True)
    
    context = {
        'collaborateur': collaborateur,
        'roles': roles,
        'action': 'edit',
        'title': f'Modifier {collaborateur}'
    }
    
    return render(request, 'collaborateurs/edit.html', context)

@login_required
def collaborateur_delete(request, pk):
    """Vue pour supprimer un collaborateur"""
    if not request.user.has_permission('collaborateurs', 'delete'):
        messages.error(request, 'Vous n\'avez pas les permissions pour supprimer un collaborateur.')
        return redirect('collaborateurs:list')
    
    collaborateur = get_object_or_404(Collaborateur, pk=pk)
    
    # Calculer les conditions de blocage dans la vue
    has_active_lancements = False
    try:
        # Essayer d'abord avec 'lancements', puis 'lancement_set'
        if hasattr(collaborateur, 'lancements'):
            has_active_lancements = collaborateur.lancements.filter(
                statut__in=['en_cours', 'lance']
            ).exists()
        elif hasattr(collaborateur, 'lancement_set'):
            has_active_lancements = collaborateur.lancement_set.filter(
                statut__in=['en_cours', 'lance']
            ).exists()
    except AttributeError:
        # La relation n'existe pas, continuer sans erreur
        pass
    
    # Vérifier si le modèle a la relation affaires_responsable
    has_active_affaires = False
    try:
        has_active_affaires = collaborateur.affaires_responsable.filter(
            statut='en_cours'
        ).exists()
    except AttributeError:
        # La relation n'existe pas, continuer sans erreur
        pass
    
    # Vérifier s'il y a des blocages pour la suppression
    can_delete = not (has_active_lancements or has_active_affaires)
    
    if request.method == 'POST':
        # Vérifications supplémentaires côté serveur
        if not can_delete:
            messages.error(request, 
                'Ce collaborateur ne peut pas être supprimé car il a des activités en cours.')
            return redirect('collaborateurs:detail', pk=pk)
        
        # Vérifications du formulaire (sans la vérification du nom)
        delete_reason = request.POST.get('delete_reason')
        
        if not delete_reason:
            messages.error(request, 'Veuillez sélectionner une raison pour la suppression.')
            return redirect('collaborateurs:delete', pk=pk)
        
        # Si "autre" est sélectionné, vérifier que la raison est fournie
        if delete_reason == 'autre':
            other_reason = request.POST.get('other_reason', '').strip()
            if not other_reason:
                messages.error(request, 'Veuillez préciser la raison de la suppression.')
                return redirect('collaborateurs:delete', pk=pk)
        
        try:
            nom_complet = str(collaborateur)
            collaborateur.delete()
            messages.success(request, f'Collaborateur {nom_complet} supprimé avec succès.')
            return redirect('collaborateurs:list')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la suppression : {str(e)}')
            return redirect('collaborateurs:detail', pk=pk)
    
    # Calculer les statistiques pour l'affichage (avec gestion des erreurs)
    stats = {
        'affectations_count': 0,
        'competences_count': 0,
        'lancements_count': 0,
        'affaires_count': 0,
    }
    
    try:
        stats['affectations_count'] = CollaborateurAtelier.objects.filter(collaborateur=collaborateur).count()
    except:
        pass
        
    try:
        stats['competences_count'] = CollaborateurCategorie.objects.filter(collaborateur=collaborateur).count()
    except:
        pass
        
    try:
        # Essayer d'abord avec 'lancements', puis 'lancement_set'
        if hasattr(collaborateur, 'lancements'):
            stats['lancements_count'] = collaborateur.lancements.count()
        elif hasattr(collaborateur, 'lancement_set'):
            stats['lancements_count'] = collaborateur.lancement_set.count()
    except:
        pass
        
    try:
        stats['affaires_count'] = collaborateur.affaires_responsable.count()
    except AttributeError:
        pass
    
    context = {
        'collaborateur': collaborateur,
        'title': f'Supprimer {collaborateur}',
        'has_active_lancements': has_active_lancements,
        'has_active_affaires': has_active_affaires,
        'can_delete': can_delete,
        'stats': stats,
    }
    
    return render(request, 'collaborateurs/delete_confirm.html', context)

@login_required
def profile_view(request):
    """Vue pour afficher le profil de l'utilisateur connecté"""
    return render(request, 'collaborateurs/profile.html', {
        'collaborateur': request.user,
        'permissions': request.user.get_all_permissions()
    })

@login_required
def check_permission_ajax(request):
    """Vue AJAX pour vérifier les permissions côté client"""
    module = request.GET.get('module')
    action = request.GET.get('action')
    
    if module and action:
        has_perm = request.user.has_permission(module, action)
        return JsonResponse({'has_permission': has_perm})
    
    return JsonResponse({'has_permission': False})
