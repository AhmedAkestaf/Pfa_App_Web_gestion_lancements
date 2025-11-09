from django.contrib import admin
from .models import Lancement

@admin.register(Lancement)
class LancementAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour les Lancements.
    C'est la table centrale - interface la plus détaillée pour gérer
    tous les aspects de la production.
    """
    list_display = (
        'num_lanc', 
        'date_lancement', 
        'atelier', 
        'categorie', 
        'collaborateur', 
        'affaire', 
        'type_production',
        'get_poids_total_display',
        'statut'
    )
    
    list_filter = (
        'statut', 
        'type_production',
        'date_lancement', 
        'atelier', 
        'categorie'
    )
    
    search_fields = (
        'num_lanc', 
        'sous_livrable', 
        'affaire__code_affaire', 
        'affaire__client'
    )
    
    ordering = ('-date_lancement',)
    list_per_page = 30
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['atelier', 'categorie', 'collaborateur', 'affaire']
    date_hierarchy = 'date_lancement'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('num_lanc', 'sous_livrable', 'statut', 'type_production')
        }),
        ('Dates', {
            'fields': ('date_reception', 'date_lancement')
        }),
        ('Affectations', {
            'fields': ('affaire', 'atelier', 'categorie', 'collaborateur')
        }),
        ('Données de production - Assemblage', {
            'fields': ('poids_assemblage',),
            'classes': ('collapse',),
            'description': 'Affiché uniquement pour le type "Assemblage"'
        }),
        ('Données de production - Débitage', {
            'fields': ('poids_debitage_1', 'poids_debitage_2'),
            'classes': ('collapse',),
            'description': 'Affiché uniquement pour le type "Débitage"'
        }),
        ('Observations', {
            'fields': ('observations',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Affichage personnalisé du poids total dans la liste
    def get_poids_total_display(self, obj):
        """Affiche le poids total calculé"""
        return obj.get_poids_total_display()
    get_poids_total_display.short_description = 'Poids Total'
    get_poids_total_display.admin_order_field = 'poids_assemblage'  # Pour le tri
    
    # JavaScript pour afficher/masquer les champs selon le type de production
    class Media:
        js = ('admin/js/lancement_admin.js',)
    
    def get_form(self, request, obj=None, **kwargs):
        """Personnalise le formulaire selon le type de production"""
        form = super().get_form(request, obj, **kwargs)
        
        # Si on édite un objet existant, on peut conditionner l'affichage
        if obj and obj.type_production:
            # Logique pour masquer/afficher des champs selon le type
            # (nécessiterait du JavaScript côté client)
            pass
            
        return form