from django.contrib import admin
from .models import RapportProduction

@admin.register(RapportProduction)
class RapportProductionAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour les Rapports de Production.
    Mis à jour avec les nouveaux champs de poids.
    """
    list_display = (
        'type_rapport', 
        'date_debut', 
        'date_fin', 
        'nb_lancements',
        'nb_lancements_assemblage',
        'nb_lancements_debitage', 
        'get_poids_assemblage_display',
        'get_poids_debitage_total_display',
        'get_poids_total_display',
        'created_at'
    )
    
    list_filter = (
        'type_rapport', 
        'date_debut', 
        'created_at'
    )
    
    search_fields = (
        'type_rapport',
    )
    
    ordering = ('-date_debut',)
    
    readonly_fields = (
        'created_at', 
        'updated_at',
        'get_poids_assemblage_display',
        'get_poids_debitage_total_display',
        'get_poids_total_display',
        'get_efficacite_assemblage_display',
        'get_efficacite_debitage_display'
    )
    
    date_hierarchy = 'date_debut'
    list_per_page = 25
    
    fieldsets = (
        ('Période du rapport', {
            'fields': ('type_rapport', 'date_debut', 'date_fin')
        }),
        ('Statistiques générales', {
            'fields': (
                'nb_lancements',
                'nb_lancements_assemblage', 
                'nb_lancements_debitage',
                'poids_total'
            )
        }),
        ('Poids par type de production', {
            'fields': (
                'poids_assemblage_total',
                'poids_debitage_1_total',
                'poids_debitage_2_total'
            ),
            'classes': ('collapse',)
        }),
        ('Métriques calculées', {
            'fields': (
                'get_poids_assemblage_display',
                'get_poids_debitage_total_display',
                'get_poids_total_display',
                'get_efficacite_assemblage_display',
                'get_efficacite_debitage_display'
            ),
            'classes': ('collapse',),
            'description': 'Valeurs calculées automatiquement'
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Actions personnalisées
    actions = ['recalculer_metriques']
    
    def recalculer_metriques(self, request, queryset):
        """Action pour recalculer les métriques des rapports sélectionnés"""
        updated_count = 0
        for rapport in queryset:
            rapport.recalculate_metrics()
            updated_count += 1
        
        self.message_user(
            request, 
            f"{updated_count} rapport(s) mis à jour avec succès."
        )
    recalculer_metriques.short_description = "Recalculer les métriques"
    
    # Méthodes d'affichage personnalisées pour l'admin
    def get_poids_assemblage_display(self, obj):
        """Affichage formaté du poids assemblage"""
        return obj.get_poids_assemblage_display()
    get_poids_assemblage_display.short_description = 'Poids Assemblage'
    get_poids_assemblage_display.admin_order_field = 'poids_assemblage_total'
    
    def get_poids_debitage_total_display(self, obj):
        """Affichage formaté du poids débitage total"""
        return obj.get_poids_debitage_total_display()
    get_poids_debitage_total_display.short_description = 'Poids Débitage Total'
    
    def get_poids_total_display(self, obj):
        """Affichage formaté du poids total"""
        return obj.get_poids_total_display()
    get_poids_total_display.short_description = 'Poids Total'
    get_poids_total_display.admin_order_field = 'poids_total'
    
    def get_efficacite_assemblage_display(self, obj):
        """Affichage de l'efficacité assemblage"""
        efficacite = obj.get_efficacite_assemblage()
        return f"{efficacite:.2f} kg/lancement" if efficacite > 0 else "N/A"
    get_efficacite_assemblage_display.short_description = 'Efficacité Assemblage'
    
    def get_efficacite_debitage_display(self, obj):
        """Affichage de l'efficacité débitage"""
        efficacite = obj.get_efficacite_debitage()
        return f"{efficacite:.2f} kg/lancement" if efficacite > 0 else "N/A"
    get_efficacite_debitage_display.short_description = 'Efficacité Débitage'
    
    def has_add_permission(self, request):
        """Contrôle les permissions d'ajout"""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Contrôle les permissions de modification"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Contrôle les permissions de suppression"""
        return True