
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
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
]