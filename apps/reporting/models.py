# apps/reporting/models.py - MIS À JOUR avec nouveaux champs de poids

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
    
    # MISE À JOUR des métriques calculées selon les nouveaux champs de poids
    nb_lancements = models.IntegerField(default=0, verbose_name="Nombre de lancements")
    
    # Nouveaux champs alignés sur le modèle Lancement mis à jour
    poids_assemblage_total = models.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        default=0, 
        verbose_name="Poids assemblage total"
    )
    poids_debitage_1_total = models.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        default=0, 
        verbose_name="Poids débitage 1 total"
    )
    poids_debitage_2_total = models.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        default=0, 
        verbose_name="Poids débitage 2 total"
    )
    
    # Champ calculé pour le poids total
    poids_total = models.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        default=0, 
        verbose_name="Poids total traité"
    )
    
    # Statistiques par type de production
    nb_lancements_assemblage = models.IntegerField(
        default=0, 
        verbose_name="Nombre de lancements assemblage"
    )
    nb_lancements_debitage = models.IntegerField(
        default=0, 
        verbose_name="Nombre de lancements débitage"
    )
    
    # Dates de création et modification
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière mise à jour")

    def __str__(self):
        return f"Rapport {self.type_rapport} - {self.date_debut} à {self.date_fin}"

    def get_poids_debitage_total(self):
        """Calcule le poids débitage total (débitage 1 + débitage 2)"""
        return float(self.poids_debitage_1_total or 0) + float(self.poids_debitage_2_total or 0)
    
    def get_poids_debitage_total_display(self):
        """Retourne le poids débitage total formaté"""
        return f"{self.get_poids_debitage_total():.3f} kg"
    
    def get_poids_assemblage_display(self):
        """Retourne le poids assemblage formaté"""
        return f"{float(self.poids_assemblage_total or 0):.3f} kg"
    
    def get_poids_total_display(self):
        """Retourne le poids total formaté"""
        return f"{float(self.poids_total or 0):.3f} kg"
    
    def get_efficacite_assemblage(self):
        """Calcule l'efficacité pour l'assemblage"""
        if self.nb_lancements_assemblage == 0:
            return 0
        return float(self.poids_assemblage_total) / self.nb_lancements_assemblage
    
    def get_efficacite_debitage(self):
        """Calcule l'efficacité pour le débitage"""
        if self.nb_lancements_debitage == 0:
            return 0
        return self.get_poids_debitage_total() / self.nb_lancements_debitage
    
    def recalculate_metrics(self):
        """
        Recalcule toutes les métriques basées sur les lancements de la période
        """
        lancements = Lancement.objects.filter(
            date_lancement__range=[self.date_debut, self.date_fin]
        )
        
        # Calculs généraux
        self.nb_lancements = lancements.count()
        
        # Calculs par type de production
        lancements_assemblage = lancements.filter(type_production='assemblage')
        lancements_debitage = lancements.filter(type_production='debitage')
        
        self.nb_lancements_assemblage = lancements_assemblage.count()
        self.nb_lancements_debitage = lancements_debitage.count()
        
        # Calcul des poids totaux
        from django.db.models import Sum
        
        # Poids assemblage
        assemblage_sum = lancements.aggregate(Sum('poids_assemblage'))
        self.poids_assemblage_total = assemblage_sum['poids_assemblage__sum'] or 0
        
        # Poids débitage 1
        debitage_1_sum = lancements.aggregate(Sum('poids_debitage_1'))
        self.poids_debitage_1_total = debitage_1_sum['poids_debitage_1__sum'] or 0
        
        # Poids débitage 2
        debitage_2_sum = lancements.aggregate(Sum('poids_debitage_2'))
        self.poids_debitage_2_total = debitage_2_sum['poids_debitage_2__sum'] or 0
        
        # Poids total
        self.poids_total = (
            float(self.poids_assemblage_total or 0) + 
            float(self.poids_debitage_1_total or 0) + 
            float(self.poids_debitage_2_total or 0)
        )
        
        self.save()

    class Meta:
        db_table = 'rapport_production'
        verbose_name = 'Rapport de Production'
        verbose_name_plural = 'Rapports de Production'
        ordering = ['-date_debut']
        indexes = [
            models.Index(fields=['date_debut', 'date_fin']),
            models.Index(fields=['type_rapport']),
            models.Index(fields=['created_at']),
        ]