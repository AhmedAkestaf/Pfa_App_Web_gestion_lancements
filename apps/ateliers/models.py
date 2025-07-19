from django.db import models
from apps.collaborateurs.models import Collaborateur

class Atelier(models.Model):
    """
    Modèle représentant les ateliers de production.
    Chaque atelier a des spécialités, une capacité et un responsable.
    Les ateliers sont les lieux physiques où sont réalisés les travaux.
    """
    # Informations de base de l'atelier
    nom_atelier = models.CharField(max_length=100, verbose_name="Nom de l'atelier")
    type_atelier = models.CharField(max_length=50, choices=[
        ('fabrication', 'Fabrication'),
        ('assemblage', 'Assemblage'),
        ('finition', 'Finition'),
        ('controle', 'Contrôle qualité'),
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
    
    # Capacité maximale de production
    capacite_max = models.IntegerField(default=0, verbose_name="Capacité maximale")
    
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
    Table d'association pour gérer l'affectation des collaborateurs aux ateliers.
    Permet de suivre qui travaille dans quel atelier, avec quel rôle,
    et pendant quelle période. Un collaborateur peut travailler dans plusieurs
    ateliers et un atelier peut avoir plusieurs collaborateurs.
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
    
    # Période d'affectation
    date_affectation = models.DateField(auto_now_add=True, verbose_name="Date d'affectation")
    date_fin_affectation = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Date de fin d'affectation"
    )
    
    # Rôle du collaborateur dans cet atelier
    role_dans_atelier = models.CharField(max_length=50, choices=[
        ('operateur', 'Opérateur'),
        ('chef_equipe', 'Chef d\'équipe'),
        ('technicien', 'Technicien'),
        ('controleur', 'Contrôleur'),
    ], verbose_name="Rôle dans l'atelier")
    
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
    Table d'association pour gérer les compétences/spécialisations des collaborateurs.
    Indique dans quelles catégories chaque collaborateur est compétent,
    avec son niveau de compétence. Permet la gestion des habilitations
    et certifications.
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
    
    # Niveau de compétence dans cette catégorie
    niveau_competence = models.CharField(max_length=20, choices=[
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance', 'Avancé'),
        ('expert', 'Expert'),
    ], verbose_name="Niveau de compétence")
    
    # Date d'obtention de la compétence/certification
    date_certification = models.DateField(auto_now_add=True, verbose_name="Date de certification")
    
    def __str__(self):
        """Retourne la relation collaborateur-catégorie avec le niveau"""
        return f"{self.collaborateur} - {self.categorie} ({self.niveau_competence})"

    class Meta:
        db_table = 'collaborateur_categorie'
        unique_together = ('collaborateur', 'categorie')
        verbose_name = 'Spécialisation Collaborateur-Catégorie'
        verbose_name_plural = 'Spécialisations Collaborateur-Catégorie'


class AtelierCategorie(models.Model):
    """
    Table d'association pour définir les capacités des ateliers par catégorie.
    Indique quelles catégories de produits/services peuvent être traitées
    dans chaque atelier, avec quelle capacité et en combien de temps.
    Permet la planification et l'optimisation des ressources.
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
    
    # Capacité de traitement pour cette catégorie dans cet atelier
    capacite_categorie = models.IntegerField(
        default=0, 
        verbose_name="Capacité pour cette catégorie"
    )
    
    # Temps moyen de traitement en heures
    temps_moyen_traitement = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Temps moyen de traitement (heures)"
    )
    
    def __str__(self):
        """Retourne la relation atelier-catégorie"""
        return f"{self.atelier} - {self.categorie}"

    class Meta:
        db_table = 'atelier_categorie'
        unique_together = ('atelier', 'categorie')
        verbose_name = 'Capacité Atelier-Catégorie'
        verbose_name_plural = 'Capacités Atelier-Catégorie'