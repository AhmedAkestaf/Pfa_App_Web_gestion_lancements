from django.urls import path
from . import views

app_name = 'collaborateurs'

urlpatterns = [
    path('', views.index, name='index'),
]