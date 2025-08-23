from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_with_stats, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ========== GESTION DES RÔLES ==========
    path('roles/', views.roles_list, name='roles_list'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/<int:role_id>/', views.role_detail, name='role_detail'),
    path('roles/<int:role_id>/edit/', views.role_edit, name='role_edit'),
    path('roles/<int:role_id>/toggle-status/', views.role_toggle_status, name='role_toggle_status'),
    path('roles/<int:role_id>/duplicate/', views.role_duplicate, name='role_duplicate'),

    # Gestion des permissions
    path('roles/<int:role_id>/permissions/', views.role_permissions, name='role_permissions'),
    
    # Gestion des utilisateurs
    path('roles/<int:role_id>/users/', views.role_users, name='role_users'),
    path('roles/assign-user/', views.assign_role_to_user, name='assign_role_to_user'),
    
    # Templates et outils avancés
    path('roles/templates/', views.role_templates, name='role_templates'),
    path('roles/<int:role_id>/export/', views.export_role_config, name='export_role_config'),
    path('roles/import/', views.import_role_config, name='import_role_config'),

    # ========== GESTION DES AFFAIRES ==========
    path('affaires/', views.affaires_list, name='affaires_list'),
    path('affaires/create/', views.affaire_create, name='affaire_create'),
    path('affaires/<int:affaire_id>/', views.affaire_detail, name='affaire_detail'),
    path('affaires/<int:affaire_id>/edit/', views.affaire_edit, name='affaire_edit'),
    path('affaires/<int:affaire_id>/delete/', views.affaire_delete, name='affaire_delete'),
    path('affaires/<int:affaire_id>/toggle-statut/', views.affaire_toggle_statut, name='affaire_toggle_statut'),
    path('affaires/export/', views.affaires_export, name='affaires_export'),

    # ========== URLS AJAX POUR NOTIFICATIONS ==========
    path('notifications/', views.NotificationsListView.as_view(), name='notifications_list'),
    path('notifications/json/', views.get_notifications_json, name='notifications_json'),
    
    path('notifications/<int:notification_id>/mark-read/', 
         views.marquer_notification_lue_alt, name='notification_mark_read'),
    path('notifications/mark-all-read/', 
         views.marquer_toutes_notifications_lues, name='notifications_mark_all_read'),
    
    # Activités système
    path('activites/', views.ActivitesListView.as_view(), name='activites_list'),
    path('activites/json/', views.get_activites_recentes_json, name='activites_json'),
    
    # Utilitaires de développement
    path('notifications/test/', views.creer_notification_test, name='notification_test'),
    
    path('guide-technique/', views.guide_technique_view, name='guide_technique'),

]