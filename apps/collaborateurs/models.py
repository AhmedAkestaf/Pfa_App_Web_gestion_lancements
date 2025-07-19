from django.db import models

class Collaborateur(models.Model):
    """
    Modèle représentant les collaborateurs de l'entreprise.
    Cette classe gère les informations personnelles et professionnelles
    des employés qui travaillent sur les projets et dans les ateliers.
    """
    # Informations personnelles du collaborateur
    nom_collaborateur = models.CharField(max_length=100, verbose_name="Nom")
    prenom_collaborateur = models.CharField(max_length=100, verbose_name="Prénom")
    
    # Authentification et autorisation
    password = models.CharField(max_length=255, verbose_name="Mot de passe")
    role = models.CharField(max_length=50, choices=[
        ('admin', 'Administrateur'),
        ('manager', 'Manager'),
        ('employee', 'Employé'),
    ], verbose_name="Rôle")
    
    # Timestamps pour le suivi des modifications
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    def __str__(self):
        """Retourne le nom complet du collaborateur"""
        return f"{self.nom_collaborateur} {self.prenom_collaborateur}"

    class Meta:
        db_table = 'collaborateur'
        verbose_name = 'Collaborateur'
        verbose_name_plural = 'Collaborateurs'
        ordering = ['nom_collaborateur', 'prenom_collaborateur']