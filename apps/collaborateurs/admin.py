from django.contrib import admin
from .models import Collaborateur

@admin.register(Collaborateur)
class CollaborateurAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour les Collaborateurs.
    Permet de gérer les employés avec filtres, recherche et affichage optimisé.
    """
    list_display = ('nom_collaborateur', 'prenom_collaborateur', 'user_role', 'created_at')
    list_filter = ('user_role', 'created_at')
    search_fields = ('nom_collaborateur', 'prenom_collaborateur')
    ordering = ('nom_collaborateur', 'prenom_collaborateur')
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('nom_collaborateur', 'prenom_collaborateur')
        }),
        ('Informations professionnelles', {
            'fields': ('user_role', 'password')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )