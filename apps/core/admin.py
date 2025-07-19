from django.contrib import admin
from .models import Affaire

@admin.register(Affaire)
class AffaireAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour les Affaires.
    Gestion des projets clients avec suivi temporel et responsables.
    """
    list_display = ('code_affaire', 'client', 'responsable_affaire', 'statut', 'date_debut', 'date_fin_prevue')
    list_filter = ('statut', 'date_debut', 'created_at')
    search_fields = ('code_affaire', 'client')
    ordering = ('-date_debut',)
    list_per_page = 25
    readonly_fields = ('created_at',)
    autocomplete_fields = ['responsable_affaire']
    date_hierarchy = 'date_debut'