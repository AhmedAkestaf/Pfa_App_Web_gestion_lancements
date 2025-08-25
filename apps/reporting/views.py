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


# =============================================================================
# FONCTION UTILITAIRE DE FORMATAGE FRANÇAIS
# =============================================================================

def number_format_french(value, decimal_places=3, unit="kg", include_unit=True):
    """
    Fonction utilitaire pour formater les nombres avec le format français
    - Espaces comme séparateurs de milliers
    - Virgule comme séparateur décimal
    - Nombre de décimales configurable (défaut: 3)
    """
    try:
        if value is None:
            formatted = "0" + ",000" if decimal_places >= 3 else (",0" * decimal_places if decimal_places > 0 else "")
            return f"{formatted} {unit}" if include_unit else formatted
        
        # Convertir en float si nécessaire
        float_value = float(value)
        
        # Si la valeur est 0, retourner directement
        if float_value == 0:
            formatted = "0" + (",000" if decimal_places >= 3 else f",{'0' * decimal_places}" if decimal_places > 0 else "")
            return f"{formatted} {unit}" if include_unit else formatted
        
        # Formatter avec le nombre de décimales spécifié
        formatted = f"{float_value:.{decimal_places}f}"
        
        # Séparer la partie entière et décimale
        if '.' in formatted:
            integer_part, decimal_part = formatted.split('.')
        else:
            integer_part = formatted
            decimal_part = "0" * decimal_places if decimal_places > 0 else ""
        
        # Ajouter les espaces comme séparateurs de milliers
        integer_formatted = ""
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                integer_formatted = " " + integer_formatted
            integer_formatted = digit + integer_formatted
        
        # Retourner le résultat formaté avec virgule comme séparateur décimal
        if decimal_places > 0:
            result = f"{integer_formatted},{decimal_part}"
        else:
            result = integer_formatted
            
        return f"{result} {unit}" if include_unit else result
        
    except (ValueError, TypeError):
        formatted = "0" + (",000" if decimal_places >= 3 else f",{'0' * decimal_places}" if decimal_places > 0 else "")
        return f"{formatted} {unit}" if include_unit else formatted


# =============================================================================
# VUES PRINCIPALES
# =============================================================================

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
    total_poids_debitage = lancements_aggregation['total_debitage'] or 0
    total_poids_assemblage = lancements_aggregation['total_assemblage'] or 0

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
        'total_poids_debitage': total_poids_debitage,
        'total_poids_assemblage': total_poids_assemblage,
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

    # Calcul des totaux globaux
    total_debitage_global = sum(float(stat['poids_debitage'] or 0) for stat in stats_ateliers)
    total_assemblage_global = sum(float(stat['poids_assemblage'] or 0) for stat in stats_ateliers)

    # Traitement des statistiques avec pourcentages
    stats_ateliers_list = []
    
    for stat in stats_ateliers:
        debitage = float(stat['poids_debitage'] or 0)
        assemblage = float(stat['poids_assemblage'] or 0)
        poids_total = debitage + assemblage
        
        # Calcul des pourcentages par rapport aux totaux globaux
        pourcentage_debitage = (debitage / total_debitage_global * 100) if total_debitage_global > 0 else 0
        pourcentage_assemblage = (assemblage / total_assemblage_global * 100) if total_assemblage_global > 0 else 0
        pourcentage_poids = ((poids_total) / (total_debitage_global + total_assemblage_global) * 100) if (total_debitage_global + total_assemblage_global) > 0 else 0
        
        stat_data = {
            'atelier__id': stat['atelier__id'],
            'atelier__nom_atelier': stat['atelier__nom_atelier'],
            'atelier__type_atelier': stat['atelier__type_atelier'],
            'nb_lancements': stat['nb_lancements'],
            'poids_debitage': debitage,
            'poids_assemblage': assemblage,
            'poids_total': poids_total,
            'pourcentage_debitage': pourcentage_debitage,
            'pourcentage_assemblage': pourcentage_assemblage,
            'pourcentage_poids': pourcentage_poids
        }
        stats_ateliers_list.append(stat_data)

    # Tri par poids total décroissant
    stats_ateliers_list.sort(key=lambda x: x['poids_total'], reverse=True)

    # Statistiques par collaborateur
    stats_collaborateurs_base = lancements.values(
        'collaborateur__id', 
        'collaborateur__nom_collaborateur', 
        'collaborateur__prenom_collaborateur'
    ).annotate(
        nb_lancements=Count('id'),
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )

    # Calcul des moyennes manuellement
    stats_collaborateurs_list = []
    for stat in stats_collaborateurs_base:
        debitage = stat['poids_debitage'] or 0
        assemblage = stat['poids_assemblage'] or 0
        stat['poids_total'] = debitage + assemblage
        
        # Calcul des moyennes
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
    poids_debitage_total = (lancements_aggregation['total_debitage'] or 0)
    poids_assemblage_total = (lancements_aggregation['total_assemblage'] or 0)

    # Calcul du nombre de jours d'analyse
    jours_analyse = (date_fin - date_debut).days + 1

    dashboard_stats = {
        'total_lancements': lancements.count(),
        'poids__debitage_total': poids_debitage_total,
        'poids__assemblage_total': poids_assemblage_total,
        'efficacite': 85.5,
        'delai_moyen': 5,
        'completion_rate': 78.2,
    }

    # Top collaborateurs pour les graphiques
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

    # Top affaires par poids débitage uniquement
    top_affaires_data = lancements.values(
        'affaire__code_affaire'
    ).annotate(
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )

    # Traitement des top affaires
    top_affaires_list = []
    total_poids_debitage_affaires = 0
    
    for affaire in top_affaires_data:
        poids_debitage = affaire['poids_debitage'] or 0
        
        affaire_data = {
            'code_affaire': affaire['affaire__code_affaire'],
            'poids_debitage': poids_debitage,
            'poids_total': poids_debitage
        }
        top_affaires_list.append(affaire_data)
        total_poids_debitage_affaires += poids_debitage

    # Tri et limitation à 8 affaires par poids débitage
    top_affaires_list.sort(key=lambda x: x['poids_debitage'], reverse=True)
    top_affaires = top_affaires_list[:8]

    # Calcul des pourcentages pour les affaires
    for affaire in top_affaires:
        if total_poids_debitage_affaires > 0:
            affaire['pourcentage'] = (affaire['poids_debitage'] / total_poids_debitage_affaires) * 100
        else:
            affaire['pourcentage'] = 0

    # Répartition par catégories
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

    # Performance des ateliers
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
        
        # Simulation d'efficacité
        base_efficacite = 70
        bonus_lancements = min(25, (atelier.nb_lancements or 0) * 2)
        bonus_poids = min(5, atelier.poids_total / 100)
        atelier.efficacite = min(95, base_efficacite + bonus_lancements + bonus_poids)
        
        performance_ateliers_list.append(atelier)

    # Tri par poids total décroissant
    performance_ateliers_list.sort(key=lambda x: x.poids_total, reverse=True)

    # Insights
    top_performer = performance_ateliers_list[0] if performance_ateliers_list else None
    top_collaborateur = top_collaborateurs[0] if top_collaborateurs else None
    top_affaire = top_affaires[0] if top_affaires else None

    # Tendance (simulation)
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
    recent_exports = []
    
    # Statistiques d'export
    total_exports = 25
    
    context = {
        'ateliers': ateliers,
        'collaborateurs': collaborateurs,
        'affaires': affaires,
        'recent_exports': recent_exports,
        'total_exports': total_exports,
    }
    
    return render(request, 'reporting/export.html', context)


# =============================================================================
# FONCTIONS D'EXPORT AVEC FORMATAGE FRANÇAIS
# =============================================================================

@login_required
@permission_required('rapports', 'export')
def process_export(request):
    """
    Traitement de l'export des données avec formatage français
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


def generate_excel_export(lancements, date_debut, date_fin, include_stats, detailed_data):
    """
    Génération d'un fichier Excel avec formatage français des nombres
    """
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    
    # Styles avec format français
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
    
    # Format numérique français : espace comme séparateur de milliers, virgule pour décimales
    number_format_french = workbook.add_format({
        'border': 1,
        'num_format': '#,##0.000',
        'align': 'right'
    })

    # Feuille principale - Données des lancements
    worksheet = workbook.add_worksheet('Lancements')
    
    # En-têtes
    headers = [
        'Numéro Lancement', 'Date Lancement', 'Date Réception', 
        'Affaire', 'Client', 'Sous-livrable', 'Atelier', 'Type Atelier',
        'Collaborateur', 'Catégorie', 'Poids Débitage', 'Poids Assemblage',
        'Statut', 'Observations'
    ]
    
    # Écriture des en-têtes
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # Écriture des données avec formatage français
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
        worksheet.write(row, 10, float(lancement.poids_debitage), number_format_french)
        worksheet.write(row, 11, float(lancement.poids_assemblage), number_format_french)
        worksheet.write(row, 12, lancement.get_statut_display(), data_format)
        worksheet.write(row, 13, lancement.observations or '', data_format)

    # Ajustement de la largeur des colonnes
    worksheet.set_column('A:N', 15)

    total_debitage = lancements.aggregate(Sum('poids_debitage'))['poids_debitage__sum'] or 0
    total_assemblage = lancements.aggregate(Sum('poids_assemblage'))['poids_assemblage__sum'] or 0

    # Feuille statistiques avec formatage français
    if include_stats:
        stats_worksheet = workbook.add_worksheet('Statistiques')

        # Statistiques globales
        stats_worksheet.write('A1', 'Période d\'analyse', header_format)
        stats_worksheet.write('B1', f'{date_debut.strftime("%d/%m/%Y")} - {date_fin.strftime("%d/%m/%Y")}', data_format)

        stats_worksheet.write('A2', 'Nombre total de lancements', header_format)
        stats_worksheet.write('B2', lancements.count(), data_format)
    
        # Calcul des poids totaux avec formatage français
        total_debitage = sum(float(l.poids_debitage or 0) for l in lancements)
        total_assemblage = sum(float(l.poids_assemblage or 0) for l in lancements)
    
        stats_worksheet.write('A3', 'Poids débitage total', header_format)
        stats_worksheet.write('B3', number_format_french(total_debitage), data_format)
    
        stats_worksheet.write('A4', 'Poids assemblage total', header_format)
        stats_worksheet.write('B4', number_format_french(total_assemblage), data_format)
    
        # Statistiques par atelier avec formatage français
        stats_worksheet.write('A6', 'Statistiques par Atelier', header_format)
        stats_worksheet.write('A7', 'Atelier', header_format)
        stats_worksheet.write('B7', 'Nb Lancements', header_format)
        stats_worksheet.write('C7', 'Poids Débitage', header_format)
        stats_worksheet.write('D7', 'Poids Assemblage', header_format)
    
        # Calcul des statistiques par atelier
        ateliers_stats = {}
        for lancement in lancements:
            atelier = lancement.atelier.nom_atelier if lancement.atelier else 'Non défini'
            if atelier not in ateliers_stats:
                ateliers_stats[atelier] = {
                    'nb': 0, 
                    'poids_debitage': 0, 
                    'poids_assemblage': 0
                }
            ateliers_stats[atelier]['nb'] += 1
            ateliers_stats[atelier]['poids_debitage'] += float(lancement.poids_debitage or 0)
            ateliers_stats[atelier]['poids_assemblage'] += float(lancement.poids_assemblage or 0)
    
        # Écriture des statistiques par atelier avec formatage français
        row = 8
        for atelier, stats in ateliers_stats.items():
            stats_worksheet.write(row, 0, atelier, data_format)
            stats_worksheet.write(row, 1, stats['nb'], data_format)
            stats_worksheet.write(row, 2, number_format_french(stats['poids_debitage'], include_unit=False), data_format)
            stats_worksheet.write(row, 3, number_format_french(stats['poids_assemblage'], include_unit=False), data_format)
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
    Génération d'un fichier PDF avec formatage français
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Titre
    title_style = styles['Title']
    story.append(Paragraph(f"Rapport de Production - {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}", title_style))
    story.append(Spacer(1, 12))

    # Statistiques avec formatage français
    if include_stats:
        story.append(Paragraph("Statistiques Générales", styles['Heading2']))
        
        # Calcul du poids total avec formatage français
        total_debitage = sum(float(l.poids_debitage or 0) for l in lancements)
        total_assemblage = sum(float(l.poids_assemblage or 0) for l in lancements)

        stats_data = [
            ['Métrique', 'Valeur'],
            ['Nombre de lancements', str(lancements.count())],
            ['Poids débitage total', number_format_french(total_debitage)],
            ['Poids assemblage total', number_format_french(total_assemblage)],
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

    # Tableau des lancements avec formatage français
    story.append(Paragraph("Détail des Lancements", styles['Heading2']))
    
    table_data = [['N° Lanc.', 'Date', 'Affaire', 'Atelier', 'Collaborateur', 'Débitage', 'Assemblage']]
    
    for lancement in lancements[:50]:  # Limiter à 50 pour le PDF
        poids_debitage = float(lancement.poids_debitage or 0)
        poids_assemblage = float(lancement.poids_assemblage or 0)
        
        table_data.append([
            lancement.num_lanc,
            lancement.date_lancement.strftime('%d/%m/%Y'),
            lancement.affaire.code_affaire,
            lancement.atelier.nom_atelier,
            lancement.collaborateur.get_full_name()[:20],
            number_format_french(poids_debitage, include_unit=False),
            number_format_french(poids_assemblage, include_unit=False)
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
    Génération d'un fichier CSV avec formatage français
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
        'Poids Assemblage', 'Statut'
    ]
    
    if detailed_data:
        headers.extend(['Type Atelier', 'Observations', 'Date Création'])
    
    writer.writerow(headers)
    
    # Données avec formatage français
    for lancement in lancements:
        poids_debitage = number_format_french(lancement.poids_debitage, include_unit=False)
        poids_assemblage = number_format_french(lancement.poids_assemblage, include_unit=False)
        
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
            poids_debitage,
            poids_assemblage,
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


# =============================================================================
# FONCTIONS D'EXPORT DASHBOARD AVEC FORMATAGE FRANÇAIS
# =============================================================================

@login_required
@permission_required('rapports', 'export')
def export_dashboard_data(request):
    """
    Export spécifique pour les données du dashboard avec formatage français
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
    Génération Excel dashboard avec formatage français
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
    number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.000'})
    
    # Feuille principale
    worksheet = workbook.add_worksheet('Dashboard')
    
    current_row = 0
    
    # En-tête du rapport
    worksheet.merge_range(f'A{current_row+1}:E{current_row+1}', 'TABLEAU DE BORD - ANALYTICS DE PRODUCTION', header_format)
    current_row += 1
    
    worksheet.merge_range(f'A{current_row+1}:E{current_row+1}', f'Période: {date_debut.strftime("%d/%m/%Y")} - {date_fin.strftime("%d/%m/%Y")}', data_format)
    current_row += 2
    
    # STATISTIQUES GÉNÉRALES avec formatage français
    worksheet.merge_range(f'A{current_row+1}:B{current_row+1}', 'STATISTIQUES GÉNÉRALES', header_format)
    current_row += 1
    
    # Calculs des statistiques
    total_lancements = lancements.count()
    aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    
    total_debitage = float(aggregation['total_debitage'] or 0)
    total_assemblage = float(aggregation['total_assemblage'] or 0)
    
    stats_data = [
        ['Nombre total de lancements', total_lancements],
        ['Poids total débitage', number_format_french(total_debitage)],
        ['Poids total assemblage', number_format_french(total_assemblage)],
        ['Nombre de jours analysés', (date_fin - date_debut).days + 1]
    ]
    
    # Écriture des statistiques
    for stat in stats_data:
        current_row += 1
        worksheet.write(current_row, 0, stat[0], data_format)
        if isinstance(stat[1], str) and 'kg' in stat[1]:
            worksheet.write(current_row, 1, stat[1], data_format)
        elif isinstance(stat[1], (int, float)) and stat[1] != int(stat[1]):
            worksheet.write(current_row, 1, stat[1], number_format)
        else:
            worksheet.write(current_row, 1, stat[1], data_format)
    
    current_row += 2
    
    # TOP COLLABORATEURS avec formatage français
    worksheet.merge_range(f'A{current_row+1}:C{current_row+1}', 'TOP COLLABORATEURS', header_format)
    current_row += 1
    
    collab_headers = ['Collaborateur', 'Poids Débitage', 'Poids Assemblage']
    for col, header in enumerate(collab_headers):
        worksheet.write(current_row, col, header, header_format)
    
    # Données collaborateurs avec formatage français
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
            'assemblage': assemblage
        })
    
    collab_list.sort(key=lambda x: x['debitage'], reverse=True)
    
    # Écriture des données collaborateurs avec formatage français
    for collab in collab_list[:10]:
        current_row += 1
        worksheet.write(current_row, 0, collab['nom'], data_format)
        worksheet.write(current_row, 1, number_format_french(collab['debitage'], include_unit=False), data_format)
        worksheet.write(current_row, 2, number_format_french(collab['assemblage'], include_unit=False), data_format)
    
    current_row += 2
    
    # TOP AFFAIRES avec formatage français
    worksheet.merge_range(f'A{current_row+1}:C{current_row+1}', 'TOP AFFAIRES', header_format)
    current_row += 1
    
    affaire_headers = ['Code Affaire', 'Poids Débitage', 'Pourcentage']
    for col, header in enumerate(affaire_headers):
        worksheet.write(current_row, col, header, header_format)
    
    # Données affaires avec formatage français
    affaire_data = lancements.values('affaire__code_affaire').annotate(
        poids_debitage=Sum('poids_debitage')
    )
    
    affaire_list = []
    total_debitage_affaires = 0
    
    for affaire in affaire_data:
        poids_debitage = float(affaire['poids_debitage'] or 0)
        affaire_list.append({
            'code': affaire['affaire__code_affaire'],
            'poids_debitage': poids_debitage
        })
        total_debitage_affaires += poids_debitage
    
    affaire_list.sort(key=lambda x: x['poids_debitage'], reverse=True)
    
    # Écriture des données affaires avec formatage français
    for affaire in affaire_list[:8]:
        current_row += 1
        pourcentage = (affaire['poids_debitage'] / total_debitage_affaires * 100) if total_debitage_affaires > 0 else 0
        worksheet.write(current_row, 0, affaire['code'], data_format)
        worksheet.write(current_row, 1, number_format_french(affaire['poids_debitage'], include_unit=False), data_format)
        worksheet.write(current_row, 2, f"{pourcentage:.1f}%".replace('.', ','), data_format)
    
    # Ajustement des largeurs de colonnes
    worksheet.set_column('A:A', 25)
    worksheet.set_column('B:C', 15)
    worksheet.set_column('D:E', 12)
    
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
    Génération PDF dashboard avec formatage français
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

    # Statistiques générales avec formatage français
    story.append(Paragraph("STATISTIQUES GÉNÉRALES", styles['Heading2']))
    
    total_lancements = lancements.count()
    aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    
    stats_data = [
        ['Métrique', 'Valeur'],
        ['Nombre de lancements', str(total_lancements)],
        ['Poids débitage', number_format_french(aggregation['total_debitage'] or 0)],
        ['Poids assemblage', number_format_french(aggregation['total_assemblage'] or 0)],
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

    # Top Collaborateurs avec formatage français
    story.append(Paragraph("TOP COLLABORATEURS", styles['Heading2']))
    
    collab_data = lancements.values(
        'collaborateur__nom_collaborateur',
        'collaborateur__prenom_collaborateur'
    ).annotate(
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )
    
    collab_table_data = [['Collaborateur', 'Débitage', 'Assemblage']]
    
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
    
    # Formatage français dans le tableau PDF
    for collab in collab_list[:10]:
        collab_table_data.append([
            collab['nom'],
            number_format_french(collab['debitage'], include_unit=False),
            number_format_french(collab['assemblage'], include_unit=False)
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
    Génération CSV dashboard avec formatage français
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
    
    # Statistiques générales avec formatage français
    writer.writerow(['STATISTIQUES GENERALES'])
    total_lancements = lancements.count()
    aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    
    writer.writerow(['Nombre de lancements', total_lancements])
    writer.writerow(['Poids débitage', number_format_french(aggregation['total_debitage'] or 0, include_unit=False)])
    writer.writerow(['Poids assemblage', number_format_french(aggregation['total_assemblage'] or 0, include_unit=False)])
    writer.writerow([])
    
    # Collaborateurs avec formatage français
    writer.writerow(['TOP COLLABORATEURS'])
    writer.writerow(['Collaborateur', 'Poids Débitage', 'Poids Assemblage'])
    
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
    
    # Écriture des collaborateurs avec formatage français
    for collab in collab_list[:10]:
        writer.writerow([
            collab['nom'],
            number_format_french(collab['debitage'], include_unit=False),
            number_format_french(collab['assemblage'], include_unit=False)
        ])
    
    return response


# =============================================================================
# FONCTIONS D'EXPORT RAPPORT DÉTAILLÉ AVEC FORMATAGE FRANÇAIS
# =============================================================================

@login_required
@permission_required('rapports', 'export')
def process_rapport_export(request):
    """
    Traitement de l'export spécifique pour les rapports détaillés avec formatage français
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

    try:
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
        'num_format': '#,##0.000',
        'align': 'right'
    })

    date_format = workbook.add_format({
        'border': 1,
        'num_format': 'dd/mm/yyyy',
        'align': 'center'
    })

    # Feuille principale
    worksheet = workbook.add_worksheet('Rapport Détaillé')

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
            lancement.get_statut_display() if hasattr(lancement, 'get_statut_display') else lancement.statut,
            lancement.observations or ''
        ]

        # Écriture de chaque cellule avec le bon format
        for col, value in enumerate(data_row):
            if col in [1, 2]:  # Dates
                worksheet.write(row, col, value, date_format)
            elif col in [10, 11]:  # Poids (nombres)
                worksheet.write(row, col, value, number_format)
            else:  # Texte
                worksheet.write(row, col, str(value), data_format)
        
        row += 1

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

    stats_data = [
        ['Statistique', 'Valeur', 'Unité', 'Description'],
        ['Nombre de lancements', total_lancements, 'unités', 'Total des lancements sur la période'],
        ['Poids débitage total', total_debitage, 'kg', 'Somme des poids de débitage'],
        ['Poids assemblage total', total_assemblage, 'kg', 'Somme des poids d\'assemblage'],
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
    Génération CSV avec formatage français
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f'rapport_production_{date_debut.strftime("%Y%m%d")}_{date_fin.strftime("%Y%m%d")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # BOM pour Excel
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')

    # En-têtes
    headers = [
        'Numéro Lancement', 'Date Lancement', 'Date Réception', 'Affaire', 'Client', 
        'Sous-livrable', 'Atelier', 'Type Atelier', 'Collaborateur', 'Catégorie',
        'Poids Débitage', 'Poids Assemblage', 'Statut', 'Observations'
    ]

    writer.writerow(headers)

    # Données avec formatage français
    for lancement in lancements:
        poids_debitage = number_format_french(lancement.poids_debitage, include_unit=False)
        poids_assemblage = number_format_french(lancement.poids_assemblage, include_unit=False)

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
            poids_debitage,
            poids_assemblage,
            lancement.get_statut_display() if hasattr(lancement, 'get_statut_display') else lancement.statut,
            lancement.observations or ''
        ]

        writer.writerow(row)

    return response


def generate_rapport_pdf(lancements, date_debut, date_fin):
    """
    Génération PDF avec formatage français
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

    # Résumé des statistiques avec formatage français
    total_lancements = lancements.count()
    aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )

    story.append(Paragraph("SYNTHÈSE GÉNÉRALE", styles['Heading2']))
    
    stats_data = [
        ['Métrique', 'Valeur'],
        ['Nombre de lancements', str(total_lancements)],
        ['Poids total débitage', number_format_french(aggregation['total_debitage'] or 0)],
        ['Poids total assemblage', number_format_french(aggregation['total_assemblage'] or 0)],
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

    # Tableau détaillé avec formatage français
    story.append(Paragraph("DÉTAIL DES LANCEMENTS", styles['Heading2']))
    
    table_data = [['N° Lanc.', 'Date', 'Affaire', 'Atelier', 'Collaborateur', 'Débitage', 'Assemblage']]

    for lancement in lancements[:50]:  # Limiter pour le PDF
        poids_debitage = float(lancement.poids_debitage or 0)
        poids_assemblage = float(lancement.poids_assemblage or 0)

        table_data.append([
            lancement.num_lanc,
            lancement.date_lancement.strftime('%d/%m'),
            lancement.affaire.code_affaire[:12] if lancement.affaire else '',
            lancement.atelier.nom_atelier[:15] if lancement.atelier else '',
            lancement.collaborateur.get_full_name()[:18] if lancement.collaborateur else '',
            number_format_french(poids_debitage, include_unit=False),
            number_format_french(poids_assemblage, include_unit=False)
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


# =============================================================================
# VUES UTILITAIRES ET HELPERS
# =============================================================================

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

        # Calcul des métriques
        lancements = Lancement.objects.filter(
            date_lancement__range=[date_debut, date_fin]
        )
        
        nb_lancements = lancements.count()
        
        # Calcul correct du poids total
        lancements_aggregation = lancements.aggregate(
            total_debitage=Sum('poids_debitage'),
            total_assemblage=Sum('poids_assemblage')
        )
        total_debitage = (lancements_aggregation['total_debitage'] or 0)
        total_assemblage = (lancements_aggregation['total_assemblage'] or 0)
        poids_total = total_debitage + total_assemblage

        # Création du rapport
        rapport = RapportProduction.objects.create(
            date_debut=date_debut,
            date_fin=date_fin,
            type_rapport=type_rapport,
            nb_lancements=nb_lancements,
            poids_debitage=total_debitage,
            poids_assemblage=total_assemblage,
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


# Vues pour les téléchargements avec formatage français
@login_required
@permission_required('rapports', 'export')
def download_rapport_pdf(request, rapport_id):
    """
    Télécharger un rapport spécifique en PDF
    """
    rapport = get_object_or_404(RapportProduction, id=rapport_id)
    lancements = Lancement.objects.filter(
        date_lancement__range=[rapport.date_debut, rapport.date_fin]
    ).select_related('atelier', 'collaborateur', 'affaire', 'categorie')
    return generate_rapport_pdf(lancements, rapport.date_debut, rapport.date_fin)


@login_required
@permission_required('rapports', 'export')
def download_rapport_excel(request, rapport_id):
    """
    Télécharger un rapport spécifique en Excel
    """
    rapport = get_object_or_404(RapportProduction, id=rapport_id)
    lancements = Lancement.objects.filter(
        date_lancement__range=[rapport.date_debut, rapport.date_fin]
    ).select_related('atelier', 'collaborateur', 'affaire', 'categorie')
    return generate_rapport_excel(lancements, rapport.date_debut, rapport.date_fin)


@login_required
@permission_required('rapports', 'export')
def download_rapport_csv(request, rapport_id):
    """
    Télécharger un rapport spécifique en CSV
    """
    rapport = get_object_or_404(RapportProduction, id=rapport_id)
    lancements = Lancement.objects.filter(
        date_lancement__range=[rapport.date_debut, rapport.date_fin]
    ).select_related('atelier', 'collaborateur', 'affaire', 'categorie')
    return generate_rapport_csv(lancements, rapport.date_debut, rapport.date_fin)


# =============================================================================
# API ET VUES ADDITIONNELLES
# =============================================================================

@login_required
@permission_required('rapports', 'read')
def dashboard_data_api(request):
    """
    API pour récupérer les données du dashboard avec formatage français
    """
    periode = int(request.GET.get('periode', 30))
    date_fin = timezone.now().date()
    date_debut = date_fin - timedelta(days=periode)

    lancements = Lancement.objects.filter(
        date_lancement__range=[date_debut, date_fin]
    )

    lancements_aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    poids_total = (lancements_aggregation['total_debitage'] or 0) + (lancements_aggregation['total_assemblage'] or 0)

    data = {
        'total_lancements': lancements.count(),
        'poids_total': float(poids_total),
        'poids_total_formatted': number_format_french(poids_total),
        'efficacite': 85.5,
        'delai_moyen': 5,
    }

    return JsonResponse(data)


@login_required
@permission_required('rapports', 'read')
def chart_data_api(request, chart_type):
    """
    API pour récupérer des données spécifiques de graphiques avec formatage français
    """
    periode = int(request.GET.get('periode', 30))
    date_fin = timezone.now().date()
    date_debut = date_fin - timedelta(days=periode)

    lancements = Lancement.objects.filter(
        date_lancement__range=[date_debut, date_fin]
    )

    if chart_type == 'ateliers':
        data = list(lancements.values('atelier__nom_atelier').annotate(
            count=Count('id'),
            poids_debitage=Sum('poids_debitage'),
            poids_assemblage=Sum('poids_assemblage')
        ).annotate(
            poids=F('poids_debitage') + F('poids_assemblage')
        ))
        
        # Ajouter le formatage français
        for item in data:
            item['poids_formatted'] = number_format_french(item['poids'])
            
    elif chart_type == 'collaborateurs':
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
        
        # Ajouter le formatage français
        for item in data:
            item['poids_formatted'] = number_format_french(item['poids'])
    else:
        data = []

    return JsonResponse({'data': data})


@login_required
@permission_required('rapports', 'create')
def regenerate_rapport(request, rapport_id):
    """
    Régénérer un rapport existant
    """
    rapport = get_object_or_404(RapportProduction, id=rapport_id)
    
    lancements = Lancement.objects.filter(
        date_lancement__range=[rapport.date_debut, rapport.date_fin]
    )
    
    rapport.nb_lancements = lancements.count()
    
    lancements_aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    rapport.poids_debitage = (lancements_aggregation['total_debitage'] or 0)
    rapport.poids_assemblage = (lancements_aggregation['total_assemblage'] or 0)
    rapport.poids_total = rapport.poids_debitage + rapport.poids_assemblage
    rapport.save()
    
    messages.success(request, 'Rapport régénéré avec succès.')
    return redirect('reporting:rapport_detail', rapport_id=rapport.id)


@login_required
@permission_required('rapports', 'delete')
@require_http_methods(["DELETE"])
def delete_export_history(request, export_id):
    """
    Supprimer un historique d'export
    """
    return JsonResponse({
        'success': True, 
        'message': 'Historique supprimé (fonctionnalité à implémenter)'
    })


# =============================================================================
# VUES DE REDIRECTION POUR COMPATIBILITÉ
# =============================================================================

@login_required
@permission_required('rapports', 'export')
def export_charts(request):
    messages.info(request, 'Utilisez les boutons "Exporter PNG" ou "Exporter PDF" sur la page des graphiques.')
    return redirect('reporting:graphiques')


@login_required
@permission_required('rapports', 'export') 
def export_detailed_charts(request):
    messages.info(request, 'Export détaillé des graphiques en cours de développement.')
    return redirect('reporting:graphiques')


@login_required
@permission_required('rapports', 'export')
def download_excel(request):
    return redirect('reporting:process_export')


@login_required
@permission_required('rapports', 'export')
def download_pdf(request):
    return redirect('reporting:process_export')


@login_required
@permission_required('rapports', 'export')
def download_csv(request):
    return redirect('reporting:process_export')


@login_required
@permission_required('rapports', 'export')
def download_json(request):
    return redirect('reporting:process_export')


@login_required
@permission_required('rapports', 'export')
def export_dashboard(request):
    messages.info(request, 'Export du dashboard en cours de développement.')
    return redirect('reporting:graphiques')


# Fonction pour améliorer la gestion des erreurs d'export
def handle_export_error(request, error_message, redirect_url='reporting:export'):
    """
    Gestion centralisée des erreurs d'export
    """
    messages.error(request, f'Erreur d\'export: {error_message}')
    return redirect(redirect_url)