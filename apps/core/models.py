from django.db import models
from apps.collaborateurs.models import Collaborateur
from django.contrib.auth.models import AbstractUser


class Affaire(models.Model):
    """
    Modèle représentant les projets/contrats clients.
    Une affaire est un projet global qui peut contenir plusieurs lancements.
    Elle représente l'engagement commercial avec un client.
    """
    # Identifiant unique de l'affaire
    code_affaire = models.CharField(max_length=50, unique=False, verbose_name="Code affaire")
    
    # Informations sur le livrable et le client
    livrable = models.TextField(verbose_name="Description du livrable")
    client = models.CharField(max_length=100, verbose_name="Nom du client")
    
    # Responsable commercial de l'affaire
    responsable_affaire = models.ForeignKey(
        Collaborateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='affaires_responsable',
        verbose_name="Responsable de l'affaire"
    )
    
    # Planification temporelle
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin_prevue = models.DateField(verbose_name="Date de fin prévue")
    
    # Suivi du statut de l'affaire
    statut = models.CharField(max_length=20, choices=[
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('suspendue', 'Suspendue'),
        ('annulee', 'Annulée'),
    ], default='en_cours', verbose_name="Statut")
    
    # Date de création
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    def __str__(self):
        """Retourne le code de l'affaire et le client"""
        return f"{self.code_affaire} - {self.client}"

    class Meta:
        db_table = 'affaire'
        verbose_name = 'Affaire'
        verbose_name_plural = 'Affaires'
        ordering = ['-date_debut']

class Permission(models.Model):
    """Modèle pour définir les permissions système"""
    
    # Modules de l'application
    MODULE_CHOICES = [
        ('collaborateurs', 'Collaborateurs'),
        ('ateliers', 'Ateliers'),
        ('categories', 'Catégories'),
        ('affaires', 'Affaires'),
        ('lancements', 'Lancements'),
        ('rapports', 'Rapports'),
        ('administration', 'Administration'),
    ]
    
    # Actions possibles
    ACTION_CHOICES = [
        ('create', 'Créer'),
        ('read', 'Lire'),
        ('update', 'Modifier'),
        ('delete', 'Supprimer'),
        ('assign', 'Assigner'),
        ('export', 'Exporter'),
    ]
    
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom de la permission")
    module = models.CharField(max_length=50, choices=MODULE_CHOICES, verbose_name="Module")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Action")
    description = models.TextField(blank=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('module', 'action')
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
    
    def __str__(self):
        return f"{self.get_module_display()} - {self.get_action_display()}"


class Role(models.Model):
    """Modèle pour définir les rôles utilisateur"""
    
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom du rôle")
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    is_system_role = models.BooleanField(default=False, verbose_name="Rôle système")
    permissions = models.ManyToManyField(Permission, blank=True, verbose_name="Permissions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"
    
    def __str__(self):
        return self.name
    
    def get_permissions_by_module(self):
        """Retourne les permissions groupées par module"""
        permissions_dict = {}
        for perm in self.permissions.all():
            if perm.module not in permissions_dict:
                permissions_dict[perm.module] = []
            permissions_dict[perm.module].append(perm.action)
        return permissions_dict
    
    def has_permission(self, module, action):
        """Vérifie si le rôle a une permission spécifique"""
        return self.permissions.filter(module=module, action=action).exists() 
    