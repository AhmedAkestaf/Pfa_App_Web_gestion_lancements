# apps/lancements/models.py - MODIFIÉ avec associations automatiques

from django.db import models
from apps.collaborateurs.models import Collaborateur
from apps.ateliers.models import Atelier, Categorie
from apps.core.models import Affaire
import logging

# Configuration du logger
logger = logging.getLogger(__name__)

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
    num_lanc = models.CharField(max_length=50, unique=False, verbose_name="Numéro de lancement")
    
    # Dates importantes du processus
    date_reception = models.DateField(verbose_name="Date de réception")
    date_lancement = models.DateField(blank=True, null=True, verbose_name="Date de lancement prévue")    
    # Description du sous-livrable
    sous_livrable = models.TextField(verbose_name="Description du sous-livrable")
    
    # Données de production (poids en kg)
    poids_debitage = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        default=0, 
        verbose_name="Poids débitage (kg)"
    )
    poids_assemblage = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
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
        """Méthode pour calculer le poids total avec gestion des erreurs"""
        try:
            poids_debitage = float(self.poids_debitage or 0)
            poids_assemblage = float(self.poids_assemblage or 0)
            return poids_debitage + poids_assemblage
        except (ValueError, TypeError):
            return 0.0
    
    def get_poids_total_display(self):
        """Retourne le poids total formaté pour l'affichage"""
        return f"{self.get_poids_total():.2f} kg"

    def get_absolute_url(self):
        """URL pour accéder au détail du lancement"""
        from django.urls import reverse
        return reverse('lancements:detail', kwargs={'pk': self.pk})

    @property
    def is_en_retard(self):
        """Vérifie si le lancement est en retard par rapport à la date prévue"""
        from django.utils import timezone
        if self.statut in ['termine']:
            return False
        return self.date_lancement < timezone.now().date()

    def create_associations(self):
        """
        Crée automatiquement les associations dans les tables :
        - CollaborateurAtelier
        - CollaborateurCategorie  
        - AtelierCategorie
        """
        try:
            # Import des modèles d'association
            from apps.ateliers.models import (
                CollaborateurAtelier, 
                CollaborateurCategorie, 
                AtelierCategorie
            )
            
            # Vérifier que tous les éléments nécessaires sont présents
            if not all([self.collaborateur_id, self.atelier_id, self.categorie_id]):
                logger.warning(f"⚠️ Données manquantes pour créer les associations du lancement {self.num_lanc}")
                return
            
            associations_created = 0
            
            # 1. ASSOCIATION COLLABORATEUR-ATELIER
            try:
                collab_atelier, created = CollaborateurAtelier.objects.get_or_create(
                    collaborateur_id=self.collaborateur_id,
                    atelier_id=self.atelier_id
                )
                if created:
                    associations_created += 1
                    logger.info(f"✅ Association CollaborateurAtelier créée : "
                               f"Collaborateur({self.collaborateur_id}) ↔ Atelier({self.atelier_id})")
            except Exception as e:
                logger.error(f"❌ Erreur création CollaborateurAtelier : {str(e)}")
            
            # 2. ASSOCIATION COLLABORATEUR-CATEGORIE
            try:
                collab_categorie, created = CollaborateurCategorie.objects.get_or_create(
                    collaborateur_id=self.collaborateur_id,
                    categorie_id=self.categorie_id
                )
                if created:
                    associations_created += 1
                    logger.info(f"✅ Association CollaborateurCategorie créée : "
                               f"Collaborateur({self.collaborateur_id}) ↔ Categorie({self.categorie_id})")
            except Exception as e:
                logger.error(f"❌ Erreur création CollaborateurCategorie : {str(e)}")
            
            # 3. ASSOCIATION ATELIER-CATEGORIE
            try:
                atelier_categorie, created = AtelierCategorie.objects.get_or_create(
                    atelier_id=self.atelier_id,
                    categorie_id=self.categorie_id
                )
                if created:
                    associations_created += 1
                    logger.info(f"✅ Association AtelierCategorie créée : "
                               f"Atelier({self.atelier_id}) ↔ Categorie({self.categorie_id})")
            except Exception as e:
                logger.error(f"❌ Erreur création AtelierCategorie : {str(e)}")
            
            # Log du résumé
            logger.info(f"📊 Lancement {self.num_lanc} : {associations_created} nouvelles associations créées")
            
        except Exception as e:
            logger.error(f"❌ Erreur générale lors de la création des associations pour {self.num_lanc} : {str(e)}")

    def save(self, *args, **kwargs):
        """
        Méthode save() personnalisée pour créer automatiquement les associations
        """
        # Sauvegarder d'abord le lancement
        super().save(*args, **kwargs)
        
        # Puis créer les associations automatiquement
        self.create_associations()

    class Meta:
        db_table = 'lancement'
        verbose_name = 'Lancement'
        verbose_name_plural = 'Lancements'
        ordering = ['-date_lancement', '-created_at']
        indexes = [
            models.Index(fields=['date_lancement']),
            models.Index(fields=['statut']),
            models.Index(fields=['affaire']),
            models.Index(fields=['atelier']),
        ]