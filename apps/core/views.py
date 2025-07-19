# apps/core/views.py
from django.shortcuts import render

def dashboard(request):
    """Vue principale du tableau de bord"""
    context = {
        'title': 'Tableau de bord',
        'user': request.user,
    }
    return render(request, 'dashboard/dashboard.html', context)

def home(request):
    """Page d'accueil qui redirige vers le dashboard"""
    return dashboard(request)