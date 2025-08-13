from django.urls import path
from . import views

app_name = 'associations'

urlpatterns = [
    # URLs Collaborateur-Atelier
    path('collaborateur-atelier/', views.collaborateur_atelier_list, name='collaborateur_atelier_list'),
    path('collaborateur-atelier/create/', views.collaborateur_atelier_create, name='collaborateur_atelier_create'),
    path('collaborateur-atelier/<int:pk>/terminate/', views.collaborateur_atelier_terminate, name='collaborateur_atelier_terminate'),
    path('collaborateur-atelier/<int:pk>/delete/', views.collaborateur_atelier_delete, name='collaborateur_atelier_delete'),
    
    # URLs Collaborateur-Catégorie
    path('collaborateur-categorie/', views.collaborateur_categorie_list, name='collaborateur_categorie_list'),
    path('collaborateur-categorie/create/', views.collaborateur_categorie_create, name='collaborateur_categorie_create'),
    path('collaborateur-categorie/<int:pk>/upgrade/', views.collaborateur_categorie_upgrade, name='collaborateur_categorie_upgrade'),
    path('collaborateur-categorie/<int:pk>/delete/', views.collaborateur_categorie_delete, name='collaborateur_categorie_delete'),
    
    # URLs Atelier-Catégorie
    path('atelier-categorie/', views.atelier_categorie_list, name='atelier_categorie_list'),
    path('atelier-categorie/create/', views.atelier_categorie_create, name='atelier_categorie_create'),
    path('atelier-categorie/<int:pk>/details/', views.atelier_categorie_details, name='atelier_categorie_details'),
    path('atelier-categorie/<int:pk>/update/', views.atelier_categorie_update, name='atelier_categorie_update'),
    path('atelier-categorie/<int:pk>/delete/', views.atelier_categorie_delete, name='atelier_categorie_delete'),
    
    # URLs utilitaires AJAX
    path('check-collaborateur-atelier-conflict/', views.check_collaborateur_atelier_conflict, name='check_collaborateur_atelier_conflict'),
    path('check-collaborateur-categorie-conflict/', views.check_collaborateur_categorie_conflict, name='check_collaborateur_categorie_conflict'),
    path('check-atelier-categorie-conflict/', views.check_atelier_categorie_conflict, name='check_atelier_categorie_conflict'),
]