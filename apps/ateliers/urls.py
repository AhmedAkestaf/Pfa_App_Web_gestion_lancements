from django.urls import path
from . import views

app_name = 'ateliers'

urlpatterns = [
    # === ATELIERS ===
    # Liste des ateliers
    path('list/', views.atelier_list, name='list'),
    
    # Détail d'un atelier
    path('<int:pk>/', views.atelier_detail, name='detail'),
    
    # Création d'un nouvel atelier
    path('create/', views.atelier_create, name='create'),
    
    # Modification d'un atelier
    path('<int:pk>/edit/', views.atelier_edit, name='edit'),
    
    # Suppression d'un atelier
    path('<int:pk>/delete/', views.atelier_delete, name='delete'),

    # === CATÉGORIES ===
    # Liste des catégories
    path('categories/', views.categorie_list, name='categorie_list'),
    
    # Détail d'une catégorie
    path('categories/<int:pk>/', views.categorie_detail, name='categorie_detail'),
    
    # Création d'une nouvelle catégorie
    path('categories/create/', views.categorie_create, name='categorie_create'),
    
    # Modification d'une catégorie
    path('categories/<int:pk>/edit/', views.categorie_edit, name='categorie_edit'),
    
    # Suppression d'une catégorie
    path('categories/<int:pk>/delete/', views.categorie_delete, name='categorie_delete'),
]