from django.urls import path
from . import views

app_name = 'lancements'

urlpatterns = [
    # URLs principales
    path('', views.lancement_list, name='list'),
    path('create/', views.lancement_create, name='create'),
    path('<int:pk>/', views.lancement_detail, name='detail'),
    path('<int:pk>/edit/', views.lancement_edit, name='edit'),
    path('<int:pk>/delete/', views.lancement_delete, name='delete'),
    
    # Planning et vues spécialisées
    path('planning/', views.lancement_planning, name='planning'),
    path('statistics/', views.lancement_statistics, name='statistics'),
    path('export/', views.lancement_export, name='export'),
    
    # APIs et vues AJAX 
    path('api/data/', views.get_lancements_data, name='api_data'),
    path('<int:pk>/update-status/', views.update_lancement_status, name='update_status'),
]