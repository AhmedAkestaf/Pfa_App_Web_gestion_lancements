from django.urls import path
from . import views

app_name = 'collaborateurs'

urlpatterns = [
    path('', views.profile_view, name='profile'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('ajax/check-permission/', views.check_permission_ajax, name='check_permission'),
]
