from django.contrib import admin
from .models import Atelier, Categorie, CollaborateurAtelier, CollaborateurCategorie, AtelierCategorie

@admin.register(Atelier)
class AtelierAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour les Ateliers.
    Gestion des ateliers de production avec leurs responsables et capacités.
    """
    list_display = ('nom_atelier', 'type_atelier', 'responsable_atelier', 'capacite_max', 'created_at')
    list_filter = ('type_atelier', 'created_at')
    search_fields = ('nom_atelier',)
    ordering = ('nom_atelier',)
    list_per_page = 20
    readonly_fields = ('created_at',)
    autocomplete_fields = ['responsable_atelier']

@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour les Catégories.
    Gestion des catégories de produits/services avec recherche et tri.
    """
    list_display = ('nom_categorie', 'description', 'created_at')
    search_fields = ('nom_categorie',)
    ordering = ('nom_categorie',)
    list_per_page = 20
    readonly_fields = ('created_at',)

@admin.register(CollaborateurAtelier)
class CollaborateurAtelierAdmin(admin.ModelAdmin):
    """
    Configuration pour les affectations Collaborateur-Atelier.
    """
    list_display = ('collaborateur', 'atelier', 'role_dans_atelier', 'date_affectation', 'date_fin_affectation')
    list_filter = ('role_dans_atelier', 'date_affectation', 'atelier')
    search_fields = ('collaborateur__nom_collaborateur', 'atelier__nom_atelier')
    ordering = ('-date_affectation',)
    autocomplete_fields = ['collaborateur', 'atelier']

@admin.register(CollaborateurCategorie)
class CollaborateurCategorieAdmin(admin.ModelAdmin):
    """
    Configuration pour les spécialisations Collaborateur-Catégorie.
    """
    list_display = ('collaborateur', 'categorie', 'niveau_competence', 'date_certification')
    list_filter = ('niveau_competence', 'date_certification', 'categorie')
    search_fields = ('collaborateur__nom_collaborateur', 'categorie__nom_categorie')
    ordering = ('-date_certification',)
    autocomplete_fields = ['collaborateur', 'categorie']

@admin.register(AtelierCategorie)
class AtelierCategorieAdmin(admin.ModelAdmin):
    """
    Configuration pour les capacités Atelier-Catégorie.
    """
    list_display = ('atelier', 'categorie', 'capacite_categorie', 'temps_moyen_traitement')
    list_filter = ('atelier', 'categorie')
    search_fields = ('atelier__nom_atelier', 'categorie__nom_categorie')
    ordering = ('atelier', 'categorie')
    autocomplete_fields = ['atelier', 'categorie']