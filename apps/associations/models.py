from django.db import models
from apps.core.models import Affaire
from apps.ateliers.models import Categorie

class AffaireCategorie(models.Model):
    """
    Table d'association pour gérer les catégories liées aux affaires.
    Relation many-to-many entre affaires et catégories.
    """
    # Relations vers les tables principales
    affaire = models.ForeignKey(
        Affaire, 
        on_delete=models.CASCADE,
        related_name='affaire_categories',
        verbose_name="Affaire"
    )
    categorie = models.ForeignKey(
        Categorie, 
        on_delete=models.CASCADE,
        related_name='affaire_categories',
        verbose_name="Catégorie"
    )
    
    # Métadonnées (optionnelles)
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    
    def __str__(self):
        """Retourne la relation affaire-catégorie"""
        return f"{self.affaire.code_affaire} - {self.categorie.nom_categorie}"

    class Meta:
        db_table = 'affaire_categorie'
        unique_together = ('affaire', 'categorie')
        verbose_name = 'Association Affaire-Catégorie'
        verbose_name_plural = 'Associations Affaire-Catégorie'
        ordering = ['affaire__code_affaire', 'categorie__nom_categorie']


from apps.ateliers.models import (
    CollaborateurAtelier,
    CollaborateurCategorie,
    AtelierCategorie,
    Atelier,
    Categorie
)

# Réexportation pour faciliter l'importation
__all__ = [
    'CollaborateurAtelier',
    'CollaborateurCategorie', 
    'AtelierCategorie',
    'Atelier',
    'Categorie',
    'AffaireCategorie'
]