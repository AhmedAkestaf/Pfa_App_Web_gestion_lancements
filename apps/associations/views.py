from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import json

from apps.ateliers.models import (
    CollaborateurAtelier, 
    CollaborateurCategorie, 
    AtelierCategorie,
    Atelier,
    Categorie
)
from apps.collaborateurs.models import Collaborateur


# =============================================================================
# VUES COLLABORATEUR-ATELIER
# =============================================================================

@login_required
def collaborateur_atelier_list(request):
    """Liste des affectations collaborateur-atelier"""
    if not request.user.has_permission('ateliers', 'read'):
        messages.error(request, 'Vous n\'avez pas les permissions pour accéder à cette page.')
        return redirect('core:dashboard')
    
    # Paramètres de recherche
    search_query = request.GET.get('search', '')
    atelier_filter = request.GET.get('atelier', '')
    collaborateur_filter = request.GET.get('collaborateur', '')
    
    # Requête de base
    affectations = CollaborateurAtelier.objects.select_related(
        'collaborateur', 'atelier'
    ).all()
    
    # Filtres
    if search_query:
        affectations = affectations.filter(
            Q(collaborateur__nom_collaborateur__icontains=search_query) |
            Q(collaborateur__prenom_collaborateur__icontains=search_query) |
            Q(atelier__nom_atelier__icontains=search_query)
        )
    
    if atelier_filter:
        affectations = affectations.filter(atelier_id=atelier_filter)
    
    if collaborateur_filter:
        affectations = affectations.filter(collaborateur_id=collaborateur_filter)
    
    # Tri par collaborateur et atelier
    affectations = affectations.order_by('collaborateur__nom_collaborateur', 'atelier__nom_atelier')
    
    # Pagination
    paginator = Paginator(affectations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    ateliers = Atelier.objects.all().order_by('nom_atelier')
    collaborateurs = Collaborateur.objects.filter(is_active=True).order_by('nom_collaborateur', 'prenom_collaborateur')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'atelier_filter': atelier_filter,
        'collaborateur_filter': collaborateur_filter,
        'ateliers': ateliers,
        'collaborateurs': collaborateurs,
    }
    
    return render(request, 'associations/collaborateur_atelier_list.html', context)


@login_required
def collaborateur_atelier_create(request):
    """Créer une nouvelle affectation collaborateur-atelier"""
    if not request.user.has_permission('ateliers', 'create'):
        messages.error(request, 'Vous n\'avez pas les permissions pour créer une affectation.')
        return redirect('associations:collaborateur_atelier_list')
    
    if request.method == 'POST':
        collaborateur_id = request.POST.get('collaborateur')
        atelier_id = request.POST.get('atelier')
        
        # Validation
        if not all([collaborateur_id, atelier_id]):
            messages.error(request, 'Collaborateur et atelier sont obligatoires.')
            return redirect('associations:collaborateur_atelier_create')
        
        try:
            collaborateur = Collaborateur.objects.get(id=collaborateur_id)
            atelier = Atelier.objects.get(id=atelier_id)
            
            # Vérifier qu'il n'y a pas déjà cette affectation
            existing = CollaborateurAtelier.objects.filter(
                collaborateur=collaborateur,
                atelier=atelier
            ).exists()
            
            if existing:
                messages.error(request, 
                    f'{collaborateur} est déjà affecté à {atelier}.')
                return redirect('associations:collaborateur_atelier_create')
            
            # Créer l'affectation
            affectation = CollaborateurAtelier.objects.create(
                collaborateur=collaborateur,
                atelier=atelier
            )
            
            messages.success(request, 
                f'Affectation créée : {collaborateur} → {atelier}')
            return redirect('associations:collaborateur_atelier_list')
            
        except (Collaborateur.DoesNotExist, Atelier.DoesNotExist):
            messages.error(request, 'Collaborateur ou atelier introuvable.')
        except Exception as e:
            messages.error(request, f'Erreur lors de la création : {str(e)}')
    
    # Données pour le formulaire
    collaborateurs = Collaborateur.objects.filter(is_active=True).order_by('nom_collaborateur', 'prenom_collaborateur')
    ateliers = Atelier.objects.all().order_by('nom_atelier')
    
    context = {
        'collaborateurs': collaborateurs,
        'ateliers': ateliers,
    }
    
    return render(request, 'associations/collaborateur_atelier_create.html', context)


@login_required
@require_http_methods(["POST"])
def collaborateur_atelier_terminate(request, pk):
    """Terminer une affectation collaborateur-atelier (marquer comme inactive)"""
    if not request.user.has_permission('ateliers', 'update'):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    try:
        affectation = get_object_or_404(CollaborateurAtelier, pk=pk)
        collaborateur_nom = str(affectation.collaborateur)
        atelier_nom = str(affectation.atelier)
        
        # Ajouter une date de fin si le modèle en a une, sinon marquer comme inactif
        if hasattr(affectation, 'date_fin'):
            affectation.date_fin = timezone.now()
            affectation.save()
        elif hasattr(affectation, 'is_active'):
            affectation.is_active = False
            affectation.save()
        else:
            # Si pas de champ pour marquer comme terminé, on supprime
            affectation.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'Affectation terminée : {collaborateur_nom} → {atelier_nom}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def collaborateur_atelier_delete(request, pk):
    """Supprimer une affectation collaborateur-atelier"""
    if not request.user.has_permission('ateliers', 'delete'):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    try:
        affectation = get_object_or_404(CollaborateurAtelier, pk=pk)
        collaborateur_nom = str(affectation.collaborateur)
        atelier_nom = str(affectation.atelier)
        affectation.delete()
        return JsonResponse({
            'success': True, 
            'message': f'Affectation supprimée : {collaborateur_nom} → {atelier_nom}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =============================================================================
# VUES COLLABORATEUR-CATEGORIE
# =============================================================================

@login_required
def collaborateur_categorie_list(request):
    """Liste des compétences collaborateur-catégorie"""
    if not request.user.has_permission('ateliers', 'read'):
        messages.error(request, 'Vous n\'avez pas les permissions pour accéder à cette page.')
        return redirect('core:dashboard')
    
    # Paramètres de recherche
    search_query = request.GET.get('search', '')
    collaborateur_filter = request.GET.get('collaborateur', '')
    categorie_filter = request.GET.get('categorie', '')
    
    # Requête de base
    competences = CollaborateurCategorie.objects.select_related(
        'collaborateur', 'categorie'
    ).all()
    
    # Filtres
    if search_query:
        competences = competences.filter(
            Q(collaborateur__nom_collaborateur__icontains=search_query) |
            Q(collaborateur__prenom_collaborateur__icontains=search_query) |
            Q(categorie__nom_categorie__icontains=search_query)
        )
    
    if collaborateur_filter:
        competences = competences.filter(collaborateur_id=collaborateur_filter)
    
    if categorie_filter:
        competences = competences.filter(categorie_id=categorie_filter)
    
    # Tri
    competences = competences.order_by('collaborateur__nom_collaborateur', 'categorie__nom_categorie')
    
    # Pagination
    paginator = Paginator(competences, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    collaborateurs = Collaborateur.objects.filter(is_active=True).order_by('nom_collaborateur', 'prenom_collaborateur')
    categories = Categorie.objects.all().order_by('nom_categorie')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'collaborateur_filter': collaborateur_filter,
        'categorie_filter': categorie_filter,
        'collaborateurs': collaborateurs,
        'categories': categories,
    }
    
    return render(request, 'associations/collaborateur_categorie_list.html', context)


@login_required
def collaborateur_categorie_create(request):
    """Créer une nouvelle compétence collaborateur-catégorie"""
    if not request.user.has_permission('ateliers', 'create'):
        messages.error(request, 'Vous n\'avez pas les permissions pour créer une compétence.')
        return redirect('associations:collaborateur_categorie_list')
    
    if request.method == 'POST':
        collaborateur_id = request.POST.get('collaborateur')
        categorie_id = request.POST.get('categorie')
        
        # Validation
        if not all([collaborateur_id, categorie_id]):
            messages.error(request, 'Collaborateur et catégorie sont obligatoires.')
            return redirect('associations:collaborateur_categorie_create')
        
        try:
            collaborateur = Collaborateur.objects.get(id=collaborateur_id)
            categorie = Categorie.objects.get(id=categorie_id)
            
            # Vérifier qu'il n'y a pas déjà cette compétence
            existing = CollaborateurCategorie.objects.filter(
                collaborateur=collaborateur,
                categorie=categorie
            ).exists()
            
            if existing:
                messages.error(request, 
                    f'{collaborateur} a déjà une compétence dans {categorie}.')
                return redirect('associations:collaborateur_categorie_create')
            
            # Créer la compétence
            competence = CollaborateurCategorie.objects.create(
                collaborateur=collaborateur,
                categorie=categorie
            )
            
            messages.success(request, 
                f'Compétence créée : {collaborateur} → {categorie}')
            return redirect('associations:collaborateur_categorie_list')
            
        except (Collaborateur.DoesNotExist, Categorie.DoesNotExist):
            messages.error(request, 'Collaborateur ou catégorie introuvable.')
        except Exception as e:
            messages.error(request, f'Erreur lors de la création : {str(e)}')
    
    # Données pour le formulaire
    collaborateurs = Collaborateur.objects.filter(is_active=True).order_by('nom_collaborateur', 'prenom_collaborateur')
    categories = Categorie.objects.all().order_by('nom_categorie')
    
    context = {
        'collaborateurs': collaborateurs,
        'categories': categories,
    }
    
    return render(request, 'associations/collaborateur_categorie_create.html', context)


@login_required
@require_http_methods(["POST"])
def collaborateur_categorie_upgrade(request, pk):
    """Améliorer le niveau d'une compétence collaborateur-catégorie"""
    if not request.user.has_permission('ateliers', 'update'):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    try:
        competence = get_object_or_404(CollaborateurCategorie, pk=pk)
        collaborateur_nom = str(competence.collaborateur)
        categorie_nom = str(competence.categorie)
        
        # Si le modèle a un champ niveau, l'améliorer
        if hasattr(competence, 'niveau'):
            niveau_precedent = competence.niveau
            # Supposons que les niveaux sont : Débutant -> Intermédiaire -> Avancé -> Expert
            niveaux = ['Débutant', 'Intermédiaire', 'Avancé', 'Expert']
            if competence.niveau in niveaux:
                current_index = niveaux.index(competence.niveau)
                if current_index < len(niveaux) - 1:
                    competence.niveau = niveaux[current_index + 1]
                    competence.save()
                    return JsonResponse({
                        'success': True, 
                        'message': f'Niveau amélioré pour {collaborateur_nom} → {categorie_nom} : {niveau_precedent} → {competence.niveau}'
                    })
                else:
                    return JsonResponse({
                        'success': False, 
                        'error': f'Niveau maximum déjà atteint pour {collaborateur_nom} → {categorie_nom}'
                    })
        
        # Si pas de champ niveau, mettre à jour la date de modification
        if hasattr(competence, 'date_modification'):
            competence.date_modification = timezone.now()
            competence.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Compétence mise à jour : {collaborateur_nom} → {categorie_nom}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def collaborateur_categorie_delete(request, pk):
    """Supprimer une compétence collaborateur-catégorie"""
    if not request.user.has_permission('ateliers', 'delete'):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    try:
        competence = get_object_or_404(CollaborateurCategorie, pk=pk)
        collaborateur_nom = str(competence.collaborateur)
        categorie_nom = str(competence.categorie)
        competence.delete()
        return JsonResponse({
            'success': True, 
            'message': f'Compétence supprimée : {collaborateur_nom} → {categorie_nom}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =============================================================================
# VUES ATELIER-CATEGORIE
# =============================================================================

@login_required
def atelier_categorie_list(request):
    """Liste des relations atelier-catégorie"""
    if not request.user.has_permission('ateliers', 'read'):
        messages.error(request, 'Vous n\'avez pas les permissions pour accéder à cette page.')
        return redirect('core:dashboard')
    
    # Paramètres de recherche
    search_query = request.GET.get('search', '')
    atelier_filter = request.GET.get('atelier', '')
    categorie_filter = request.GET.get('categorie', '')
    
    # Requête de base
    relations = AtelierCategorie.objects.select_related(
        'atelier', 'categorie'
    ).all()
    
    # Filtres
    if search_query:
        relations = relations.filter(
            Q(atelier__nom_atelier__icontains=search_query) |
            Q(categorie__nom_categorie__icontains=search_query)
        )
    
    if atelier_filter:
        relations = relations.filter(atelier_id=atelier_filter)
    
    if categorie_filter:
        relations = relations.filter(categorie_id=categorie_filter)
    
    # Tri
    relations = relations.order_by('atelier__nom_atelier', 'categorie__nom_categorie')
    
    # Pagination
    paginator = Paginator(relations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    ateliers = Atelier.objects.all().order_by('nom_atelier')
    categories = Categorie.objects.all().order_by('nom_categorie')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'atelier_filter': atelier_filter,
        'categorie_filter': categorie_filter,
        'ateliers': ateliers,
        'categories': categories,
    }
    
    return render(request, 'associations/atelier_categorie_list.html', context)


@login_required
def atelier_categorie_create(request):
    """Créer une nouvelle relation atelier-catégorie"""
    if not request.user.has_permission('ateliers', 'create'):
        messages.error(request, 'Vous n\'avez pas les permissions pour créer une relation.')
        return redirect('associations:atelier_categorie_list')
    
    if request.method == 'POST':
        atelier_id = request.POST.get('atelier')
        categorie_id = request.POST.get('categorie')
        
        # Validation
        if not all([atelier_id, categorie_id]):
            messages.error(request, 'Atelier et catégorie sont obligatoires.')
            return redirect('associations:atelier_categorie_create')
        
        try:
            atelier = Atelier.objects.get(id=atelier_id)
            categorie = Categorie.objects.get(id=categorie_id)
            
            # Vérifier qu'il n'y a pas déjà cette relation
            existing = AtelierCategorie.objects.filter(
                atelier=atelier,
                categorie=categorie
            ).exists()
            
            if existing:
                messages.error(request, 
                    f'Une relation existe déjà pour {atelier} → {categorie}.')
                return redirect('associations:atelier_categorie_create')
            
            # Créer la relation
            relation = AtelierCategorie.objects.create(
                atelier=atelier,
                categorie=categorie
            )
            
            messages.success(request, 
                f'Relation créée : {atelier} → {categorie}')
            return redirect('associations:atelier_categorie_list')
            
        except (Atelier.DoesNotExist, Categorie.DoesNotExist):
            messages.error(request, 'Atelier ou catégorie introuvable.')
        except Exception as e:
            messages.error(request, f'Erreur lors de la création : {str(e)}')
    
    # Données pour le formulaire
    ateliers = Atelier.objects.all().order_by('nom_atelier')
    categories = Categorie.objects.all().order_by('nom_categorie')
    
    context = {
        'ateliers': ateliers,
        'categories': categories,
    }
    
    return render(request, 'associations/atelier_categorie_create.html', context)


@login_required
def atelier_categorie_details(request, pk):
    """Afficher les détails d'une relation atelier-catégorie"""
    if not request.user.has_permission('ateliers', 'read'):
        messages.error(request, 'Vous n\'avez pas les permissions pour accéder à cette page.')
        return redirect('associations:atelier_categorie_list')
    
    try:
        relation = get_object_or_404(AtelierCategorie, pk=pk)
        
        # Statistiques utiles
        context = {
            'relation': relation,
            'atelier': relation.atelier,
            'categorie': relation.categorie,
        }
        
        # Ajouter des collaborateurs compétents dans cette catégorie pour cet atelier
        if hasattr(relation.atelier, 'collaborateurs'):
            collaborateurs_competents = CollaborateurCategorie.objects.filter(
                categorie=relation.categorie,
                collaborateur__in=relation.atelier.collaborateurs.all()
            ).select_related('collaborateur')
            context['collaborateurs_competents'] = collaborateurs_competents
        
        return render(request, 'associations/atelier_categorie_details.html', context)
        
    except Exception as e:
        messages.error(request, f'Erreur lors de l\'affichage : {str(e)}')
        return redirect('associations:atelier_categorie_list')


@login_required
def atelier_categorie_update(request, pk):
    """Modifier une relation atelier-catégorie"""
    if not request.user.has_permission('ateliers', 'update'):
        messages.error(request, 'Vous n\'avez pas les permissions pour modifier cette relation.')
        return redirect('associations:atelier_categorie_list')
    
    try:
        relation = get_object_or_404(AtelierCategorie, pk=pk)
        
        if request.method == 'POST':
            atelier_id = request.POST.get('atelier')
            categorie_id = request.POST.get('categorie')
            
            # Validation
            if not all([atelier_id, categorie_id]):
                messages.error(request, 'Atelier et catégorie sont obligatoires.')
                return redirect('associations:atelier_categorie_update', pk=pk)
            
            try:
                atelier = Atelier.objects.get(id=atelier_id)
                categorie = Categorie.objects.get(id=categorie_id)
                
                # Vérifier qu'il n'y a pas déjà cette relation (sauf celle actuelle)
                existing = AtelierCategorie.objects.filter(
                    atelier=atelier,
                    categorie=categorie
                ).exclude(id=relation.id).exists()
                
                if existing:
                    messages.error(request, 
                        f'Une relation existe déjà pour {atelier} → {categorie}.')
                    return redirect('associations:atelier_categorie_update', pk=pk)
                
                # Modifier la relation
                relation.atelier = atelier
                relation.categorie = categorie
                relation.save()
                
                messages.success(request, 
                    f'Relation modifiée : {atelier} → {categorie}')
                return redirect('associations:atelier_categorie_list')
                
            except (Atelier.DoesNotExist, Categorie.DoesNotExist):
                messages.error(request, 'Atelier ou catégorie introuvable.')
            except Exception as e:
                messages.error(request, f'Erreur lors de la modification : {str(e)}')
        
        # Données pour le formulaire
        ateliers = Atelier.objects.all().order_by('nom_atelier')
        categories = Categorie.objects.all().order_by('nom_categorie')
        
        context = {
            'relation': relation,
            'ateliers': ateliers,
            'categories': categories,
        }
        
        return render(request, 'associations/atelier_categorie_update.html', context)
        
    except Exception as e:
        messages.error(request, f'Erreur lors de l\'affichage : {str(e)}')
        return redirect('associations:atelier_categorie_list')


@login_required
@require_http_methods(["POST"])
def atelier_categorie_delete(request, pk):
    """Supprimer une relation atelier-catégorie"""
    if not request.user.has_permission('ateliers', 'delete'):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    try:
        relation = get_object_or_404(AtelierCategorie, pk=pk)
        atelier_nom = str(relation.atelier)
        categorie_nom = str(relation.categorie)
        relation.delete()
        return JsonResponse({
            'success': True, 
            'message': f'Relation supprimée : {atelier_nom} → {categorie_nom}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =============================================================================
# VUES UTILITAIRES AJAX
# =============================================================================

@login_required
@require_http_methods(["POST"])
def check_collaborateur_atelier_conflict(request):
    """Vérifier les conflits d'affectation collaborateur-atelier"""
    try:
        data = json.loads(request.body)
        collaborateur_id = data.get('collaborateur_id')
        atelier_id = data.get('atelier_id')
        
        if not collaborateur_id or not atelier_id:
            return JsonResponse({'has_conflict': False})
        
        # Vérifier s'il y a déjà cette affectation
        conflict = CollaborateurAtelier.objects.filter(
            collaborateur_id=collaborateur_id,
            atelier_id=atelier_id
        ).exists()
        
        if conflict:
            return JsonResponse({
                'has_conflict': True,
                'message': 'Ce collaborateur est déjà affecté à cet atelier.'
            })
        
        return JsonResponse({'has_conflict': False})
        
    except Exception as e:
        return JsonResponse({'has_conflict': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def check_collaborateur_categorie_conflict(request):
    """Vérifier les conflits de compétence collaborateur-catégorie"""
    try:
        data = json.loads(request.body)
        collaborateur_id = data.get('collaborateur_id')
        categorie_id = data.get('categorie_id')
        
        if not collaborateur_id or not categorie_id:
            return JsonResponse({'has_conflict': False})
        
        # Vérifier s'il y a déjà cette compétence
        conflict = CollaborateurCategorie.objects.filter(
            collaborateur_id=collaborateur_id,
            categorie_id=categorie_id
        ).exists()
        
        if conflict:
            return JsonResponse({
                'has_conflict': True,
                'message': 'Ce collaborateur a déjà une compétence dans cette catégorie.'
            })
        
        return JsonResponse({'has_conflict': False})
        
    except Exception as e:
        return JsonResponse({'has_conflict': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def check_atelier_categorie_conflict(request):
    """Vérifier les conflits de relation atelier-catégorie"""
    try:
        data = json.loads(request.body)
        atelier_id = data.get('atelier_id')
        categorie_id = data.get('categorie_id')
        
        if not atelier_id or not categorie_id:
            return JsonResponse({'has_conflict': False})
        
        # Vérifier s'il y a déjà cette relation
        conflict = AtelierCategorie.objects.filter(
            atelier_id=atelier_id,
            categorie_id=categorie_id
        ).exists()
        
        if conflict:
            return JsonResponse({
                'has_conflict': True,
                'message': 'Une relation existe déjà pour cette association atelier-catégorie.'
            })
        
        return JsonResponse({'has_conflict': False})
        
    except Exception as e:
        return JsonResponse({'has_conflict': False, 'error': str(e)})