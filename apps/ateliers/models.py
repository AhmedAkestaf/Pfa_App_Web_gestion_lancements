from django.db import models
from apps.collaborateurs.models import Collaborateur

class Atelier(models.Model):
    """
    Modèle représentant les ateliers de production.
    Chaque atelier a des spécialités et un responsable.
    Les ateliers sont les lieux physiques où sont réalisés les travaux.
    """
    # Informations de base de l'atelier
    nom_atelier = models.CharField(max_length=100, verbose_name="Nom de l'atelier")
    type_atelier = models.CharField(max_length=50, choices=[
        ('fabrication', 'Fabrication'),
        ('assemblage', 'Assemblage'),
        ('finition', 'Finition'),
        ('controle', 'Contrôle qualité'),
        ('debitage', 'Débitage'),
    ], verbose_name="Type d'atelier")
    
    # Responsable de l'atelier (relation avec Collaborateur)
    responsable_atelier = models.ForeignKey(
        Collaborateur, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='ateliers_responsable',
        verbose_name="Responsable de l'atelier"
    )
    
    # Date de création
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    def __str__(self):
        """Retourne le nom de l'atelier"""
        return self.nom_atelier

    class Meta:
        db_table = 'atelier'
        verbose_name = 'Atelier'
        verbose_name_plural = 'Ateliers'
        ordering = ['nom_atelier']


class Categorie(models.Model):
    """
    Modèle représentant les catégories de produits ou de services.
    Les catégories permettent de classifier les différents types de travaux
    réalisés dans les ateliers (ex: soudure, usinage, assemblage, etc.).
    """
    # Nom unique de la catégorie
    nom_categorie = models.CharField(max_length=100, unique=True, verbose_name="Nom de la catégorie")
    
    # Description détaillée de la catégorie
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    
    # Date de création pour le suivi
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    def __str__(self):
        """Retourne le nom de la catégorie"""
        return self.nom_categorie

    class Meta:
        db_table = 'categorie'
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'
        ordering = ['nom_categorie']


class CollaborateurAtelier(models.Model):
    """
    Table d'association simplifiée pour gérer l'affectation des collaborateurs aux ateliers.
    Relation many-to-many simple entre collaborateurs et ateliers.
    """
    # Relations vers les tables principales
    collaborateur = models.ForeignKey(
        Collaborateur, 
        on_delete=models.CASCADE,
        verbose_name="Collaborateur"
    )
    atelier = models.ForeignKey(
        Atelier, 
        on_delete=models.CASCADE,
        verbose_name="Atelier"
    )
    
    def __str__(self):
        """Retourne la relation collaborateur-atelier"""
        return f"{self.collaborateur} - {self.atelier}"

    class Meta:
        db_table = 'collaborateur_atelier'
        unique_together = ('collaborateur', 'atelier')
        verbose_name = 'Affectation Collaborateur-Atelier'
        verbose_name_plural = 'Affectations Collaborateur-Atelier'


class CollaborateurCategorie(models.Model):
    """
    Table d'association simplifiée pour gérer les compétences/spécialisations des collaborateurs.
    Relation many-to-many simple entre collaborateurs et catégories.
    """
    # Relations vers les tables principales
    collaborateur = models.ForeignKey(
        Collaborateur, 
        on_delete=models.CASCADE,
        verbose_name="Collaborateur"
    )
    categorie = models.ForeignKey(
        Categorie, 
        on_delete=models.CASCADE,
        verbose_name="Catégorie"
    )
    
    def __str__(self):
        """Retourne la relation collaborateur-catégorie"""
        return f"{self.collaborateur} - {self.categorie}"

    class Meta:
        db_table = 'collaborateur_categorie'
        unique_together = ('collaborateur', 'categorie')
        verbose_name = 'Spécialisation Collaborateur-Catégorie'
        verbose_name_plural = 'Spécialisations Collaborateur-Catégorie'


class AtelierCategorie(models.Model):
    """
    Table d'association simplifiée pour définir les relations entre ateliers et catégories.
    Relation many-to-many simple entre ateliers et catégories.
    """
    # Relations vers les tables principales
    atelier = models.ForeignKey(
        Atelier, 
        on_delete=models.CASCADE,
        verbose_name="Atelier"
    )
    categorie = models.ForeignKey(
        Categorie, 
        on_delete=models.CASCADE,
        verbose_name="Catégorie"
    )
    
    def __str__(self):
        """Retourne la relation atelier-catégorie"""
        return f"{self.atelier} - {self.categorie}"

    class Meta:
        db_table = 'atelier_categorie'
        unique_together = ('atelier', 'categorie')
        verbose_name = 'Relation Atelier-Catégorie'
        verbose_name_plural = 'Relations Atelier-Catégorie'