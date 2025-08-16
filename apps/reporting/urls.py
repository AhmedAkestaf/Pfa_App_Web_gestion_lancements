from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # Liste des rapports
    path('rapports/', views.rapports_list, name='rapports_list'),
    
    # Détail d'un rapport
    path('rapport/<int:rapport_id>/', views.rapport_detail, name='rapport_detail'),
    
    # Génération d'un nouveau rapport
    path('rapport/generer/', views.generate_rapport, name='generate_rapport'),
    
    # Suppression d'un rapport
    path('rapport/<int:rapport_id>/delete/', views.delete_rapport, name='delete_rapport'),
    
    # Tableaux de bord avec graphiques
    path('graphiques/', views.graphiques, name='graphiques'),
    path('dashboard/', views.graphiques, name='dashboard'),  # Alias
    
    # Page d'export
    path('export/', views.export_page, name='export'),
    
    # Traitement des exports
    path('export/process/', views.process_export, name='process_export'),
    
    # Téléchargements d'exports (URLs pour les fichiers générés)
    path('download/excel/', views.download_excel, name='download_excel'),
    path('download/pdf/', views.download_pdf, name='download_pdf'),
    path('download/csv/', views.download_csv, name='download_csv'),
    path('download/json/', views.download_json, name='download_json'),
    
    # APIs pour les graphiques (optionnel)
    path('api/dashboard-data/', views.dashboard_data_api, name='dashboard_data_api'),
    path('api/chart-data/<str:chart_type>/', views.chart_data_api, name='chart_data_api'),
    
    # Export des graphiques
    path('export/dashboard/', views.export_dashboard, name='export_dashboard'),
    path('export/charts/', views.export_charts, name='export_charts'),
    path('export/detailed-charts/', views.export_detailed_charts, name='export_detailed_charts'),
    
    # Régénération et téléchargement de rapports
    path('rapport/<int:rapport_id>/regenerate/', views.regenerate_rapport, name='regenerate_rapport'),
    path('rapport/<int:rapport_id>/download/pdf/', views.download_rapport_pdf, name='download_rapport_pdf'),
    path('rapport/<int:rapport_id>/download/excel/', views.download_rapport_excel, name='download_rapport_excel'),
    
    # Gestion de l'historique d'exports
    path('export/<int:export_id>/delete/', views.delete_export_history, name='delete_export_history'),
    
    # Raccourcis et redirections
    path('', views.rapports_list, name='index'),  # Page d'accueil du module
]