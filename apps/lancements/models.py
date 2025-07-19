from django.db import models
from apps.collaborateurs.models import Collaborateur
from apps.ateliers.models import Atelier, Categorie
from apps.core.models import Affaire

class Lancement(models.Model):
    """
    Modèle central représentant un lancement de production.
    C'est la table principale qui lie tous les autres éléments :
    - Un lancement appartient à une affaire
    - Il est traité dans un atelier spécifique
    - Par un collaborateur donné
    - Pour une catégorie de produit/service
    Cette table contient aussi les informations de production (poids, dates, etc.).
    """
    # Identifiant unique du lancement
    num_lanc = models.CharField(max_length=50, unique=True, verbose_name="Numéro de lancement")
    
    # Dates importantes du processus
    date_reception = models.DateField(verbose_name="Date de réception")
    date_lancement = models.DateField(verbose_name="Date de lancement")
    
    # Description du sous-livrable
    sous_livrable = models.TextField(verbose_name="Description du sous-livrable")
    
    # Données de production (poids en kg)
    poids_debitage = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="Poids débitage (kg)"
    )
    poids_assemblage = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="Poids assemblage (kg)"
    )
    
    # Notes et observations
    observations = models.TextField(blank=True, null=True, verbose_name="Observations")
    
    # ===== RELATIONS AVEC LES AUTRES TABLES =====
    # Atelier où sera traité le lancement
    atelier = models.ForeignKey(
        Atelier, 
        on_delete=models.CASCADE, 
        related_name='lancements',
        verbose_name="Atelier"
    )
    
    # Catégorie du produit/service à réaliser
    categorie = models.ForeignKey(
        Categorie, 
        on_delete=models.CASCADE, 
        related_name='lancements',
        verbose_name="Catégorie"
    )
    
    # Collaborateur responsable de ce lancement
    collaborateur = models.ForeignKey(
        Collaborateur, 
        on_delete=models.CASCADE, 
        related_name='lancements',
        verbose_name="Collaborateur responsable"
    )
    
    # Affaire parent à laquelle appartient ce lancement
    affaire = models.ForeignKey(
        Affaire, 
        on_delete=models.CASCADE, 
        related_name='lancements',
        verbose_name="Affaire"
    )
    
    # Statut du lancement pour le suivi de production
    statut = models.CharField(max_length=20, choices=[
        ('planifie', 'Planifié'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('en_attente', 'En attente'),
    ], default='planifie', verbose_name="Statut")
    
    # Timestamps pour le suivi
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    def __str__(self):
        """Retourne le numéro de lancement"""
        return f"Lancement {self.num_lanc}"

    def get_poids_total(self):
        """Méthode pour calculer le poids total"""
        return self.poids_debitage + self.poids_assemblage

    class Meta:
        db_table = 'lancement'
        verbose_name = 'Lancement'
        verbose_name_plural = 'Lancements'
        ordering = ['-date_lancement']