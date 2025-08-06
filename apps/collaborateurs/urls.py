from django.urls import path
from . import views

app_name = 'collaborateurs'

urlpatterns = [
    # Authentification
    path('', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    # Gestion des collaborateurs
    path('list/', views.collaborateur_list, name='list'),
    path('detail/<int:pk>/', views.collaborateur_detail, name='detail'),
    path('create/', views.collaborateur_create, name='create'),
    path('edit/<int:pk>/', views.collaborateur_edit, name='edit'),
    
    path('delete/<int:pk>/', views.collaborateur_delete, name='delete'),
    
    # AJAX
    path('ajax/check-permission/', views.check_permission_ajax, name='check_permission'),
]