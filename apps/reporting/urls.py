from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # URLs existantes...
    path('', views.rapports_list, name='rapports_list'),
    path('rapport/<int:rapport_id>/', views.rapport_detail, name='rapport_detail'),
    path('graphiques/', views.graphiques, name='graphiques'),
    path('export/', views.export_page, name='export'),
    path('export/process/', views.process_export, name='process_export'),
    path('generate/', views.generate_rapport, name='generate_rapport'),
    
    # Nouvelles URLs pour les exports du dashboard
    path('export/dashboard/', views.export_dashboard_data, name='export_dashboard_data'),
    
    # URLs existantes pour les téléchargements
    path('download/excel/', views.download_excel, name='download_excel'),
    path('download/pdf/', views.download_pdf, name='download_pdf'),
    path('download/csv/', views.download_csv, name='download_csv'),
    path('download/json/', views.download_json, name='download_json'),
    
    # APIs pour les données
    path('api/dashboard-data/', views.dashboard_data_api, name='dashboard_data_api'),
    path('api/chart-data/<str:chart_type>/', views.chart_data_api, name='chart_data_api'),
    
    # Actions sur les rapports
    path('rapport/<int:rapport_id>/delete/', views.delete_rapport, name='delete_rapport'),
    path('rapport/<int:rapport_id>/regenerate/', views.regenerate_rapport, name='regenerate_rapport'),
    path('rapport/<int:rapport_id>/download/pdf/', views.download_rapport_pdf, name='download_rapport_pdf'),
    path('rapport/<int:rapport_id>/download/excel/', views.download_rapport_excel, name='download_rapport_excel'),
    
    # URLs pour les exports spécialisés (à implémenter si nécessaire)
    path('export/charts/', views.export_charts, name='export_charts'),
    path('export/detailed-charts/', views.export_detailed_charts, name='export_detailed_charts'),
    


    path('export/rapport/process/', views.process_rapport_export, name='process_rapport_export'),
    path('rapport/<int:rapport_id>/download/csv/', views.download_rapport_csv, name='download_rapport_csv'),

    # Gestion de l'historique d'exports (optionnel)
    path('export/history/<int:export_id>/delete/', views.delete_export_history, name='delete_export_history'),
]