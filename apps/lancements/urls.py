from django.urls import path
from . import views

app_name = 'lancements'

urlpatterns = [
    path('', views.index, name='index'),
]