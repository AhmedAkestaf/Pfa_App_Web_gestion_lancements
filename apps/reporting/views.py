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
    """
    # Paramètres par défaut
    periode = int(request.GET.get('periode', 30))  # Nombre de jours
    atelier_filter = request.GET.get('atelier_filter', '')
    type_analyse = request.GET.get('type_analyse', 'production')

    # Calcul de la période
    date_fin = timezone.now().date()
    date_debut = date_fin - timedelta(days=periode)

    # Requête de base des lancements
    lancements = Lancement.objects.filter(
        date_lancement__range=[date_debut, date_fin]
    )

    if atelier_filter:
        lancements = lancements.filter(atelier_id=atelier_filter)

    # Statistiques du dashboard
    lancements_aggregation = lancements.aggregate(
        total_debitage=Sum('poids_debitage'),
        total_assemblage=Sum('poids_assemblage')
    )
    poids_total_dashboard = (lancements_aggregation['total_debitage'] or 0) + (lancements_aggregation['total_assemblage'] or 0)

    dashboard_stats = {
        'total_lancements': lancements.count(),
        'poids_total': poids_total_dashboard,
        'efficacite': 85.5,  # Simulation
        'delai_moyen': 5,  # Simulation
        'completion_rate': 78.2,  # Simulation
    }

    # Top collaborateurs pour les graphiques
    top_collaborateurs = lancements.values(
        'collaborateur__nom_collaborateur',
        'collaborateur__prenom_collaborateur'
    ).annotate(
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )

    # Traitement des top collaborateurs
    top_collaborateurs_list = []
    for collab in top_collaborateurs:
        debitage = collab['poids_debitage'] or 0
        assemblage = collab['poids_assemblage'] or 0
        collab['poids_total'] = debitage + assemblage
        top_collaborateurs_list.append(collab)

    # Tri et limitation à 5
    top_collaborateurs_list.sort(key=lambda x: x['poids_total'], reverse=True)
    top_collaborateurs_list = top_collaborateurs_list[:5]

    # Top affaires pour les graphiques
    top_affaires = lancements.values(
        'affaire__code_affaire'
    ).annotate(
        poids_debitage=Sum('poids_debitage'),
        poids_assemblage=Sum('poids_assemblage')
    )

    # Traitement des top affaires
    top_affaires_list = []
    for affaire in top_affaires:
        debitage = affaire['poids_debitage'] or 0
        assemblage = affaire['poids_assemblage'] or 0
        affaire['poids_total'] = debitage + assemblage
        top_affaires_list.append(affaire)

    # Tri et limitation à 5
    top_affaires_list.sort(key=lambda x: x['poids_total'], reverse=True)
    top_affaires_list = top_affaires_list[:5]

    # Ajout des couleurs pour les affaires
    colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
    for i, affaire in enumerate(top_affaires_list):
        affaire['color'] = colors[i % len(colors)]

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
        
        # Simulation d'efficacité
        atelier.efficacite = min(95, max(60, 70 + (atelier.nb_lancements or 0) * 2))
        
        performance_ateliers_list.append(atelier)

    # Évolution temporelle
    evolution_periods = []
    current_date = date_debut
    while current_date <= date_fin:
        if periode <= 7:  # Vue journalière
            next_date = current_date
            label = current_date.strftime('%d/%m')
            increment = timedelta(days=1)
        elif periode <= 30:  # Vue hebdomadaire
            next_date = current_date + timedelta(days=6)
            label = f"S{current_date.isocalendar()[1]}"
            increment = timedelta(days=7)
        else:  # Vue mensuelle
            next_date = current_date.replace(day=28) + timedelta(days=4)
            next_date = next_date.replace(day=1) - timedelta(days=1)
            label = current_date.strftime('%m/%Y')
            increment = timedelta(days=32)  # Approximation pour passer au mois suivant

        # Poids pour cette période
        lancements_periode = lancements.filter(
            date_lancement__range=[current_date, min(next_date, date_fin)]
        )
        periode_aggregation = lancements_periode.aggregate(
            total_debitage=Sum('poids_debitage'),
            total_assemblage=Sum('poids_assemblage')
        )
        poids_periode = (periode_aggregation['total_debitage'] or 0) + (periode_aggregation['total_assemblage'] or 0)

        evolution_periods.append({
            'label': label,
            'poids_total': float(poids_periode)
        })

        current_date += increment
        if current_date > date_fin:
            break

    # Meilleur performer
    try:
        top_performer = max(performance_ateliers_list, key=lambda x: x.poids_total) if performance_ateliers_list else None
    except:
        top_performer = None

    # Tendance (simulation)
    trend = 'up'
    trend_percentage = 12.5

    context = {
        'dashboard_stats': dashboard_stats,
        'top_collaborateurs': top_collaborateurs_list,
        'top_affaires': top_affaires_list,
        'performance_ateliers': performance_ateliers_list,
        'evolution_periods': evolution_periods,
        'top_performer': top_performer,
        'trend': trend,
        'trend_percentage': trend_percentage,
        'ateliers': Atelier.objects.all(),
        'periode': periode,
        'atelier_filter': atelier_filter,
        'type_analyse': type_analyse,
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
    Traitement de l'export des données
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
            result = generate_excel_export(
                lancements, date_debut, date_fin, include_stats, detailed_data
            )
            return result['response']
        elif format_export == 'pdf':
            result = generate_pdf_export(
                lancements, date_debut, date_fin, include_graphics, include_stats
            )
            return result['response']
        elif format_export == 'csv':
            result = generate_csv_export(lancements, detailed_data)
            return result['response']
        elif format_export == 'json':
            result = generate_json_export(lancements, detailed_data)
            return result['response']
        else:
            return JsonResponse({'success': False, 'error': 'Format non supporté'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erreur lors de l\'export: {str(e)}'})


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
    Télécharger un rapport spécifique en PDF
    """
    rapport = get_object_or_404(RapportProduction, id=rapport_id)
    
    # Récupérer les lancements de la période
    lancements = Lancement.objects.filter(
        date_lancement__range=[rapport.date_debut, rapport.date_fin]
    )
    
    # Générer le PDF
    result = generate_pdf_export(
        lancements, rapport.date_debut, rapport.date_fin, 
        include_graphics=False, include_stats=True
    )
    
    return result['response']


@login_required
@permission_required('rapports', 'read')
def download_rapport_excel(request, rapport_id):
    """
    Télécharger un rapport spécifique en Excel
    """
    rapport = get_object_or_404(RapportProduction, id=rapport_id)
    
    # Récupérer les lancements de la période
    lancements = Lancement.objects.filter(
        date_lancement__range=[rapport.date_debut, rapport.date_fin]
    )
    
    # Générer l'Excel
    result = generate_excel_export(
        lancements, rapport.date_debut, rapport.date_fin,
        include_stats=True, detailed_data=True
    )
    
    return result['response']


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