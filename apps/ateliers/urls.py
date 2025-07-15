from django.urls import path
from . import views

app_name = 'ateliers'

urlpatterns = [
    path('', views.index, name='index'),
]