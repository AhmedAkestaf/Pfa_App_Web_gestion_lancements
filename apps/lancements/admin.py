from django.contrib import admin
from .models import Lancement

@admin.register(Lancement)
class LancementAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour les Lancements.
    C'est la table centrale - interface la plus détaillée pour gérer
    tous les aspects de la production.
    """
    list_display = ('num_lanc', 'date_lancement', 'atelier', 'categorie', 'collaborateur', 'affaire', 'statut')
    list_filter = ('statut', 'date_lancement', 'atelier', 'categorie')
    search_fields = ('num_lanc', 'sous_livrable', 'affaire__code_affaire', 'affaire__client')
    ordering = ('-date_lancement',)
    list_per_page = 30
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['atelier', 'categorie', 'collaborateur', 'affaire']
    date_hierarchy = 'date_lancement'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('num_lanc', 'sous_livrable', 'statut')
        }),
        ('Dates', {
            'fields': ('date_reception', 'date_lancement')
        }),
        ('Affectations', {
            'fields': ('affaire', 'atelier', 'categorie', 'collaborateur')
        }),
        ('Données de production', {
            'fields': ('poids_debitage', 'poids_assemblage', 'observations')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )