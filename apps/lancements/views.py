from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from datetime import datetime, timedelta
import calendar
import logging

from apps.core.utils.permissions import permission_required
from .models import Lancement
from .forms import LancementForm
from apps.ateliers.models import Atelier
from apps.core.models import Affaire
from apps.collaborateurs.models import Collaborateur

# Configuration du logger
logger = logging.getLogger(__name__)


@login_required
@permission_required('lancements', 'read')
def lancement_list(request):
    """
    Vue pour afficher la liste des lancements avec filtres et pagination
    """
    # Récupération des paramètres de filtrage
    search_query = request.GET.get('search', '')
    statut_filter = request.GET.get('statut', '')
    atelier_filter = request.GET.get('atelier', '')
    affaire_filter = request.GET.get('affaire', '')
    date_from = request.GET.get('date_from', '')
    
    # Construction de la requête de base
    lancements = Lancement.objects.select_related(
        'affaire', 'atelier', 'categorie', 'collaborateur'
    ).order_by('-date_lancement')
    
    # Application des filtres
    if search_query:
        lancements = lancements.filter(
            Q(num_lanc__icontains=search_query) |
            Q(sous_livrable__icontains=search_query) |
            Q(affaire__code_affaire__icontains=search_query) |
            Q(affaire__client__icontains=search_query)
        )
    
    if statut_filter:
        lancements = lancements.filter(statut=statut_filter)
    
    if atelier_filter:
        lancements = lancements.filter(atelier_id=atelier_filter)
    
    if affaire_filter:
        lancements = lancements.filter(affaire_id=affaire_filter)
    
    if date_from:
        lancements = lancements.filter(date_lancement__gte=date_from)
    
    # Calcul des statistiques
    stats = lancements.aggregate(
        total_lancements=Count('id'),
        en_cours=Count('id', filter=Q(statut='en_cours')),
        termines=Count('id', filter=Q(statut='termine')),
        poids_total=Sum('poids_debitage') + Sum('poids_assemblage') or 0
    )
    
    # Pagination
    paginator = Paginator(lancements, 20)  # 20 lancements par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    ateliers = Atelier.objects.all().order_by('nom_atelier')
    affaires = Affaire.objects.filter(statut__in=['en_cours', 'planifie']).order_by('code_affaire')
    
    # Vérification des permissions
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'statut_filter': statut_filter,
        'atelier_filter': atelier_filter,
        'affaire_filter': affaire_filter,
        'date_from': date_from,
        'ateliers': ateliers,
        'affaires': affaires,
        'stats': stats,
        'can_create': request.user.has_perm('lancements.add_lancement'),
        'can_update': request.user.has_perm('lancements.change_lancement'),
        'can_delete': request.user.has_perm('lancements.delete_lancement'),
    }
    
    return render(request, 'lancements/list.html', context)


@login_required
@permission_required('lancements', 'read')
def lancement_detail(request, pk):
    """
    Vue pour afficher les détails d'un lancement
    """
    lancement = get_object_or_404(
        Lancement.objects.select_related(
            'affaire', 'atelier', 'categorie', 'collaborateur'
        ), 
        pk=pk
    )
    
    context = {
        'lancement': lancement,
        'can_update': request.user.has_perm('lancements.change_lancement'),
        'can_delete': request.user.has_perm('lancements.delete_lancement'),
    }
    
    return render(request, 'lancements/detail.html', context)


@login_required
@permission_required('lancements', 'create')
def lancement_create(request):
    """
    Vue pour créer un nouveau lancement avec gestion d'erreurs détaillée
    """
    if request.method == 'POST':
        form = LancementForm(request.POST)
        try:
            if form.is_valid():
                lancement = form.save()
                messages.success(
                    request, 
                    f'✅ Le lancement {lancement.num_lanc} a été créé avec succès.'
                )
                logger.info(f"Nouveau lancement créé: {lancement.num_lanc} par {request.user}")
                return redirect('lancements:detail', pk=lancement.pk)
            else:
                # Analyse des erreurs pour fournir des messages plus explicites
                error_details = []
                
                # Erreurs par champ
                for field, errors in form.errors.items():
                    if field == '__all__':
                        for error in errors:
                            error_details.append(f"🔸 {error}")
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        for error in errors:
                            error_details.append(f"🔸 {field_label}: {error}")
                
                # Message d'erreur principal
                if error_details:
                    messages.error(
                        request, 
                        f"❌ Erreur lors de la création du lancement. Problèmes détectés :\n" + 
                        "\n".join(error_details[:5])  # Limiter à 5 erreurs pour l'affichage
                    )
                    if len(error_details) > 5:
                        messages.info(request, f"... et {len(error_details) - 5} autre(s) erreur(s)")
                else:
                    messages.error(
                        request, 
                        "❌ Erreur lors de la création du lancement. Veuillez vérifier les données saisies."
                    )
                
                logger.warning(f"Échec création lancement par {request.user}: {form.errors}")
                
        except Exception as e:
            # Gestion des erreurs non capturées par le formulaire
            messages.error(
                request, 
                f"❌ Erreur système lors de la création du lancement: {str(e)}"
            )
            logger.error(f"Erreur système création lancement par {request.user}: {str(e)}", exc_info=True)
    else:
        form = LancementForm()
    
    # Récupération des données pour les suggestions et l'aide
    context = {
        'form': form,
        'can_create': True,
        'ateliers_stats': Atelier.objects.annotate(
            nb_lancements=Count('lancements')
        ).order_by('-nb_lancements')[:5],
        'affaires_actives': Affaire.objects.filter(
            statut__in=['en_cours', 'planifie']
        ).count(),
    }
    
    return render(request, 'lancements/create.html', context)


@login_required
@permission_required('lancements', 'update')
def lancement_edit(request, pk):
    """
    Vue pour modifier un lancement existant avec gestion d'erreurs détaillée
    """
    lancement = get_object_or_404(Lancement, pk=pk)
    
    if request.method == 'POST':
        form = LancementForm(request.POST, instance=lancement)
        try:
            if form.is_valid():
                # Capture des valeurs avant modification pour comparaison
                old_values = {
                    'statut': lancement.statut,
                    'atelier': lancement.atelier.nom_atelier if lancement.atelier else None,
                    'collaborateur': lancement.collaborateur.get_full_name() if lancement.collaborateur else None,
                    'date_lancement': lancement.date_lancement,
                }
                
                updated_lancement = form.save()
                
                # Génération d'un message personnalisé selon les modifications
                changes = []
                if old_values['statut'] != updated_lancement.statut:
                    changes.append(f"Statut: {old_values['statut']} → {updated_lancement.get_statut_display()}")
                
                if old_values['atelier'] != (updated_lancement.atelier.nom_atelier if updated_lancement.atelier else None):
                    changes.append(f"Atelier: {old_values['atelier']} → {updated_lancement.atelier.nom_atelier if updated_lancement.atelier else 'Aucun'}")
                
                if old_values['collaborateur'] != (updated_lancement.collaborateur.get_full_name() if updated_lancement.collaborateur else None):
                    changes.append(f"Collaborateur: {old_values['collaborateur']} → {updated_lancement.collaborateur.get_full_name() if updated_lancement.collaborateur else 'Aucun'}")
                
                if old_values['date_lancement'] != updated_lancement.date_lancement:
                    changes.append(f"Date: {old_values['date_lancement'].strftime('%d/%m/%Y')} → {updated_lancement.date_lancement.strftime('%d/%m/%Y')}")
                
                # Message de succès avec détails des changements
                if changes:
                    messages.success(
                        request, 
                        f"✅ Lancement {updated_lancement.num_lanc} modifié avec succès.\n"
                        f"Modifications: {' | '.join(changes)}"
                    )
                else:
                    messages.success(
                        request, 
                        f"✅ Lancement {updated_lancement.num_lanc} mis à jour (aucun changement majeur détecté)."
                    )
                
                logger.info(f"Lancement {updated_lancement.num_lanc} modifié par {request.user}. Changements: {changes}")
                return redirect('lancements:detail', pk=updated_lancement.pk)
                
            else:
                # Analyse des erreurs pour fournir des messages plus explicites
                error_details = []
                
                # Erreurs par champ
                for field, errors in form.errors.items():
                    if field == '__all__':
                        for error in errors:
                            error_details.append(f"🔸 {error}")
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        for error in errors:
                            error_details.append(f"🔸 {field_label}: {error}")
                
                # Message d'erreur principal
                if error_details:
                    messages.error(
                        request, 
                        f"❌ Erreur lors de la modification du lancement {lancement.num_lanc}.\n"
                        f"Problèmes détectés :\n" + "\n".join(error_details[:5])
                    )
                    if len(error_details) > 5:
                        messages.info(request, f"... et {len(error_details) - 5} autre(s) erreur(s)")
                else:
                    messages.error(
                        request, 
                        f"❌ Erreur lors de la modification du lancement {lancement.num_lanc}. "
                        "Veuillez vérifier les données saisies."
                    )
                
                logger.warning(f"Échec modification lancement {lancement.num_lanc} par {request.user}: {form.errors}")
                
        except Exception as e:
            # Gestion des erreurs non capturées par le formulaire
            messages.error(
                request, 
                f"❌ Erreur système lors de la modification du lancement {lancement.num_lanc}: {str(e)}"
            )
            logger.error(f"Erreur système modification lancement {lancement.num_lanc} par {request.user}: {str(e)}", exc_info=True)
    else:
        form = LancementForm(instance=lancement)
    
    # Informations supplémentaires pour l'aide à la modification
    context = {
        'form': form,
        'lancement': lancement,
        'can_update': True,
        'modification_info': {
            'last_modified': lancement.updated_at,
            'created': lancement.created_at,
            'current_status': lancement.get_statut_display(),
        },
    }
    
    return render(request, 'lancements/edit.html', context)


@login_required
@permission_required('lancements', 'delete')
def lancement_delete(request, pk):
    """
    Vue pour supprimer un lancement avec confirmation
    """
    lancement = get_object_or_404(
        Lancement.objects.select_related(
            'affaire', 'atelier', 'categorie', 'collaborateur'
        ), 
        pk=pk
    )
    
    if request.method == 'POST':
        try:
            num_lanc = lancement.num_lanc
            affaire_code = lancement.affaire.code_affaire if lancement.affaire else "Aucune"
            
            lancement.delete()
            messages.success(
                request, 
                f'✅ Le lancement {num_lanc} (Affaire: {affaire_code}) a été supprimé définitivement.'
            )
            logger.info(f"Lancement {num_lanc} supprimé par {request.user}")
            return redirect('lancements:list')
            
        except Exception as e:
            messages.error(
                request,
                f"❌ Erreur lors de la suppression du lancement {lancement.num_lanc}: {str(e)}"
            )
            logger.error(f"Erreur suppression lancement {lancement.num_lanc} par {request.user}: {str(e)}", exc_info=True)
    
    context = {
        'lancement': lancement,
        'can_delete': True,
        'related_info': {
            'affaire': lancement.affaire.code_affaire if lancement.affaire else "Aucune",
            'atelier': lancement.atelier.nom_atelier if lancement.atelier else "Aucun",
            'collaborateur': lancement.collaborateur.get_full_name() if lancement.collaborateur else "Aucun",
            'poids_total': lancement.get_poids_total() if hasattr(lancement, 'get_poids_total') else 0,
        }
    }
    
    return render(request, 'lancements/delete_confirm.html', context)


@login_required
@permission_required('lancements', 'read')
def lancement_planning(request):
    """
    Vue pour afficher le planning des lancements sous forme de calendrier
    """
    # Récupération du mois/année courants ou depuis les paramètres
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    # Calcul des dates de début et fin du mois
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # Récupération des lancements du mois
    lancements = Lancement.objects.select_related(
        'affaire', 'atelier', 'categorie', 'collaborateur'
    ).filter(
        date_lancement__range=[first_day, last_day]
    ).order_by('date_lancement')
    
    # Statistiques du mois
    stats = {
        'total_month': lancements.count(),
        'en_cours_month': lancements.filter(statut='en_cours').count(),
        'termines_month': lancements.filter(statut='termine').count(),
        'planifies_month': lancements.filter(statut='planifie').count(),
        'poids_total_month': lancements.aggregate(
            total=Sum('poids_debitage') + Sum('poids_assemblage')
        )['total'] or 0
    }
    
    # Données pour les filtres
    ateliers = Atelier.objects.all().order_by('nom_atelier')
    collaborateurs = Collaborateur.objects.filter(is_active=True).order_by('nom_collaborateur')
    
    context = {
        'lancements': lancements,
        'current_month': first_day,
        'year': year,
        'month': month,
        'stats': stats,
        'ateliers': ateliers,
        'collaborateurs': collaborateurs,
        'can_create': request.user.has_perm('lancements.add_lancement'),
    }
    
    return render(request, 'lancements/planning.html', context)


@login_required
@permission_required('lancements', 'read')
def get_lancements_data(request):
    """
    API endpoint pour récupérer les données des lancements en JSON (pour le calendrier)
    """
    try:
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')
        
        if start_date and end_date:
            lancements = Lancement.objects.select_related(
                'affaire', 'atelier', 'collaborateur'
            ).filter(
                date_lancement__range=[start_date, end_date]
            )
        else:
            lancements = Lancement.objects.select_related(
                'affaire', 'atelier', 'collaborateur'
            ).all()
        
        events = []
        for lancement in lancements:
            try:
                poids_total = float(lancement.get_poids_total()) if hasattr(lancement, 'get_poids_total') else 0.0
            except (ValueError, TypeError):
                poids_total = 0.0
                
            events.append({
                'id': lancement.id,
                'title': lancement.num_lanc,
                'start': lancement.date_lancement.strftime('%Y-%m-%d'),
                'className': f'lancement-{lancement.statut}',
                'extendedProps': {
                    'num_lanc': lancement.num_lanc,
                    'affaire': lancement.affaire.code_affaire if lancement.affaire else '',
                    'client': lancement.affaire.client if lancement.affaire else '',
                    'atelier': lancement.atelier.nom_atelier if lancement.atelier else '',
                    'collaborateur': lancement.collaborateur.get_full_name() if lancement.collaborateur else '',
                    'statut': lancement.statut,
                    'statut_display': lancement.get_statut_display(),
                    'poids_total': poids_total,
                    'sous_livrable': (lancement.sous_livrable[:50] + '...' if len(lancement.sous_livrable) > 50 else lancement.sous_livrable) if lancement.sous_livrable else ''
                }
            })
        
        return JsonResponse(events, safe=False)
        
    except Exception as e:
        logger.error(f"Erreur API lancements data: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Erreur lors de la récupération des données: {str(e)}'}, status=500)


@login_required
@permission_required('lancements', 'update')
@require_POST
def update_lancement_status(request, pk):
    """
    Vue AJAX pour mettre à jour rapidement le statut d'un lancement
    """
    try:
        lancement = get_object_or_404(Lancement, pk=pk)
        new_status = request.POST.get('status')
        
        # Validation du statut
        valid_statuses = ['planifie', 'en_cours', 'termine', 'en_attente']
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False, 
                'error': f'Statut invalide: {new_status}. Statuts valides: {", ".join(valid_statuses)}'
            }, status=400)
        
        old_status = lancement.statut
        lancement.statut = new_status
        lancement.save(update_fields=['statut', 'updated_at'])
        
        logger.info(f"Statut lancement {lancement.num_lanc} modifié par {request.user}: {old_status} → {new_status}")
        
        return JsonResponse({
            'success': True,
            'message': f'Statut du lancement {lancement.num_lanc} modifié de "{old_status}" vers "{new_status}"',
            'new_status': new_status,
            'new_status_display': lancement.get_statut_display()
        })
        
    except Exception as e:
        logger.error(f"Erreur mise à jour statut lancement {pk} par {request.user}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False, 
            'error': f'Erreur lors de la mise à jour: {str(e)}'
        }, status=500)


@login_required
@permission_required('lancements', 'read')
def lancement_statistics(request):
    """
    Vue pour afficher les statistiques détaillées des lancements
    """
    try:
        # Statistiques générales
        total_lancements = Lancement.objects.count()
        
        # Répartition par statut
        statut_stats = Lancement.objects.values('statut').annotate(
            count=Count('id')
        ).order_by('statut')
        
        # Répartition par atelier
        atelier_stats = Lancement.objects.values(
            'atelier__nom_atelier'
        ).annotate(
            count=Count('id'),
            poids_total=Sum('poids_debitage') + Sum('poids_assemblage')
        ).order_by('-count')
        
        # Statistiques mensuelles (6 derniers mois)
        from django.db.models import Extract
        monthly_stats = []
        for i in range(6):
            date = timezone.now() - timedelta(days=30*i)
            month_data = Lancement.objects.filter(
                date_lancement__year=date.year,
                date_lancement__month=date.month
            ).aggregate(
                count=Count('id'),
                poids_total=Sum('poids_debitage') + Sum('poids_assemblage') or 0
            )
            monthly_stats.append({
                'month': date.strftime('%Y-%m'),
                'month_name': date.strftime('%B %Y'),
                'count': month_data['count'],
                'poids_total': month_data['poids_total']
            })
        
        context = {
            'total_lancements': total_lancements,
            'statut_stats': statut_stats,
            'atelier_stats': atelier_stats,
            'monthly_stats': reversed(monthly_stats),
        }
        
        return render(request, 'lancements/statistics.html', context)
        
    except Exception as e:
        messages.error(request, f"❌ Erreur lors du calcul des statistiques: {str(e)}")
        logger.error(f"Erreur statistiques lancements: {str(e)}", exc_info=True)
        return redirect('lancements:list')


@login_required
@permission_required('lancements', 'read')
def lancement_export(request):
    """
    Vue pour exporter les données des lancements (CSV, PDF, Excel)
    """
    try:
        format_type = request.GET.get('format', 'csv')
        
        # Récupération des lancements avec les mêmes filtres que la liste
        lancements = Lancement.objects.select_related(
            'affaire', 'atelier', 'categorie', 'collaborateur'
        ).all()
        
        if format_type == 'csv':
            import csv
            from django.http import HttpResponse
            
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="lancements.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Numéro', 'Affaire', 'Client', 'Atelier', 'Collaborateur',
                'Date Lancement', 'Statut', 'Poids Débitage', 'Poids Assemblage',
                'Poids Total', 'Date Création'
            ])
            
            for lancement in lancements:
                try:
                    poids_total = lancement.get_poids_total() if hasattr(lancement, 'get_poids_total') else 0
                except:
                    poids_total = 0
                    
                writer.writerow([
                    lancement.num_lanc or '',
                    lancement.affaire.code_affaire if lancement.affaire else '',
                    lancement.affaire.client if lancement.affaire else '',
                    lancement.atelier.nom_atelier if lancement.atelier else '',
                    lancement.collaborateur.get_full_name() if lancement.collaborateur else '',
                    lancement.date_lancement.strftime('%d/%m/%Y') if lancement.date_lancement else '',
                    lancement.get_statut_display(),
                    lancement.poids_debitage or 0,
                    lancement.poids_assemblage or 0,
                    poids_total,
                    lancement.created_at.strftime('%d/%m/%Y %H:%M') if lancement.created_at else ''
                ])
            
            logger.info(f"Export CSV de {lancements.count()} lancements par {request.user}")
            return response
        
        # Autres formats à implémenter (PDF, Excel)
        messages.warning(request, f'⚠️ Export en format {format_type} non encore implémenté.')
        return redirect('lancements:list')
        
    except Exception as e:
        messages.error(request, f"❌ Erreur lors de l'export: {str(e)}")
        logger.error(f"Erreur export lancements format {format_type}: {str(e)}", exc_info=True)
        return redirect('lancements:list')