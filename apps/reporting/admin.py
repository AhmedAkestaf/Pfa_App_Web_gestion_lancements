from django.contrib import admin
from .models import RapportProduction

@admin.register(RapportProduction)
class RapportProductionAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour les Rapports.
    """
    list_display = ('type_rapport', 'date_debut', 'date_fin', 'nb_lancements', 'poids_total', 'created_at')
    list_filter = ('type_rapport', 'date_debut', 'created_at')
    search_fields = ('type_rapport',)
    ordering = ('-date_debut',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date_debut'