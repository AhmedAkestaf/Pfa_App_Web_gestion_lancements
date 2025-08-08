from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from .models import Atelier, AtelierCategorie, Categorie
from apps.collaborateurs.models import Collaborateur
from apps.core.models import Role
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from .models import Atelier, Categorie, AtelierCategorie, CollaborateurAtelier, CollaborateurCategorie

@login_required
def atelier_list(request):
    """Vue pour afficher la liste des ateliers avec filtres et pagination"""
    
    # Vérifier les permissions
    if not request.user.has_permission('ateliers', 'read'):
        messages.error(request, 'Vous n\'avez pas les permissions pour accéder à cette page.')
        return redirect('core:dashboard')
    
    # Récupération des paramètres de recherche et filtrage
    search_query = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    responsable_filter = request.GET.get('responsable', '')
    status_filter = request.GET.get('status', '')
    
    # Construction de la requête de base
    ateliers = Atelier.objects.select_related('responsable_atelier').all()
    
    # Application des filtres
    if search_query:
        ateliers = ateliers.filter(
            Q(nom_atelier__icontains=search_query) |
            Q(responsable_atelier__nom_collaborateur__icontains=search_query) |
            Q(responsable_atelier__prenom_collaborateur__icontains=search_query)
        )
    
    if type_filter:
        ateliers = ateliers.filter(type_atelier=type_filter)
    
    if responsable_filter:
        ateliers = ateliers.filter(responsable_atelier_id=responsable_filter)
    
    # Pagination
    paginator = Paginator(ateliers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    types_ateliers = Atelier._meta.get_field('type_atelier').choices
    responsables = Collaborateur.objects.filter(ateliers_responsable__isnull=False).distinct()
    
    # Vérification des permissions
    can_create = request.user.has_permission('ateliers', 'create')
    can_update = request.user.has_permission('ateliers', 'update')
    can_delete = request.user.has_permission('ateliers', 'delete')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'type_filter': type_filter,
        'responsable_filter': responsable_filter,
        'status_filter': status_filter,
        'types_ateliers': types_ateliers,
        'responsables': responsables,
        'can_create': can_create,
        'can_update': can_update,
        'can_delete': can_delete,
    }
    
    return render(request, 'ateliers/list.html', context)


@login_required
def atelier_detail(request, pk):
    """Vue pour afficher les détails d'un atelier"""
    
    if not request.user.has_permission('ateliers', 'read'):
        messages.error(request, 'Vous n\'avez pas les permissions pour accéder à cette page.')
        return redirect('core:dashboard')
    
    atelier = get_object_or_404(
        Atelier.objects.select_related('responsable_atelier'),
        pk=pk
    )
    
    # Récupération des catégories associées à l'atelier
    atelier_categories = AtelierCategorie.objects.filter(
        atelier=atelier
    ).select_related('categorie')
    
    # Récupération des collaborateurs affectés à l'atelier
    collaborateurs_affectes = atelier.collaborateuratelier_set.filter(
        date_fin_affectation__isnull=True
    ).select_related('collaborateur')
    
    # Vérification des permissions
    can_update = request.user.has_permission('ateliers', 'update')
    can_delete = request.user.has_permission('ateliers', 'delete')
    
    context = {
        'atelier': atelier,
        'atelier_categories': atelier_categories,
        'collaborateurs_affectes': collaborateurs_affectes,
        'can_update': can_update,
        'can_delete': can_delete,
    }
    
    return render(request, 'ateliers/detail.html', context)


@login_required
def atelier_create(request):
    """Vue pour créer un nouvel atelier"""
    
    if not request.user.has_permission('ateliers', 'create'):
        messages.error(request, 'Vous n\'avez pas les permissions pour créer un atelier.')
        return redirect('ateliers:list')
    
    if request.method == 'POST':
        # Récupération des données du formulaire
        nom_atelier = request.POST.get('nom_atelier')
        type_atelier = request.POST.get('type_atelier')
        capacite_max = request.POST.get('capacite_max')
        responsable_atelier_id = request.POST.get('responsable_atelier')
        
        # Validation basique
        if not all([nom_atelier, type_atelier, capacite_max]):
            messages.error(request, "Tous les champs obligatoires doivent être remplis.")
            return redirect('ateliers:create')
        
        try:
            # Création de l'atelier
            responsable = None
            if responsable_atelier_id:
                responsable = Collaborateur.objects.get(id=responsable_atelier_id)
            
            atelier = Atelier.objects.create(
                nom_atelier=nom_atelier,
                type_atelier=type_atelier,
                capacite_max=int(capacite_max),
                responsable_atelier=responsable
            )
            
            messages.success(request, f"L'atelier '{nom_atelier}' a été créé avec succès.")
            return redirect('ateliers:detail', pk=atelier.pk)
            
        except ValueError:
            messages.error(request, "La capacité maximale doit être un nombre entier.")
        except Collaborateur.DoesNotExist:
            messages.error(request, "Le responsable sélectionné n'existe pas.")
        except Exception as e:
            messages.error(request, f"Erreur lors de la création : {str(e)}")
    
    # Données pour le formulaire
    types_ateliers = Atelier._meta.get_field('type_atelier').choices
    collaborateurs = Collaborateur.objects.filter(is_active=True).order_by(
        'nom_collaborateur', 'prenom_collaborateur'
    )
    
    context = {
        'types_ateliers': types_ateliers,
        'collaborateurs': collaborateurs,
    }
    
    return render(request, 'ateliers/create.html', context)


@login_required
def atelier_edit(request, pk):
    """Vue pour modifier un atelier existant"""
    
    if not request.user.has_permission('ateliers', 'update'):
        messages.error(request, 'Vous n\'avez pas les permissions pour modifier un atelier.')
        return redirect('ateliers:list')
    
    atelier = get_object_or_404(Atelier, pk=pk)
    
    if request.method == 'POST':
        # Récupération des données du formulaire
        nom_atelier = request.POST.get('nom_atelier')
        type_atelier = request.POST.get('type_atelier')
        capacite_max = request.POST.get('capacite_max')
        responsable_atelier_id = request.POST.get('responsable_atelier')
        
        # Validation basique
        if not all([nom_atelier, type_atelier, capacite_max]):
            messages.error(request, "Tous les champs obligatoires doivent être remplis.")
            return redirect('ateliers:edit', pk=pk)
        
        try:
            # Mise à jour de l'atelier
            responsable = None
            if responsable_atelier_id:
                responsable = Collaborateur.objects.get(id=responsable_atelier_id)
            
            atelier.nom_atelier = nom_atelier
            atelier.type_atelier = type_atelier
            atelier.capacite_max = int(capacite_max)
            atelier.responsable_atelier = responsable
            atelier.save()
            
            messages.success(request, f"L'atelier '{nom_atelier}' a été modifié avec succès.")
            return redirect('ateliers:detail', pk=atelier.pk)
            
        except ValueError:
            messages.error(request, "La capacité maximale doit être un nombre entier.")
        except Collaborateur.DoesNotExist:
            messages.error(request, "Le responsable sélectionné n'existe pas.")
        except Exception as e:
            messages.error(request, f"Erreur lors de la modification : {str(e)}")
    
    # Données pour le formulaire
    types_ateliers = Atelier._meta.get_field('type_atelier').choices
    collaborateurs = Collaborateur.objects.filter(is_active=True).order_by(
        'nom_collaborateur', 'prenom_collaborateur'
    )
    
    context = {
        'atelier': atelier,
        'types_ateliers': types_ateliers,
        'collaborateurs': collaborateurs,
    }
    
    return render(request, 'ateliers/edit.html', context)


@login_required
def atelier_delete(request, pk):
    """Vue pour supprimer un atelier"""
    
    if not request.user.has_permission('ateliers', 'delete'):
        messages.error(request, 'Vous n\'avez pas les permissions pour supprimer un atelier.')
        return redirect('ateliers:list')
    
    atelier = get_object_or_404(Atelier, pk=pk)
    
    if request.method == 'POST':
        try:
            nom_atelier = atelier.nom_atelier
            atelier.delete()
            messages.success(request, f"L'atelier '{nom_atelier}' a été supprimé avec succès.")
            return redirect('ateliers:list')
        except Exception as e:
            messages.error(request, f"Impossible de supprimer l'atelier : {str(e)}")
            return redirect('ateliers:detail', pk=pk)
    
    # Vérification des dépendances
    lancements_count = atelier.lancement_set.count() if hasattr(atelier, 'lancement_set') else 0
    collaborateurs_affectes = atelier.collaborateuratelier_set.filter(
        date_fin_affectation__isnull=True
    ).count()
    
    context = {
        'atelier': atelier,
        'lancements_count': lancements_count,
        'collaborateurs_affectes': collaborateurs_affectes,
    }
    
    return render(request, 'ateliers/delete_confirm.html', context)

@login_required
def categorie_list(request):
    """Vue pour afficher la liste des catégories avec filtres et pagination"""
    
    # Vérifier les permissions
    if not request.user.has_permission('categories', 'read'):
        messages.error(request, 'Vous n\'avez pas les permissions pour accéder à cette page.')
        return redirect('core:dashboard')
    
    # Récupération des paramètres de recherche et filtrage
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    
    # Construction de la requête de base avec annotations
    categories = Categorie.objects.annotate(
        ateliers_count=Count('ateliercategorie', distinct=True),
        collaborateurs_count=Count('collaborateurcategorie', distinct=True)
    )
    
    # Application des filtres
    if search_query:
        categories = categories.filter(
            Q(nom_categorie__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if date_from:
        categories = categories.filter(created_at__gte=date_from)
    
    # Tri par nom
    categories = categories.order_by('nom_categorie')
    
    # Pagination
    paginator = Paginator(categories, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Vérification des permissions
    can_create = request.user.has_permission('categories', 'create')
    can_update = request.user.has_permission('categories', 'update')
    can_delete = request.user.has_permission('categories', 'delete')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'date_from': date_from,
        'can_create': can_create,
        'can_update': can_update,
        'can_delete': can_delete,
    }
    
    return render(request, 'categories/list.html', context)


@login_required
def categorie_detail(request, pk):
    """Vue pour afficher les détails d'une catégorie"""
    
    if not request.user.has_permission('categories', 'read'):
        messages.error(request, 'Vous n\'avez pas les permissions pour accéder à cette page.')
        return redirect('core:dashboard')
    
    categorie = get_object_or_404(Categorie, pk=pk)
    
    # Récupération des ateliers associés
    ateliers_associes = AtelierCategorie.objects.filter(
        categorie=categorie
    ).select_related('atelier')
    
    # Récupération des collaborateurs compétents
    collaborateurs_competents = CollaborateurCategorie.objects.filter(
        categorie=categorie
    ).select_related('collaborateur').order_by('-date_certification')
    
    # Récupération des lancements récents (10 derniers)
    lancements_recents = []
    lancements_count = 0
    try:
        if hasattr(categorie, 'lancement_set'):
            lancements_recents = categorie.lancement_set.select_related(
                'affaire', 'atelier', 'collaborateur'
            ).order_by('-date_lancement')[:10]
            lancements_count = categorie.lancement_set.count()
    except:
        pass
    
    # Vérification des permissions
    can_update = request.user.has_permission('categories', 'update')
    can_delete = request.user.has_permission('categories', 'delete')
    
    context = {
        'categorie': categorie,
        'ateliers_associes': ateliers_associes,
        'collaborateurs_competents': collaborateurs_competents,
        'lancements_recents': lancements_recents,
        'lancements_count': lancements_count,
        'can_update': can_update,
        'can_delete': can_delete,
    }
    
    return render(request, 'categories/detail.html', context)


@login_required
def categorie_create(request):
    """Vue pour créer une nouvelle catégorie"""
    
    if not request.user.has_permission('categories', 'create'):
        messages.error(request, 'Vous n\'avez pas les permissions pour créer une catégorie.')
        return redirect('ateliers:categorie_list')
    
    if request.method == 'POST':
        # Récupération des données du formulaire
        nom_categorie = request.POST.get('nom_categorie', '').strip()
        description = request.POST.get('description', '').strip()
        
        # Validation basique
        if not nom_categorie:
            messages.error(request, "Le nom de la catégorie est obligatoire.")
        elif len(nom_categorie) > 100:
            messages.error(request, "Le nom de la catégorie ne peut pas dépasser 100 caractères.")
        elif Categorie.objects.filter(nom_categorie=nom_categorie).exists():
            messages.error(request, "Une catégorie avec ce nom existe déjà.")
        else:
            try:
                # Création de la catégorie
                categorie = Categorie.objects.create(
                    nom_categorie=nom_categorie,
                    description=description if description else None
                )
                
                messages.success(request, f"La catégorie '{nom_categorie}' a été créée avec succès.")
                return redirect('ateliers:categorie_detail', pk=categorie.pk)
                
            except Exception as e:
                messages.error(request, f"Erreur lors de la création : {str(e)}")
    
    return render(request, 'categories/create.html')


@login_required
def categorie_edit(request, pk):
    """Vue pour modifier une catégorie existante"""
    
    if not request.user.has_permission('categories', 'update'):
        messages.error(request, 'Vous n\'avez pas les permissions pour modifier une catégorie.')
        return redirect('ateliers:categorie_list')
    
    categorie = get_object_or_404(Categorie, pk=pk)
    
    if request.method == 'POST':
        # Récupération des données du formulaire
        nom_categorie = request.POST.get('nom_categorie', '').strip()
        description = request.POST.get('description', '').strip()
        
        # Validation basique
        if not nom_categorie:
            messages.error(request, "Le nom de la catégorie est obligatoire.")
        elif len(nom_categorie) > 100:
            messages.error(request, "Le nom de la catégorie ne peut pas dépasser 100 caractères.")
        elif Categorie.objects.filter(nom_categorie=nom_categorie).exclude(pk=pk).exists():
            messages.error(request, "Une autre catégorie avec ce nom existe déjà.")
        else:
            try:
                # Mise à jour de la catégorie
                categorie.nom_categorie = nom_categorie
                categorie.description = description if description else None
                categorie.save()
                
                messages.success(request, f"La catégorie '{nom_categorie}' a été modifiée avec succès.")
                return redirect('ateliers:categorie_detail', pk=categorie.pk)
                
            except Exception as e:
                messages.error(request, f"Erreur lors de la modification : {str(e)}")
    
    # Statistiques pour l'affichage
    ateliers_count = AtelierCategorie.objects.filter(categorie=categorie).count()
    collaborateurs_count = CollaborateurCategorie.objects.filter(categorie=categorie).count()
    lancements_count = 0
    try:
        if hasattr(categorie, 'lancement_set'):
            lancements_count = categorie.lancement_set.count()
    except:
        pass
    
    context = {
        'categorie': categorie,
        'ateliers_count': ateliers_count,
        'collaborateurs_count': collaborateurs_count,
        'lancements_count': lancements_count,
    }
    
    return render(request, 'categories/edit.html', context)


@login_required
def categorie_delete(request, pk):
    """Vue pour supprimer une catégorie"""
    
    if not request.user.has_permission('categories', 'delete'):
        messages.error(request, 'Vous n\'avez pas les permissions pour supprimer une catégorie.')
        return redirect('ateliers:categorie_list')
    
    categorie = get_object_or_404(Categorie, pk=pk)
    
    # Vérifier les dépendances
    has_ateliers = AtelierCategorie.objects.filter(categorie=categorie).exists()
    has_collaborateurs = CollaborateurCategorie.objects.filter(categorie=categorie).exists()
    has_lancements = False
    try:
        if hasattr(categorie, 'lancement_set'):
            has_lancements = categorie.lancement_set.exists()
    except:
        pass
    
    can_delete = not (has_ateliers or has_collaborateurs or has_lancements)
    
    if request.method == 'POST':
        if not can_delete:
            messages.error(request, 
                'Cette catégorie ne peut pas être supprimée car elle est utilisée par d\'autres éléments.')
            return redirect('ateliers:categorie_detail', pk=pk)
        
        # Validation du formulaire
        delete_reason = request.POST.get('delete_reason')
        confirm_delete = request.POST.get('confirm_delete')
        
        if not delete_reason:
            messages.error(request, 'Veuillez sélectionner une raison pour la suppression.')
            return redirect('ateliers:categorie_delete', pk=pk)
        
        if not confirm_delete:
            messages.error(request, 'Veuillez confirmer la suppression.')
            return redirect('ateliers:categorie_delete', pk=pk)
        
        if delete_reason == 'autre':
            other_reason = request.POST.get('other_reason', '').strip()
            if not other_reason:
                messages.error(request, 'Veuillez préciser la raison de la suppression.')
                return redirect('ateliers:categorie_delete', pk=pk)
        
        try:
            nom_categorie = categorie.nom_categorie
            categorie.delete()
            messages.success(request, f"La catégorie '{nom_categorie}' a été supprimée avec succès.")
            return redirect('ateliers:categorie_list')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression : {str(e)}")
            return redirect('ateliers:categorie_detail', pk=pk)
    
    # Calculer les statistiques pour l'affichage
    stats = {
        'ateliers_count': AtelierCategorie.objects.filter(categorie=categorie).count(),
        'collaborateurs_count': CollaborateurCategorie.objects.filter(categorie=categorie).count(),
        'lancements_count': 0,
    }
    
    try:
        if hasattr(categorie, 'lancement_set'):
            stats['lancements_count'] = categorie.lancement_set.count()
    except:
        pass
    
    context = {
        'categorie': categorie,
        'has_ateliers': has_ateliers,
        'has_collaborateurs': has_collaborateurs,
        'has_lancements': has_lancements,
        'can_delete': can_delete,
        'stats': stats,
    }
    
    return render(request, 'categories/delete_confirm.html', context)