from django.db import models
from apps.collaborateurs.models import Collaborateur

class Affaire(models.Model):
    """
    Modèle représentant les projets/contrats clients.
    Une affaire est un projet global qui peut contenir plusieurs lancements.
    Elle représente l'engagement commercial avec un client.
    """
    # Identifiant unique de l'affaire
    code_affaire = models.CharField(max_length=50, unique=True, verbose_name="Code affaire")
    
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