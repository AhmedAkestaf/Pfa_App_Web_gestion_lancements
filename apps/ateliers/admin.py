from django.contrib import admin
from .models import Atelier, Categorie, CollaborateurAtelier, CollaborateurCategorie, AtelierCategorie

@admin.register(Atelier)
class AtelierAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour les Ateliers.
    Gestion des ateliers de production avec leurs responsables.
    """
    list_display = ('nom_atelier', 'type_atelier', 'responsable_atelier', 'created_at')
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
    Configuration simplifiée pour les affectations Collaborateur-Atelier.
    Relation many-to-many simple entre collaborateurs et ateliers.
    """
    list_display = ('collaborateur', 'atelier')
    list_filter = ('atelier',)
    search_fields = ('collaborateur__nom_collaborateur', 'atelier__nom_atelier')
    ordering = ('collaborateur', 'atelier')
    autocomplete_fields = ['collaborateur', 'atelier']
    
    class Meta:
        verbose_name = "Affectation Collaborateur-Atelier"
        verbose_name_plural = "Affectations Collaborateur-Atelier"

@admin.register(CollaborateurCategorie)
class CollaborateurCategorieAdmin(admin.ModelAdmin):
    """
    Configuration simplifiée pour les spécialisations Collaborateur-Catégorie.
    Relation many-to-many simple entre collaborateurs et catégories.
    """
    list_display = ('collaborateur', 'categorie')
    list_filter = ('categorie',)
    search_fields = ('collaborateur__nom_collaborateur', 'categorie__nom_categorie')
    ordering = ('collaborateur', 'categorie')
    autocomplete_fields = ['collaborateur', 'categorie']
    
    class Meta:
        verbose_name = "Spécialisation Collaborateur-Catégorie"
        verbose_name_plural = "Spécialisations Collaborateur-Catégorie"

@admin.register(AtelierCategorie)
class AtelierCategorieAdmin(admin.ModelAdmin):
    """
    Configuration simplifiée pour les relations Atelier-Catégorie.
    Relation many-to-many simple entre ateliers et catégories.
    """
    list_display = ('atelier', 'categorie')
    list_filter = ('atelier', 'categorie')
    search_fields = ('atelier__nom_atelier', 'categorie__nom_categorie')
    ordering = ('atelier', 'categorie')
    autocomplete_fields = ['atelier', 'categorie']
    
    class Meta:
        verbose_name = "Relation Atelier-Catégorie"
        verbose_name_plural = "Relations Atelier-Catégorie"