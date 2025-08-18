from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, Avg, F
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
import json
import os
import tempfile
import csv
import xlsxwriter
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from django.conf import settings 
from io import BytesIO

from .models import RapportProduction
from apps.lancements.models import Lancement
from apps.ateliers.models import Atelier
from apps.collaborateurs.models import Collaborateur
from apps.core.models import Affaire
from apps.core.utils.permissions import permission_required


@login_required
@permission_required('rapports', 'read')
def rapports_list(request):
    """
    Vue pour afficher la liste des rapports de production
    """
    # Filtres
    type_filter = request.GET.get('type_rapport', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Requête de base
    rapports = RapportProduction.objects.all()

    # Application des filtres
    if type_filter:
        rapports = rapports.filter(type_rapport=type_filter)
    
    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
            rapports = rapports.filter(date_debut__gte=date_from_parsed)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
            rapports = rapports.filter(date_fin__lte=date_to_parsed)
        except ValueError:
            pass

    # Tri par date de création décroissante
    rapports = rapports.order_by('-created_at')

    # Pagination
    paginator = Paginator(rapports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistiques globales
    total_rapports = RapportProduction.objects.count()
    total_lancements = Lancement.objects.count()
    
    # Calcul du poids total
    lancements_aggregation = Lancement.objects.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    total_poids = (lancements_aggregation['total_debitage'] or 0) + (lancements_aggregation['total_assemblage'] or 0)
    
    try:
        rapport_recent = RapportProduction.objects.latest('created_at')
    except RapportProduction.DoesNotExist:
        rapport_recent = None

    context = {
        'page_obj': page_obj,
        'type_filter': type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_rapports': total_rapports,
        'total_lancements': total_lancements,
        'total_poids': total_poids,
        'rapport_recent': rapport_recent,
    }

    return render(request, 'reporting/rapports_list.html', context)


@login_required
@permission_required('rapports', 'read')
def rapport_detail(request, rapport_id):
    """
    Vue pour afficher les détails d'un rapport spécifique
    """
    rapport = get_object_or_404(RapportProduction, id=rapport_id)

    # Récupération des lancements pour la période du rapport
    lancements = Lancement.objects.filter(
        date_lancement__range=[rapport.date_debut, rapport.date_fin]
    )

    # Statistiques par atelier
    stats_ateliers = lancements.values(
        'atelier__id', 'atelier__nom_atelier', 'atelier__type_atelier'
    ).annotate(
        nb_lancements=Count('id'),
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )

    # Ajouter le poids total et calculer les pourcentages
    stats_ateliers_list = []
    total_poids_periode = 0
    
    for stat in stats_ateliers:
        debitage = stat['poids_debitage'] or 0
        assemblage = stat['poids_assemblage'] or 0
        poids_total = debitage + assemblage
        stat['poids_total'] = poids_total
        total_poids_periode += poids_total
        stats_ateliers_list.append(stat)

    # Tri par poids total décroissant
    stats_ateliers_list.sort(key=lambda x: x['poids_total'], reverse=True)

    # Calcul des pourcentages
    for stat in stats_ateliers_list:
        if total_poids_periode > 0:
            stat['pourcentage_poids'] = (stat['poids_total'] or 0) * 100 / total_poids_periode
        else:
            stat['pourcentage_poids'] = 0

    # Statistiques par collaborateur - SOLUTION SANS AVG SUR AGGREGATES
    # D'abord récupérer les données de base
    stats_collaborateurs_base = lancements.values(
        'collaborateur__id', 
        'collaborateur__nom_collaborateur', 
        'collaborateur__prenom_collaborateur'
    ).annotate(
        nb_lancements=Count('id'),
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )

    # Ensuite calculer les moyennes manuellement
    stats_collaborateurs_list = []
    for stat in stats_collaborateurs_base:
        # Calcul du poids total
        debitage = stat['poids_debitage'] or 0
        assemblage = stat['poids_assemblage'] or 0
        stat['poids_total'] = debitage + assemblage
        
        # Calcul des moyennes (poids total / nombre de lancements)
        if stat['nb_lancements'] > 0:
            stat['moyenne_debitage'] = debitage / stat['nb_lancements']
            stat['moyenne_assemblage'] = assemblage / stat['nb_lancements']
            stat['moyenne_poids'] = stat['poids_total'] / stat['nb_lancements']
        else:
            stat['moyenne_debitage'] = 0
            stat['moyenne_assemblage'] = 0
            stat['moyenne_poids'] = 0
        
        stats_collaborateurs_list.append(stat)

    # Tri par poids total décroissant
    stats_collaborateurs_list.sort(key=lambda x: x['poids_total'], reverse=True)

    # Calcul des pourcentages de performance pour les collaborateurs
    max_poids_collaborateur = 0
    for stat in stats_collaborateurs_list:
        if stat['poids_total'] and stat['poids_total'] > max_poids_collaborateur:
            max_poids_collaborateur = stat['poids_total']
    
    if max_poids_collaborateur == 0:
        max_poids_collaborateur = 1

    for stat in stats_collaborateurs_list:
        stat['pourcentage_performance'] = (stat['poids_total'] or 0) * 100 / max_poids_collaborateur

    # Statistiques par affaire
    stats_affaires = lancements.values(
        'affaire__id', 'affaire__code_affaire', 'affaire__client', 'affaire__statut'
    ).annotate(
        nb_lancements=Count('id'),
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )

    # Traitement des affaires
    stats_affaires_list = []
    for stat in stats_affaires:
        debitage = stat['poids_debitage'] or 0
        assemblage = stat['poids_assemblage'] or 0
        stat['poids_total'] = debitage + assemblage
        stats_affaires_list.append(stat)

    # Tri par poids total décroissant
    stats_affaires_list.sort(key=lambda x: x['poids_total'], reverse=True)

    # Statistiques générales
    stats = {
        'nb_ateliers': len(stats_ateliers_list),
        'nb_collaborateurs': len(stats_collaborateurs_list),
    }

    # Timeline des événements
    timeline_events = [
        {
            'title': f'{lancements.count()} lancements créés',
            'description': 'Lancements de la période',
            'date': rapport.date_debut,
            'color': '#28a745'
        }
    ]

    context = {
        'rapport': rapport,
        'stats': stats,
        'stats_ateliers': stats_ateliers_list,
        'stats_collaborateurs': stats_collaborateurs_list,
        'stats_affaires': stats_affaires_list,
        'timeline_events': timeline_events,
    }

    return render(request, 'reporting/rapport_detail.html', context)

@login_required
@permission_required('rapports', 'read')
def graphiques(request):
    """
    Vue pour les tableaux de bord avec graphiques
    Modifiée pour utiliser des dates de début/fin au lieu de périodes prédéfinies
    """
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Récupération des dates depuis les paramètres GET ou valeurs par défaut
    date_debut_str = request.GET.get('date_debut')
    date_fin_str = request.GET.get('date_fin')
    
    # Dates par défaut : 30 derniers jours
    if not date_debut_str or not date_fin_str:
        date_fin = timezone.now().date()
        date_debut = date_fin - timedelta(days=30)
    else:
        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        except ValueError:
            # En cas d'erreur de format, utiliser les dates par défaut
            date_fin = timezone.now().date()
            date_debut = date_fin - timedelta(days=30)
    
    # S'assurer que date_debut <= date_fin
    if date_debut > date_fin:
        date_debut, date_fin = date_fin, date_debut

    # Requête de base des lancements pour la période sélectionnée
    lancements = Lancement.objects.filter(
        date_lancement__range=[date_debut, date_fin]
    )

    # Statistiques du dashboard
    lancements_aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    poids_total_dashboard = (lancements_aggregation['total_debitage'] or 0) + (lancements_aggregation['total_assemblage'] or 0)

    # Calcul du nombre de jours d'analyse
    jours_analyse = (date_fin - date_debut).days + 1

    dashboard_stats = {
        'total_lancements': lancements.count(),
        'poids_total': poids_total_dashboard,
        'efficacite': 85.5,  # Simulation - vous pouvez calculer la vraie efficacité
        'delai_moyen': 5,  # Simulation - calculer le vrai délai moyen
        'completion_rate': 78.2,  # Simulation
    }

    # Top collaborateurs pour les graphiques - avec noms complets
    top_collaborateurs_data = lancements.values(
        'collaborateur__nom_collaborateur',
        'collaborateur__prenom_collaborateur'
    ).annotate(
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )

    # Traitement des top collaborateurs avec noms complets
    top_collaborateurs_list = []
    for collab in top_collaborateurs_data:
        debitage = collab['poids_debitage'] or 0
        assemblage = collab['poids_assemblage'] or 0
        poids_total = debitage + assemblage
        
        # Construction du nom complet
        nom_complet = f"{collab['collaborateur__prenom_collaborateur']} {collab['collaborateur__nom_collaborateur']}"
        
        collab_data = {
            'nom_collaborateur': nom_complet,
            'poids_debitage': debitage,
            'poids_assemblage': assemblage,
            'poids_total': poids_total
        }
        top_collaborateurs_list.append(collab_data)

    # Tri et limitation à 10 collaborateurs
    top_collaborateurs_list.sort(key=lambda x: x['poids_total'], reverse=True)
    top_collaborateurs = top_collaborateurs_list[:10]

    # Top affaires pour les graphiques
    top_affaires_data = lancements.values(
        'affaire__code_affaire'
    ).annotate(
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )

    # Traitement des top affaires
    top_affaires_list = []
    for affaire in top_affaires_data:
        debitage = affaire['poids_debitage'] or 0
        assemblage = affaire['poids_assemblage'] or 0
        poids_total = debitage + assemblage
        
        affaire_data = {
            'code_affaire': affaire['affaire__code_affaire'],
            'poids_total': poids_total
        }
        top_affaires_list.append(affaire_data)

    # Tri et limitation à 8 affaires
    top_affaires_list.sort(key=lambda x: x['poids_total'], reverse=True)
    top_affaires = top_affaires_list[:8]

    # Calcul des pourcentages pour les affaires
    total_poids_affaires = sum(affaire['poids_total'] for affaire in top_affaires)
    for affaire in top_affaires:
        if total_poids_affaires > 0:
            affaire['pourcentage'] = (affaire['poids_total'] / total_poids_affaires) * 100
        else:
            affaire['pourcentage'] = 0

    # Nouvelle analyse : Répartition par catégories (remplace l'évolution temporelle)
    repartition_categories = lancements.values(
        'categorie__nom_categorie'
    ).annotate(
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage'),
        nb_lancements=Count('id')
    )

    # Traitement des catégories
    categories_list = []
    for cat in repartition_categories:
        debitage = cat['poids_debitage'] or 0
        assemblage = cat['poids_assemblage'] or 0
        poids_total = debitage + assemblage
        
        cat_data = {
            'categorie__nom_categorie': cat['categorie__nom_categorie'],
            'poids_total': poids_total,
            'nb_lancements': cat['nb_lancements']
        }
        categories_list.append(cat_data)

    # Tri par poids total décroissant
    categories_list.sort(key=lambda x: x['poids_total'], reverse=True)

    # Performance des ateliers - CORRECTION DU RELATED_NAME
    performance_ateliers = Atelier.objects.annotate(
        nb_lancements=Count('lancements', filter=Q(
            lancements__date_lancement__range=[date_debut, date_fin]
        )),
        poids_debitage=Sum('lancements__poids_debitage', filter=Q(
            lancements__date_lancement__range=[date_debut, date_fin]
        )),
        poids_assemblage=Sum('lancements__poids_assemblage', filter=Q(
            lancements__date_lancement__range=[date_debut, date_fin]
        ))
    ).filter(nb_lancements__gt=0)

    # Traitement des performances des ateliers
    performance_ateliers_list = []
    for atelier in performance_ateliers:
        # Calcul du poids total
        debitage = atelier.poids_debitage or 0
        assemblage = atelier.poids_assemblage or 0
        atelier.poids_total = debitage + assemblage
        
        # Simulation d'efficacité basée sur le nombre de lancements et le poids
        base_efficacite = 70
        bonus_lancements = min(25, (atelier.nb_lancements or 0) * 2)
        bonus_poids = min(5, atelier.poids_total / 100)
        atelier.efficacite = min(95, base_efficacite + bonus_lancements + bonus_poids)
        
        performance_ateliers_list.append(atelier)

    # Tri par poids total décroissant
    performance_ateliers_list.sort(key=lambda x: x.poids_total, reverse=True)

    # Meilleur performer (atelier avec le plus gros poids)
    top_performer = performance_ateliers_list[0] if performance_ateliers_list else None

    # Top collaborateur (celui avec le plus gros poids total)
    top_collaborateur = top_collaborateurs[0] if top_collaborateurs else None

    # Top affaire (celle avec le plus gros pourcentage)
    top_affaire = top_affaires[0] if top_affaires else None

    # Tendance (simulation basée sur la comparaison avec la période précédente)
    # Calcul de la période précédente (même durée)
    duree_periode = (date_fin - date_debut).days + 1
    date_debut_precedente = date_debut - timedelta(days=duree_periode)
    date_fin_precedente = date_debut - timedelta(days=1)

    lancements_precedents = Lancement.objects.filter(
        date_lancement__range=[date_debut_precedente, date_fin_precedente]
    )
    
    precedent_aggregation = lancements_precedents.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    poids_total_precedent = (precedent_aggregation['total_debitage'] or 0) + (precedent_aggregation['total_assemblage'] or 0)

    # Calcul de la tendance
    if poids_total_precedent > 0:
        variation = ((float(poids_total_dashboard) - float(poids_total_precedent)) / float(poids_total_precedent)) * 100
        if variation > 5:
            trend = 'up'
            trend_percentage = variation
        elif variation < -5:
            trend = 'down'
            trend_percentage = abs(variation)
        else:
            trend = 'stable'
            trend_percentage = abs(variation)
    else:
        trend = 'up' if poids_total_dashboard > 0 else 'stable'
        trend_percentage = 0

    context = {
        # Données du dashboard
        'dashboard_stats': dashboard_stats,
        'top_collaborateurs': top_collaborateurs,
        'top_affaires': top_affaires,
        'repartition_categories': categories_list,
        'performance_ateliers': performance_ateliers_list,
        
        # Insights
        'top_performer': top_performer,
        'top_collaborateur': top_collaborateur,
        'top_affaire': top_affaire,
        'trend': trend,
        'trend_percentage': trend_percentage,
        
        # Paramètres de filtre
        'date_debut': date_debut,
        'date_fin': date_fin,
        'jours_analyse': jours_analyse,
    }

    return render(request, 'reporting/graphiques.html', context)


@login_required
@permission_required('rapports', 'read')
def export_page(request):
    """
    Vue pour la page d'export
    """
    # Données pour les sélecteurs
    ateliers = Atelier.objects.all().order_by('nom_atelier')
    collaborateurs = Collaborateur.objects.filter(is_active=True).order_by(
        'nom_collaborateur', 'prenom_collaborateur'
    )
    affaires = Affaire.objects.all().order_by('code_affaire')
    
    # Exports récents (simulation)
    recent_exports = []  # À implémenter avec un modèle d'historique d'exports
    
    # Statistiques d'export
    total_exports = 25  # Simulation
    
    context = {
        'ateliers': ateliers,
        'collaborateurs': collaborateurs,
        'affaires': affaires,
        'recent_exports': recent_exports,
        'total_exports': total_exports,
    }
    
    return render(request, 'reporting/export.html', context)


@login_required
@permission_required('rapports', 'export')
def process_export(request):
    """
    Traitement de l'export des données - Version mise à jour
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        # Récupération des paramètres
        format_export = request.POST.get('format')
        if not format_export:
            return JsonResponse({'success': False, 'error': 'Format d\'export requis'})
            
        date_debut_str = request.POST.get('date_debut')
        date_fin_str = request.POST.get('date_fin')
        
        if not date_debut_str or not date_fin_str:
            return JsonResponse({'success': False, 'error': 'Dates de début et fin requises'})
        
        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Format de date invalide'})
        
        # Filtres optionnels
        ateliers_ids = request.POST.getlist('ateliers')
        collaborateurs_ids = request.POST.getlist('collaborateurs')
        statuts = request.POST.getlist('statuts')
        affaires_ids = request.POST.getlist('affaires')
        
        # Options d'export
        include_graphics = request.POST.get('include_graphics') == 'on'
        include_stats = request.POST.get('include_stats') == 'on'
        detailed_data = request.POST.get('detailed_data') == 'on'
        send_email = request.POST.get('send_email') == 'on'
        email_address = request.POST.get('email_address', '')

        # Construction de la requête
        lancements = Lancement.objects.filter(
            date_lancement__range=[date_debut, date_fin]
        ).select_related('atelier', 'collaborateur', 'affaire', 'categorie')

        # Application des filtres
        if ateliers_ids:
            lancements = lancements.filter(atelier_id__in=ateliers_ids)
        if collaborateurs_ids:
            lancements = lancements.filter(collaborateur_id__in=collaborateurs_ids)
        if statuts:
            lancements = lancements.filter(statut__in=statuts)
        if affaires_ids:
            lancements = lancements.filter(affaire_id__in=affaires_ids)

        # Génération du fichier selon le format
        if format_export == 'excel':
            # Vérifier si c'est un export dashboard ou standard
            if include_stats and not detailed_data:
                return generate_dashboard_excel(lancements, date_debut, date_fin)
            else:
                result = generate_excel_export(
                    lancements, date_debut, date_fin, include_stats, detailed_data
                )
                return result['response']
        elif format_export == 'pdf':
            if include_graphics or include_stats:
                return generate_dashboard_pdf(lancements, date_debut, date_fin)
            else:
                result = generate_pdf_export(
                    lancements, date_debut, date_fin, include_graphics, include_stats
                )
                return result['response']
        elif format_export == 'csv':
            if include_stats and not detailed_data:
                return generate_dashboard_csv(lancements, date_debut, date_fin)
            else:
                result = generate_csv_export(lancements, detailed_data)
                return result['response']
        elif format_export == 'json':
            result = generate_json_export(lancements, detailed_data)
            return result['response']
        else:
            return JsonResponse({'success': False, 'error': 'Format non supporté'})

    except Exception as e:
        import traceback
        print(f"Erreur dans process_export: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': f'Erreur lors de l\'export: {str(e)}'})


# Fonctions utilitaires pour les exports des graphiques
@login_required 
@permission_required('rapports', 'export')
def export_charts(request):
    """
    Export des graphiques (placeholder - à implémenter selon vos besoins)
    """
    # Cette fonction peut être utilisée pour générer des images des graphiques
    # ou rediriger vers d'autres types d'exports
    
    messages.info(request, 'Utilisez les boutons "Exporter PNG" ou "Exporter PDF" sur la page des graphiques.')
    return redirect('reporting:graphiques')


@login_required
@permission_required('rapports', 'export') 
def export_detailed_charts(request):
    """
    Export détaillé des graphiques (placeholder)
    """
    messages.info(request, 'Export détaillé des graphiques en cours de développement.')
    return redirect('reporting:graphiques')


# Fonction pour améliorer la gestion des erreurs d'export
def handle_export_error(request, error_message, redirect_url='reporting:export'):
    """
    Gestion centralisée des erreurs d'export
    """
    messages.error(request, f'Erreur d\'export: {error_message}')
    return redirect(redirect_url)


def generate_excel_export(lancements, date_debut, date_fin, include_stats, detailed_data):
    """
    Génération d'un fichier Excel
    """
    # Création d'un fichier temporaire
    output = BytesIO()
    
    workbook = xlsxwriter.Workbook(output)
    
    # Styles
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'border': 1
    })
    
    data_format = workbook.add_format({
        'border': 1,
        'align': 'left'
    })
    
    number_format = workbook.add_format({
        'border': 1,
        'num_format': '#,##0.00'
    })

    # Feuille principale - Données des lancements
    worksheet = workbook.add_worksheet('Lancements')
    
    # En-têtes
    headers = [
        'Numéro Lancement', 'Date Lancement', 'Date Réception', 
        'Affaire', 'Client', 'Sous-livrable', 'Atelier', 'Type Atelier',
        'Collaborateur', 'Catégorie', 'Poids Débitage', 'Poids Assemblage',
        'Poids Total', 'Statut', 'Observations'
    ]
    
    # Écriture des en-têtes
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # Écriture des données
    for row, lancement in enumerate(lancements, 1):
        worksheet.write(row, 0, lancement.num_lanc, data_format)
        worksheet.write(row, 1, lancement.date_lancement.strftime('%d/%m/%Y'), data_format)
        worksheet.write(row, 2, lancement.date_reception.strftime('%d/%m/%Y'), data_format)
        worksheet.write(row, 3, lancement.affaire.code_affaire, data_format)
        worksheet.write(row, 4, lancement.affaire.client, data_format)
        worksheet.write(row, 5, lancement.sous_livrable, data_format)
        worksheet.write(row, 6, lancement.atelier.nom_atelier, data_format)
        worksheet.write(row, 7, lancement.atelier.get_type_atelier_display(), data_format)
        worksheet.write(row, 8, lancement.collaborateur.get_full_name(), data_format)
        worksheet.write(row, 9, lancement.categorie.nom_categorie, data_format)
        worksheet.write(row, 10, float(lancement.poids_debitage), number_format)
        worksheet.write(row, 11, float(lancement.poids_assemblage), number_format)
        worksheet.write(row, 12, float(lancement.get_poids_total()), number_format)
        worksheet.write(row, 13, lancement.get_statut_display(), data_format)
        worksheet.write(row, 14, lancement.observations or '', data_format)

    # Ajustement de la largeur des colonnes
    worksheet.set_column('A:O', 15)

    # Feuille statistiques si demandée
    if include_stats:
        stats_worksheet = workbook.add_worksheet('Statistiques')
        
        # Statistiques globales
        stats_worksheet.write('A1', 'Période d\'analyse', header_format)
        stats_worksheet.write('B1', f'{date_debut.strftime("%d/%m/%Y")} - {date_fin.strftime("%d/%m/%Y")}', data_format)
        
        stats_worksheet.write('A2', 'Nombre total de lancements', header_format)
        stats_worksheet.write('B2', lancements.count(), data_format)
        
        # Calcul du poids total
        total_poids = sum(l.get_poids_total() for l in lancements)
        
        stats_worksheet.write('A3', 'Poids total traité (kg)', header_format)
        stats_worksheet.write('B3', total_poids, number_format)
        
        # Statistiques par atelier
        stats_worksheet.write('A5', 'Statistiques par Atelier', header_format)
        stats_worksheet.write('A6', 'Atelier', header_format)
        stats_worksheet.write('B6', 'Nb Lancements', header_format)
        stats_worksheet.write('C6', 'Poids Total', header_format)
        
        ateliers_stats = {}
        for lancement in lancements:
            atelier = lancement.atelier.nom_atelier
            if atelier not in ateliers_stats:
                ateliers_stats[atelier] = {'nb': 0, 'poids': 0}
            ateliers_stats[atelier]['nb'] += 1
            ateliers_stats[atelier]['poids'] += lancement.get_poids_total()
        
        row = 7
        for atelier, stats in ateliers_stats.items():
            stats_worksheet.write(row, 0, atelier, data_format)
            stats_worksheet.write(row, 1, stats['nb'], data_format)
            stats_worksheet.write(row, 2, stats['poids'], number_format)
            row += 1

    workbook.close()
    output.seek(0)
    
    # Création de la réponse HTTP
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'export_lancements_{date_debut}_{date_fin}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return {'response': response, 'filename': filename}


def generate_pdf_export(lancements, date_debut, date_fin, include_graphics, include_stats):
    """
    Génération d'un fichier PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Titre
    title_style = styles['Title']
    story.append(Paragraph(f"Rapport de Production - {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}", title_style))
    story.append(Spacer(1, 12))

    # Statistiques si demandées
    if include_stats:
        story.append(Paragraph("Statistiques Générales", styles['Heading2']))
        
        # Calcul du poids total
        total_poids = sum(l.get_poids_total() for l in lancements)
        
        stats_data = [
            ['Métrique', 'Valeur'],
            ['Nombre de lancements', str(lancements.count())],
            ['Poids total traité', f'{total_poids:.2f} kg'],
            ['Période', f'{date_debut.strftime("%d/%m/%Y")} - {date_fin.strftime("%d/%m/%Y")}']
        ]
        
        stats_table = Table(stats_data)
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 12))

    # Tableau des lancements
    story.append(Paragraph("Détail des Lancements", styles['Heading2']))
    
    # Données du tableau (limitées pour le PDF)
    table_data = [['N° Lanc.', 'Date', 'Affaire', 'Atelier', 'Collaborateur', 'Poids Total']]
    
    for lancement in lancements[:50]:  # Limiter à 50 pour le PDF
        table_data.append([
            lancement.num_lanc,
            lancement.date_lancement.strftime('%d/%m/%Y'),
            lancement.affaire.code_affaire,
            lancement.atelier.nom_atelier,
            lancement.collaborateur.get_full_name()[:20],
            f'{lancement.get_poids_total():.1f} kg'
        ])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8)
    ]))
    
    story.append(table)
    
    if lancements.count() > 50:
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"... et {lancements.count() - 50} autres lancements", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    filename = f'rapport_production_{date_debut}_{date_fin}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return {'response': response, 'filename': filename}


def generate_csv_export(lancements, detailed_data):
    """
    Génération d'un fichier CSV
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="export_lancements.csv"'
    
    # Ajout du BOM pour Excel
    response.write('\ufeff')
    
    writer = csv.writer(response, delimiter=';')
    
    # En-têtes
    headers = [
        'Numéro Lancement', 'Date Lancement', 'Date Réception',
        'Code Affaire', 'Client', 'Sous-livrable', 'Atelier',
        'Collaborateur', 'Catégorie', 'Poids Débitage',
        'Poids Assemblage', 'Poids Total', 'Statut'
    ]
    
    if detailed_data:
        headers.extend(['Type Atelier', 'Observations', 'Date Création'])
    
    writer.writerow(headers)
    
    # Données
    for lancement in lancements:
        row = [
            lancement.num_lanc,
            lancement.date_lancement.strftime('%d/%m/%Y'),
            lancement.date_reception.strftime('%d/%m/%Y'),
            lancement.affaire.code_affaire,
            lancement.affaire.client,
            lancement.sous_livrable,
            lancement.atelier.nom_atelier,
            lancement.collaborateur.get_full_name(),
            lancement.categorie.nom_categorie,
            str(lancement.poids_debitage).replace('.', ','),
            str(lancement.poids_assemblage).replace('.', ','),
            str(lancement.get_poids_total()).replace('.', ','),
            lancement.get_statut_display()
        ]
        
        if detailed_data:
            row.extend([
                lancement.atelier.get_type_atelier_display(),
                lancement.observations or '',
                lancement.created_at.strftime('%d/%m/%Y %H:%M')
            ])
        
        writer.writerow(row)
    
    return {'response': response, 'filename': 'export_lancements.csv'}


def generate_json_export(lancements, detailed_data):
    """
    Génération d'un fichier JSON
    """
    data = []
    
    for lancement in lancements:
        item = {
            'numero_lancement': lancement.num_lanc,
            'date_lancement': lancement.date_lancement.isoformat(),
            'date_reception': lancement.date_reception.isoformat(),
            'affaire': {
                'code': lancement.affaire.code_affaire,
                'client': lancement.affaire.client
            },
            'sous_livrable': lancement.sous_livrable,
            'atelier': {
                'nom': lancement.atelier.nom_atelier,
                'type': lancement.atelier.type_atelier
            },
            'collaborateur': {
                'nom': lancement.collaborateur.nom_collaborateur,
                'prenom': lancement.collaborateur.prenom_collaborateur
            },
            'categorie': lancement.categorie.nom_categorie,
            'poids': {
                'debitage': float(lancement.poids_debitage),
                'assemblage': float(lancement.poids_assemblage),
                'total': float(lancement.get_poids_total())
            },
            'statut': lancement.statut
        }
        
        if detailed_data:
            item.update({
                'observations': lancement.observations,
                'date_creation': lancement.created_at.isoformat(),
                'date_modification': lancement.updated_at.isoformat()
            })
        
        data.append(item)
    
    json_data = json.dumps(data, ensure_ascii=False, indent=2)
    
    response = HttpResponse(json_data, content_type='application/json; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="export_lancements.json"'
    
    return {'response': response, 'filename': 'export_lancements.json'}


@login_required
@permission_required('rapports', 'create')
@require_http_methods(["POST"])
def generate_rapport(request):
    """
    Génération d'un nouveau rapport de production
    """
    try:
        type_rapport = request.POST.get('type_rapport')
        date_debut = datetime.strptime(request.POST.get('date_debut'), '%Y-%m-%d').date()
        date_fin = datetime.strptime(request.POST.get('date_fin'), '%Y-%m-%d').date()

        # Calcul des métriques - Correction
        lancements = Lancement.objects.filter(
            date_lancement__range=[date_debut, date_fin]
        )
        
        nb_lancements = lancements.count()
        
        # Calcul correct du poids total
        lancements_aggregation = lancements.aggregate(
            total_debitage=Sum('poids_debitage'),
            total_assemblage=Sum('poids_assemblage')
        )
        poids_total = (lancements_aggregation['total_debitage'] or 0) + (lancements_aggregation['total_assemblage'] or 0)

        # Création du rapport
        rapport = RapportProduction.objects.create(
            date_debut=date_debut,
            date_fin=date_fin,
            type_rapport=type_rapport,
            nb_lancements=nb_lancements,
            poids_total=poids_total
        )

        messages.success(request, f'Rapport {type_rapport} généré avec succès.')
        return redirect('reporting:rapport_detail', rapport_id=rapport.id)

    except Exception as e:
        messages.error(request, f'Erreur lors de la génération du rapport: {str(e)}')
        return redirect('reporting:rapports_list')


@login_required
@require_http_methods(["DELETE"])
def delete_rapport(request, rapport_id):
    """
    Suppression d'un rapport
    """
    try:
        rapport = get_object_or_404(RapportProduction, id=rapport_id)
        rapport.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Vues pour les téléchargements
@login_required
@permission_required('rapports', 'export')
def download_excel(request):
    """
    Vue pour télécharger le dernier export Excel
    """
    # Cette vue peut être utilisée pour servir des fichiers Excel temporaires
    # ou rediriger vers process_export avec format=excel
    return redirect('reporting:process_export')


@login_required
@permission_required('rapports', 'export')
def download_pdf(request):
    """
    Vue pour télécharger le dernier export PDF
    """
    return redirect('reporting:process_export')


@login_required
@permission_required('rapports', 'export')
def download_csv(request):
    """
    Vue pour télécharger le dernier export CSV
    """
    return redirect('reporting:process_export')


@login_required
@permission_required('rapports', 'export')
def download_json(request):
    """
    Vue pour télécharger le dernier export JSON
    """
    return redirect('reporting:process_export')


# API pour les données du dashboard
@login_required
@permission_required('rapports', 'read')
def dashboard_data_api(request):
    """
    API pour récupérer les données du dashboard
    """
    # Paramètres
    periode = int(request.GET.get('periode', 30))
    date_fin = timezone.now().date()
    date_debut = date_fin - timedelta(days=periode)

    # Requête des lancements
    lancements = Lancement.objects.filter(
        date_lancement__range=[date_debut, date_fin]
    )

    # Correction pour le calcul du poids total
    lancements_aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    poids_total = (lancements_aggregation['total_debitage'] or 0) + (lancements_aggregation['total_assemblage'] or 0)

    # Données du dashboard
    data = {
        'total_lancements': lancements.count(),
        'poids_total': float(poids_total),
        'efficacite': 85.5,  # Simulation
        'delai_moyen': 5,    # Simulation
    }

    return JsonResponse(data)


@login_required
@permission_required('rapports', 'read')
def chart_data_api(request, chart_type):
    """
    API pour récupérer des données spécifiques de graphiques
    """
    periode = int(request.GET.get('periode', 30))
    date_fin = timezone.now().date()
    date_debut = date_fin - timedelta(days=periode)

    lancements = Lancement.objects.filter(
        date_lancement__range=[date_debut, date_fin]
    )

    if chart_type == 'ateliers':
        # Correction pour les données des ateliers
        data = list(lancements.values('atelier__nom_atelier').annotate(
            count=Count('id'),
            poids_debitage=Sum('poids_debitage'),
            poids_assemblage=Sum('poids_assemblage')
        ).annotate(
            poids=F('poids_debitage') + F('poids_assemblage')
        ))
    elif chart_type == 'collaborateurs':
        # Correction pour les données des collaborateurs
        data = list(lancements.values(
            'collaborateur__nom_collaborateur',
            'collaborateur__prenom_collaborateur'
        ).annotate(
            count=Count('id'),
            poids_debitage=Sum('poids_debitage'),
            poids_assemblage=Sum('poids_assemblage')
        ).annotate(
            poids=F('poids_debitage') + F('poids_assemblage')
        )[:10])
    else:
        data = []

    return JsonResponse({'data': data})


@login_required
@permission_required('rapports', 'export')
def export_dashboard(request):
    """
    Export du dashboard complet
    """
    messages.info(request, 'Export du dashboard en cours de développement.')
    return redirect('reporting:graphiques')


@login_required
@permission_required('rapports', 'export')
def export_charts(request):
    """
    Export des graphiques
    """
    messages.info(request, 'Export des graphiques en cours de développement.')
    return redirect('reporting:graphiques')


@login_required
@permission_required('rapports', 'export')
def export_detailed_charts(request):
    """
    Export détaillé des graphiques
    """
    messages.info(request, 'Export détaillé en cours de développement.')
    return redirect('reporting:graphiques')


@login_required
@permission_required('rapports', 'create')
def regenerate_rapport(request, rapport_id):
    """
    Régénérer un rapport existant
    """
    rapport = get_object_or_404(RapportProduction, id=rapport_id)
    
    # Recalcul des métriques - Correction
    lancements = Lancement.objects.filter(
        date_lancement__range=[rapport.date_debut, rapport.date_fin]
    )
    
    rapport.nb_lancements = lancements.count()
    
    # Correction pour le calcul du poids total
    lancements_aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    rapport.poids_total = (lancements_aggregation['total_debitage'] or 0) + (lancements_aggregation['total_assemblage'] or 0)
    rapport.save()
    
    messages.success(request, 'Rapport régénéré avec succès.')
    return redirect('reporting:rapport_detail', rapport_id=rapport.id)


@login_required
@permission_required('rapports', 'read')
def download_rapport_pdf(request, rapport_id):
    """
    Télécharger un rapport spécifique en PDF avec tableau détaillé
    """
    rapport = get_object_or_404(RapportProduction, id=rapport_id)

    # Récupérer les lancements de la période
    lancements = Lancement.objects.filter(
        date_lancement__range=[rapport.date_debut, rapport.date_fin]
    ).select_related('atelier', 'collaborateur', 'affaire', 'categorie')

    # Générer le PDF avec le nouveau format
    return generate_rapport_pdf(lancements, rapport.date_debut, rapport.date_fin)

@login_required
@permission_required('rapports', 'read')
def download_rapport_excel(request, rapport_id):
    """
    Télécharger un rapport spécifique en Excel avec tableau détaillé
    """
    rapport = get_object_or_404(RapportProduction, id=rapport_id)

    # Récupérer les lancements de la période
    lancements = Lancement.objects.filter(
        date_lancement__range=[rapport.date_debut, rapport.date_fin]
    ).select_related('atelier', 'collaborateur', 'affaire', 'categorie')

    # Générer l'Excel avec le nouveau format
    return generate_rapport_excel(lancements, rapport.date_debut, rapport.date_fin)

# Ajoutez aussi cette vue pour le CSV des rapports
@login_required
@permission_required('rapports', 'read')
def download_rapport_csv(request, rapport_id):
    """
    Télécharger un rapport spécifique en CSV avec tableau détaillé
    """
    rapport = get_object_or_404(RapportProduction, id=rapport_id)

    # Récupérer les lancements de la période
    lancements = Lancement.objects.filter(
        date_lancement__range=[rapport.date_debut, rapport.date_fin]
    ).select_related('atelier', 'collaborateur', 'affaire', 'categorie')

    # Générer le CSV avec le nouveau format
    return generate_rapport_csv(lancements, rapport.date_debut, rapport.date_fin)

@login_required
@permission_required('rapports', 'delete')
@require_http_methods(["DELETE"])
def delete_export_history(request, export_id):
    """
    Supprimer un historique d'export (à implémenter avec un modèle)
    """
    # Placeholder pour la suppression d'historique d'exports
    # Vous devrez créer un modèle ExportHistory si nécessaire
    return JsonResponse({
        'success': True, 
        'message': 'Historique supprimé (fonctionnalité à implémenter)'
    })
# Ajoutez ces vues à votre fichier views.py existant

@login_required
@permission_required('rapports', 'export')
def export_dashboard_data(request):
    """
    Export spécifique pour les données du dashboard
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        format_export = request.POST.get('format', 'excel')
        date_debut_str = request.POST.get('date_debut')
        date_fin_str = request.POST.get('date_fin')
        
        if not date_debut_str or not date_fin_str:
            return JsonResponse({'success': False, 'error': 'Dates requises'})
        
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        
        # Récupération des données
        lancements = Lancement.objects.filter(
            date_lancement__range=[date_debut, date_fin]
        ).select_related('atelier', 'collaborateur', 'affaire', 'categorie')
        
        # Export selon le format demandé
        if format_export == 'excel':
            return generate_dashboard_excel(lancements, date_debut, date_fin)
        elif format_export == 'pdf':
            return generate_dashboard_pdf(lancements, date_debut, date_fin)
        elif format_export == 'csv':
            return generate_dashboard_csv(lancements, date_debut, date_fin)
        else:
            return JsonResponse({'success': False, 'error': 'Format non supporté'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erreur: {str(e)}'})


def generate_dashboard_excel(lancements, date_debut, date_fin):
    """
    Génération Excel spécifique pour le dashboard
    """
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    
    # Styles
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'border': 1,
        'align': 'center'
    })
    
    data_format = workbook.add_format({'border': 1})
    number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
    
    # Feuille principale - Résumé du dashboard
    worksheet = workbook.add_worksheet('Dashboard')
    
    # En-tête du rapport
    worksheet.write('A1', 'TABLEAU DE BORD - ANALYTICS DE PRODUCTION', header_format)
    worksheet.merge_range('A1:E1', 'TABLEAU DE BORD - ANALYTICS DE PRODUCTION', header_format)
    worksheet.write('A2', f'Période: {date_debut.strftime("%d/%m/%Y")} - {date_fin.strftime("%d/%m/%Y")}', data_format)
    worksheet.merge_range('A2:E2', f'Période: {date_debut.strftime("%d/%m/%Y")} - {date_fin.strftime("%d/%m/%Y")}', data_format)
    
    # Statistiques globales
    row = 4
    worksheet.write(row, 0, 'STATISTIQUES GÉNÉRALES', header_format)
    worksheet.merge_range(f'A{row+1}:B{row+1}', 'STATISTIQUES GÉNÉRALES', header_format)
    
    # Calculs des statistiques
    total_lancements = lancements.count()
    aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    poids_total = (aggregation['total_debitage'] or 0) + (aggregation['total_assemblage'] or 0)
    
    stats_data = [
        ['Nombre total de lancements', total_lancements],
        ['Poids total débitage (kg)', float(aggregation['total_debitage'] or 0)],
        ['Poids total assemblage (kg)', float(aggregation['total_assemblage'] or 0)],
        ['Poids total traité (kg)', float(poids_total)],
        ['Nombre de jours analysés', (date_fin - date_debut).days + 1]
    ]
    
    row = 6
    for stat in stats_data:
        worksheet.write(row, 0, stat[0], data_format)
        if isinstance(stat[1], (int, float)):
            worksheet.write(row, 1, stat[1], number_format if isinstance(stat[1], float) else data_format)
        else:
            worksheet.write(row, 1, stat[1], data_format)
        row += 1
    
    # Top collaborateurs
    row += 2
    worksheet.write(row, 0, 'TOP COLLABORATEURS', header_format)
    worksheet.merge_range(f'A{row+1}:D{row+1}', 'TOP COLLABORATEURS', header_format)
    
    # En-têtes collaborateurs
    row += 1
    collab_headers = ['Collaborateur', 'Poids Débitage', 'Poids Assemblage', 'Total']
    for col, header in enumerate(collab_headers):
        worksheet.write(row, col, header, header_format)
    
    # Données collaborateurs
    collab_data = lancements.values(
        'collaborateur__nom_collaborateur',
        'collaborateur__prenom_collaborateur'
    ).annotate(
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )
    
    collab_list = []
    for collab in collab_data:
        debitage = float(collab['poids_debitage'] or 0)
        assemblage = float(collab['poids_assemblage'] or 0)
        nom_complet = f"{collab['collaborateur__prenom_collaborateur']} {collab['collaborateur__nom_collaborateur']}"
        collab_list.append({
            'nom': nom_complet,
            'debitage': debitage,
            'assemblage': assemblage,
            'total': debitage + assemblage
        })
    
    collab_list.sort(key=lambda x: x['total'], reverse=True)
    
    row += 1
    for collab in collab_list[:10]:  # Top 10
        worksheet.write(row, 0, collab['nom'], data_format)
        worksheet.write(row, 1, collab['debitage'], number_format)
        worksheet.write(row, 2, collab['assemblage'], number_format)
        worksheet.write(row, 3, collab['total'], number_format)
        row += 1
    
    # Top affaires
    row += 2
    worksheet.write(row, 0, 'TOP AFFAIRES', header_format)
    worksheet.merge_range(f'A{row+1}:C{row+1}', 'TOP AFFAIRES', header_format)
    
    row += 1
    affaire_headers = ['Code Affaire', 'Poids Total', 'Pourcentage']
    for col, header in enumerate(affaire_headers):
        worksheet.write(row, col, header, header_format)
    
    # Données affaires
    affaire_data = lancements.values('affaire__code_affaire').annotate(
        poids_total=Sum('poids_debitage') + Sum('poids_assemblage')
    )
    
    affaire_list = []
    total_affaires = 0
    for affaire in affaire_data:
        poids = float(affaire['poids_total'] or 0)
        affaire_list.append({
            'code': affaire['affaire__code_affaire'],
            'poids': poids
        })
        total_affaires += poids
    
    affaire_list.sort(key=lambda x: x['poids'], reverse=True)
    
    row += 1
    for affaire in affaire_list[:8]:  # Top 8
        pourcentage = (affaire['poids'] / total_affaires * 100) if total_affaires > 0 else 0
        worksheet.write(row, 0, affaire['code'], data_format)
        worksheet.write(row, 1, affaire['poids'], number_format)
        worksheet.write(row, 2, f"{pourcentage:.1f}%", data_format)
        row += 1
    
    # Ajustement des largeurs de colonnes
    worksheet.set_column('A:A', 25)
    worksheet.set_column('B:D', 15)
    
    workbook.close()
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'dashboard_{date_debut}_{date_fin}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def generate_dashboard_pdf(lancements, date_debut, date_fin):
    """
    Génération PDF spécifique pour le dashboard
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Titre principal
    title_style = styles['Title']
    story.append(Paragraph("TABLEAU DE BORD - ANALYTICS DE PRODUCTION", title_style))
    story.append(Paragraph(f"Période: {date_debut.strftime('%d/%m/%Y')} - {date_fin.strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Spacer(1, 20))

    # Statistiques générales
    story.append(Paragraph("STATISTIQUES GÉNÉRALES", styles['Heading2']))
    
    total_lancements = lancements.count()
    aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    poids_total = (aggregation['total_debitage'] or 0) + (aggregation['total_assemblage'] or 0)
    
    stats_data = [
        ['Métrique', 'Valeur'],
        ['Nombre de lancements', str(total_lancements)],
        ['Poids débitage', f"{float(aggregation['total_debitage'] or 0):.2f} kg"],
        ['Poids assemblage', f"{float(aggregation['total_assemblage'] or 0):.2f} kg"],
        ['Poids total', f"{float(poids_total):.2f} kg"],
        ['Durée d\'analyse', f"{(date_fin - date_debut).days + 1} jour(s)"]
    ]
    
    stats_table = Table(stats_data)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(stats_table)
    story.append(Spacer(1, 20))

    # Top Collaborateurs
    story.append(Paragraph("TOP COLLABORATEURS", styles['Heading2']))
    
    collab_data = lancements.values(
        'collaborateur__nom_collaborateur',
        'collaborateur__prenom_collaborateur'
    ).annotate(
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )
    
    collab_table_data = [['Collaborateur', 'Débitage (kg)', 'Assemblage (kg)', 'Total (kg)']]
    
    collab_list = []
    for collab in collab_data:
        debitage = float(collab['poids_debitage'] or 0)
        assemblage = float(collab['poids_assemblage'] or 0)
        nom_complet = f"{collab['collaborateur__prenom_collaborateur']} {collab['collaborateur__nom_collaborateur']}"
        collab_list.append({
            'nom': nom_complet,
            'debitage': debitage,
            'assemblage': assemblage,
            'total': debitage + assemblage
        })
    
    collab_list.sort(key=lambda x: x['total'], reverse=True)
    
    for collab in collab_list[:10]:
        collab_table_data.append([
            collab['nom'],
            f"{collab['debitage']:.1f}",
            f"{collab['assemblage']:.1f}",
            f"{collab['total']:.1f}"
        ])
    
    collab_table = Table(collab_table_data)
    collab_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(collab_table)
    story.append(Spacer(1, 20))

    doc.build(story)
    buffer.seek(0)
    
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    filename = f'dashboard_{date_debut}_{date_fin}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def generate_dashboard_csv(lancements, date_debut, date_fin):
    """
    Génération CSV spécifique pour le dashboard
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f'dashboard_{date_debut}_{date_fin}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # BOM pour Excel
    response.write('\ufeff')
    
    writer = csv.writer(response, delimiter=';')
    
    # En-tête
    writer.writerow([f'DASHBOARD - {date_debut} à {date_fin}'])
    writer.writerow([])
    
    # Statistiques générales
    writer.writerow(['STATISTIQUES GENERALES'])
    total_lancements = lancements.count()
    aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    
    writer.writerow(['Nombre de lancements', total_lancements])
    writer.writerow(['Poids débitage (kg)', str(aggregation['total_debitage'] or 0).replace('.', ',')])
    writer.writerow(['Poids assemblage (kg)', str(aggregation['total_assemblage'] or 0).replace('.', ',')])
    writer.writerow([])
    
    # Collaborateurs
    writer.writerow(['TOP COLLABORATEURS'])
    writer.writerow(['Collaborateur', 'Poids Débitage', 'Poids Assemblage', 'Total'])
    
    collab_data = lancements.values(
        'collaborateur__nom_collaborateur',
        'collaborateur__prenom_collaborateur'
    ).annotate(
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )
    
    collab_list = []
    for collab in collab_data:
        debitage = float(collab['poids_debitage'] or 0)
        assemblage = float(collab['poids_assemblage'] or 0)
        nom_complet = f"{collab['collaborateur__prenom_collaborateur']} {collab['collaborateur__nom_collaborateur']}"
        collab_list.append({
            'nom': nom_complet,
            'debitage': debitage,
            'assemblage': assemblage,
            'total': debitage + assemblage
        })
    
    collab_list.sort(key=lambda x: x['total'], reverse=True)
    
    for collab in collab_list[:10]:
        writer.writerow([
            collab['nom'],
            str(collab['debitage']).replace('.', ','),
            str(collab['assemblage']).replace('.', ','),
            str(collab['total']).replace('.', ',')
        ])
    
    return response


# Ajoutez ces nouvelles vues à votre fichier views.py

@login_required
@permission_required('rapports', 'export')
def process_rapport_export(request):
    """
    Traitement de l'export spécifique pour les rapports détaillés
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

    try:
        # Récupération des paramètres
        format_export = request.POST.get('format')
        if not format_export:
            return JsonResponse({'success': False, 'error': 'Format d\'export requis'})

        date_debut_str = request.POST.get('date_debut')
        date_fin_str = request.POST.get('date_fin')

        if not date_debut_str or not date_fin_str:
            return JsonResponse({'success': False, 'error': 'Dates de début et fin requises'})

        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Format de date invalide'})

        # Récupération des données complètes des lancements
        lancements = Lancement.objects.filter(
            date_lancement__range=[date_debut, date_fin]
        ).select_related(
            'atelier', 'collaborateur', 'affaire', 'categorie'
        ).order_by('-date_lancement')

        # Génération du fichier selon le format
        if format_export == 'excel':
            return generate_rapport_excel(lancements, date_debut, date_fin)
        elif format_export == 'pdf':
            return generate_rapport_pdf(lancements, date_debut, date_fin)
        elif format_export == 'csv':
            return generate_rapport_csv(lancements, date_debut, date_fin)
        else:
            return JsonResponse({'success': False, 'error': 'Format non supporté'})

    except Exception as e:
        import traceback
        print(f"Erreur dans process_rapport_export: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': f'Erreur lors de l\'export: {str(e)}'})


def generate_rapport_excel(lancements, date_debut, date_fin):
    """
    Génération Excel avec tableau complet comme dans l'image
    """
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)

    # Styles
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    })

    data_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'top'
    })

    number_format = workbook.add_format({
        'border': 1,
        'num_format': '#,##0.00',
        'align': 'right'
    })

    date_format = workbook.add_format({
        'border': 1,
        'num_format': 'dd/mm/yyyy',
        'align': 'center'
    })

    # Feuille principale
    worksheet = workbook.add_worksheet('Rapport Détaillé')

    # En-têtes - exactement comme dans l'image
    headers = [
        'Numéro Lancement',
        'Date Lancement', 
        'Date Réception',
        'Affaire',
        'Client', 
        'Sous-livrable',
        'Atelier',
        'Type Atelier',
        'Collaborateur',
        'Catégorie',
        'Poids Débitage',
        'Poids Assemblage',
        'Poids Total',
        'Statut',
        'Observations'
    ]

    # Écriture des en-têtes
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)

    # Écriture des données
    row = 1
    for lancement in lancements:
        # Calcul du poids total
        poids_debitage = float(lancement.poids_debitage or 0)
        poids_assemblage = float(lancement.poids_assemblage or 0)
        poids_total = poids_debitage + poids_assemblage

        # Données de la ligne
        data_row = [
            lancement.num_lanc,
            lancement.date_lancement,
            lancement.date_reception,
            lancement.affaire.code_affaire if lancement.affaire else '',
            lancement.affaire.client if lancement.affaire else '',
            lancement.sous_livrable or '',
            lancement.atelier.nom_atelier if lancement.atelier else '',
            lancement.atelier.get_type_atelier_display() if lancement.atelier else '',
            lancement.collaborateur.get_full_name() if lancement.collaborateur else '',
            lancement.categorie.nom_categorie if lancement.categorie else '',
            poids_debitage,
            poids_assemblage,
            poids_total,
            lancement.get_statut_display() if hasattr(lancement, 'get_statut_display') else lancement.statut,
            lancement.observations or ''
        ]

        # Écriture de chaque cellule avec le bon format
        for col, value in enumerate(data_row):
            if col in [1, 2]:  # Dates
                worksheet.write(row, col, value, date_format)
            elif col in [10, 11, 12]:  # Poids (nombres)
                worksheet.write(row, col, value, number_format)
            else:  # Texte
                worksheet.write(row, col, str(value), data_format)
        
        row += 1

    # Ajustement automatique de la largeur des colonnes
    column_widths = [
        15,  # Numéro Lancement
        12,  # Date Lancement
        12,  # Date Réception
        15,  # Affaire
        20,  # Client
        20,  # Sous-livrable
        15,  # Atelier
        12,  # Type Atelier
        20,  # Collaborateur
        15,  # Catégorie
        12,  # Poids Débitage
        12,  # Poids Assemblage
        12,  # Poids Total
        12,  # Statut
        25   # Observations
    ]

    for col, width in enumerate(column_widths):
        worksheet.set_column(col, col, width)

    # Ajout d'une feuille de synthèse
    summary_worksheet = workbook.add_worksheet('Synthèse')
    
    # Titre de la synthèse
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 16,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'align': 'center',
        'border': 1
    })
    
    summary_worksheet.merge_range('A1:D1', f'RAPPORT DE PRODUCTION - {date_debut.strftime("%d/%m/%Y")} au {date_fin.strftime("%d/%m/%Y")}', title_format)

    # Statistiques générales
    total_lancements = lancements.count()
    aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    total_debitage = float(aggregation['total_debitage'] or 0)
    total_assemblage = float(aggregation['total_assemblage'] or 0)
    total_poids = total_debitage + total_assemblage

    stats_data = [
        ['Statistique', 'Valeur', 'Unité', 'Description'],
        ['Nombre de lancements', total_lancements, 'unités', 'Total des lancements sur la période'],
        ['Poids débitage total', total_debitage, 'kg', 'Somme des poids de débitage'],
        ['Poids assemblage total', total_assemblage, 'kg', 'Somme des poids d\'assemblage'],
        ['Poids total traité', total_poids, 'kg', 'Poids total débitage + assemblage'],
        ['Durée d\'analyse', (date_fin - date_debut).days + 1, 'jours', 'Nombre de jours analysés']
    ]

    # Écriture des statistiques
    for row_idx, row_data in enumerate(stats_data, start=3):
        for col_idx, cell_value in enumerate(row_data):
            if row_idx == 3:  # En-tête
                summary_worksheet.write(row_idx, col_idx, cell_value, header_format)
            else:
                if col_idx == 1 and isinstance(cell_value, (int, float)):
                    summary_worksheet.write(row_idx, col_idx, cell_value, number_format)
                else:
                    summary_worksheet.write(row_idx, col_idx, str(cell_value), data_format)

    # Largeur des colonnes pour la synthèse
    summary_worksheet.set_column('A:A', 20)
    summary_worksheet.set_column('B:B', 15)
    summary_worksheet.set_column('C:C', 10)
    summary_worksheet.set_column('D:D', 30)

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'rapport_production_{date_debut.strftime("%Y%m%d")}_{date_fin.strftime("%Y%m%d")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


def generate_rapport_csv(lancements, date_debut, date_fin):
    """
    Génération CSV avec toutes les colonnes du tableau
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f'rapport_production_{date_debut.strftime("%Y%m%d")}_{date_fin.strftime("%Y%m%d")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # BOM pour Excel
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')

    # En-têtes
    headers = [
        'Numéro Lancement',
        'Date Lancement', 
        'Date Réception',
        'Affaire',
        'Client', 
        'Sous-livrable',
        'Atelier',
        'Type Atelier',
        'Collaborateur',
        'Catégorie',
        'Poids Débitage',
        'Poids Assemblage',
        'Poids Total',
        'Statut',
        'Observations'
    ]

    writer.writerow(headers)

    # Données
    for lancement in lancements:
        poids_debitage = float(lancement.poids_debitage or 0)
        poids_assemblage = float(lancement.poids_assemblage or 0)
        poids_total = poids_debitage + poids_assemblage

        row = [
            lancement.num_lanc,
            lancement.date_lancement.strftime('%d/%m/%Y'),
            lancement.date_reception.strftime('%d/%m/%Y'),
            lancement.affaire.code_affaire if lancement.affaire else '',
            lancement.affaire.client if lancement.affaire else '',
            lancement.sous_livrable or '',
            lancement.atelier.nom_atelier if lancement.atelier else '',
            lancement.atelier.get_type_atelier_display() if lancement.atelier else '',
            lancement.collaborateur.get_full_name() if lancement.collaborateur else '',
            lancement.categorie.nom_categorie if lancement.categorie else '',
            str(poids_debitage).replace('.', ','),
            str(poids_assemblage).replace('.', ','),
            str(poids_total).replace('.', ','),
            lancement.get_statut_display() if hasattr(lancement, 'get_statut_display') else lancement.statut,
            lancement.observations or ''
        ]

        writer.writerow(row)

    return response


def generate_rapport_pdf(lancements, date_debut, date_fin):
    """
    Génération PDF avec tableau détaillé
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40)
    styles = getSampleStyleSheet()
    story = []

    # Titre principal
    title_style = styles['Title']
    story.append(Paragraph(f"RAPPORT DE PRODUCTION DÉTAILLÉ", title_style))
    story.append(Paragraph(f"Du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Spacer(1, 20))

    # Résumé des statistiques
    total_lancements = lancements.count()
    aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    total_poids = (aggregation['total_debitage'] or 0) + (aggregation['total_assemblage'] or 0)

    story.append(Paragraph("SYNTHÈSE GÉNÉRALE", styles['Heading2']))
    
    stats_data = [
        ['Métrique', 'Valeur'],
        ['Nombre de lancements', str(total_lancements)],
        ['Poids total traité', f"{float(total_poids):.2f} kg"],
        ['Période d\'analyse', f"{(date_fin - date_debut).days + 1} jour(s)"]
    ]

    stats_table = Table(stats_data)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(stats_table)
    story.append(Spacer(1, 20))

    # Tableau détaillé (première page avec en-têtes principaux)
    story.append(Paragraph("DÉTAIL DES LANCEMENTS", styles['Heading2']))
    
    # Tableau simplifié pour le PDF (colonnes principales)
    table_data = [['N° Lanc.', 'Date', 'Affaire', 'Atelier', 'Collaborateur', 'Débitage', 'Assemblage', 'Total']]

    for lancement in lancements[:50]:  # Limiter pour le PDF
        poids_debitage = float(lancement.poids_debitage or 0)
        poids_assemblage = float(lancement.poids_assemblage or 0)
        poids_total = poids_debitage + poids_assemblage

        table_data.append([
            lancement.num_lanc,
            lancement.date_lancement.strftime('%d/%m'),
            lancement.affaire.code_affaire[:12] if lancement.affaire else '',
            lancement.atelier.nom_atelier[:15] if lancement.atelier else '',
            lancement.collaborateur.get_full_name()[:18] if lancement.collaborateur else '',
            f'{poids_debitage:.1f}',
            f'{poids_assemblage:.1f}',
            f'{poids_total:.1f}'
        ])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7)
    ]))

    story.append(table)

    if lancements.count() > 50:
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"... et {lancements.count() - 50} autres lancements", styles['Normal']))

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type='application/pdf')
    filename = f'rapport_production_{date_debut.strftime("%Y%m%d")}_{date_fin.strftime("%Y%m%d")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response
