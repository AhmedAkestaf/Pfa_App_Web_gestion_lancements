from django.urls import path
from . import views

app_name = 'ateliers'

urlpatterns = [
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
]