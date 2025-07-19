from django.db import models
from django.utils import timezone
from apps.lancements.models import Lancement
from apps.ateliers.models import Atelier
from apps.collaborateurs.models import Collaborateur

class RapportProduction(models.Model):
    """
    Modèle pour générer des rapports de production.
    Permet de stocker des statistiques et métriques
    pour les tableaux de bord et analyses.
    """
    # Période du rapport
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    
    # Type de rapport
    type_rapport = models.CharField(max_length=50, choices=[
        ('journalier', 'Journalier'),
        ('hebdomadaire', 'Hebdomadaire'),
        ('mensuel', 'Mensuel'),
        ('annuel', 'Annuel'),
    ], verbose_name="Type de rapport")
    
    # Métriques calculées
    nb_lancements = models.IntegerField(default=0, verbose_name="Nombre de lancements")
    poids_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Poids total traité")
    
    # Dates de création et modification
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière mise à jour")

    def __str__(self):
        return f"Rapport {self.type_rapport} - {self.date_debut} à {self.date_fin}"

    class Meta:
        db_table = 'rapport_production'
        verbose_name = 'Rapport de Production'
        verbose_name_plural = 'Rapports de Production'
        ordering = ['-date_debut']
