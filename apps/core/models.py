from django.db import models
from apps.collaborateurs.models import Collaborateur
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone


class Affaire(models.Model):
    """
    Modèle représentant les projets/contrats clients.
    Une affaire est un projet global qui peut contenir plusieurs lancements.
    Elle représente l'engagement commercial avec un client.
    """
    # Identifiant unique de l'affaire (SEUL CHAMP OBLIGATOIRE)
    code_affaire = models.CharField(max_length=50, unique=False, verbose_name="Code affaire")
    
    # Informations sur le livrable et le client (OPTIONNELS)
    livrable = models.TextField(blank=True, null=True, verbose_name="Nom du livrable")
    client = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nom du client")
    
    # Responsable commercial de l'affaire (OPTIONNEL)
    responsable_affaire = models.ForeignKey(
        Collaborateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='affaires_responsable',
        verbose_name="Responsable de l'affaire"
    )
    
    # Planification temporelle (OPTIONNELLE)
    date_debut = models.DateField(blank=True, null=True, verbose_name="Date de début")
    date_fin_prevue = models.DateField(blank=True, null=True, verbose_name="Date de fin prévue")
    
    # Suivi du statut de l'affaire (SIMPLIFIÉ - seulement 2 choix)
    statut = models.CharField(max_length=20, choices=[
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
    ], default='en_cours', verbose_name="Statut")
    
    # Date de création
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    def __str__(self):
        """Retourne le code de l'affaire et le client si disponible"""
        if self.client:
            return f"{self.code_affaire} - {self.client}"
        return f"{self.code_affaire}"

    def is_complete(self):
        """Vérifie si l'affaire a tous les champs remplis"""
        return all([
            self.client,
            self.livrable,
            self.responsable_affaire,
            self.date_debut,
            self.date_fin_prevue
        ])
    
    def get_missing_fields(self):
        """Retourne la liste des champs manquants"""
        missing = []
        if not self.client:
            missing.append('Client')
        if not self.livrable:
            missing.append('Description du livrable')
        if not self.responsable_affaire:
            missing.append('Responsable de l\'affaire')
        if not self.date_debut:
            missing.append('Date de début')
        if not self.date_fin_prevue:
            missing.append('Date de fin prévue')
        return missing
    
    @property
    def completion_percentage(self):
        """Calcule le pourcentage de completion de l'affaire"""
        total_fields = 5  # client, livrable, responsable, date_debut, date_fin_prevue
        completed_fields = total_fields - len(self.get_missing_fields())
        return (completed_fields / total_fields) * 100

    class Meta:
        db_table = 'affaire'
        verbose_name = 'Affaire'
        verbose_name_plural = 'Affaires'
        ordering = ['-date_debut', '-created_at']


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
    
class Notification(models.Model):
    """
    Modèle pour gérer les notifications utilisateur
    """
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Succès'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
        ('system', 'Système'),
    ]
    
    # Destinataire de la notification
    destinataire = models.ForeignKey(
        Collaborateur, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        verbose_name="Destinataire"
    )
    
    # Type et contenu de la notification
    type_notification = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPES, 
        default='info',
        verbose_name="Type"
    )
    titre = models.CharField(max_length=200, verbose_name="Titre")
    message = models.TextField(verbose_name="Message")
    
    # État de la notification
    lu = models.BooleanField(default=False, verbose_name="Lu")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_lecture = models.DateTimeField(null=True, blank=True, verbose_name="Date de lecture")
    
    # Lien optionnel vers une page
    url_action = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        verbose_name="URL d'action"
    )
    
    # Métadonnées pour les notifications automatiques
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        null=True, 
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    objet_lie = GenericForeignKey('content_type', 'object_id')
    
    # Expiration de la notification
    date_expiration = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Date d'expiration"
    )
    
    class Meta:
        db_table = 'notification'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['destinataire', 'lu']),
            models.Index(fields=['date_creation']),
            models.Index(fields=['type_notification']),
        ]
    
    def __str__(self):
        return f"{self.titre} - {self.destinataire.get_full_name()}"
    
    def marquer_comme_lu(self):
        """Marque la notification comme lue"""
        if not self.lu:
            self.lu = True
            self.date_lecture = timezone.now()
            self.save(update_fields=['lu', 'date_lecture'])
    
    @property
    def is_expired(self):
        """Vérifie si la notification a expiré"""
        if self.date_expiration:
            return timezone.now() > self.date_expiration
        return False
    
    def get_icon_class(self):
        """Retourne la classe CSS pour l'icône selon le type"""
        icons = {
            'info': 'fas fa-info-circle text-info',
            'success': 'fas fa-check-circle text-success',
            'warning': 'fas fa-exclamation-triangle text-warning',
            'error': 'fas fa-exclamation-circle text-danger',
            'system': 'fas fa-cog text-secondary',
        }
        return icons.get(self.type_notification, 'fas fa-bell')
    
    def get_time_ago(self):
        """Retourne le temps écoulé depuis la création"""
        from django.utils.timesince import timesince
        return timesince(self.date_creation)


class Activite(models.Model):
    """
    Modèle pour enregistrer les activités/historique du système
    """
    ACTIONS = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
        ('assign', 'Assignation'),
        ('status_change', 'Changement de statut'),
        ('export', 'Export'),
        ('import', 'Import'),
    ]
    
    MODULES = [
        ('collaborateurs', 'Collaborateurs'),
        ('ateliers', 'Ateliers'),
        ('categories', 'Catégories'),
        ('affaires', 'Affaires'),
        ('lancements', 'Lancements'),
        ('rapports', 'Rapports'),
        ('administration', 'Administration'),
        ('system', 'Système'),
    ]
    
    # Utilisateur qui a effectué l'action
    utilisateur = models.ForeignKey(
        Collaborateur, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='activites',
        verbose_name="Utilisateur"
    )
    
    # Description de l'activité
    action = models.CharField(max_length=20, choices=ACTIONS, verbose_name="Action")
    module = models.CharField(max_length=50, choices=MODULES, verbose_name="Module")
    description = models.TextField(verbose_name="Description")
    
    # Objet concerné par l'activité
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        null=True, 
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    objet_lie = GenericForeignKey('content_type', 'object_id')
    
    # Métadonnées
    adresse_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    user_agent = models.TextField(blank=True, null=True, verbose_name="User Agent")
    
    # Données supplémentaires (JSON)
    donnees_avant = models.JSONField(null=True, blank=True, verbose_name="Données avant")
    donnees_après = models.JSONField(null=True, blank=True, verbose_name="Données après")
    
    # Timestamp
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date")
    
    class Meta:
        db_table = 'activite'
        verbose_name = 'Activité'
        verbose_name_plural = 'Activités'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['date_creation']),
            models.Index(fields=['utilisateur', 'date_creation']),
            models.Index(fields=['module', 'action']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        user_name = self.utilisateur.get_full_name() if self.utilisateur else "Système"
        return f"{user_name} - {self.get_action_display()} - {self.description}"
    
    def get_icon_class(self):
        """Retourne la classe CSS pour l'icône selon l'action"""
        icons = {
            'create': 'fas fa-plus-circle text-success',
            'update': 'fas fa-edit text-warning',
            'delete': 'fas fa-trash-alt text-danger',
            'login': 'fas fa-sign-in-alt text-info',
            'logout': 'fas fa-sign-out-alt text-secondary',
            'assign': 'fas fa-user-cog text-primary',
            'status_change': 'fas fa-exchange-alt text-info',
            'export': 'fas fa-download text-success',
            'import': 'fas fa-upload text-primary',
        }
        return icons.get(self.action, 'fas fa-info-circle')
    
    def get_time_ago(self):
        """Retourne le temps écoulé depuis la création"""
        from django.utils.timesince import timesince
        return timesince(self.date_creation)
    
    @classmethod
    def log_activity(cls, utilisateur, action, module, description, objet=None, request=None, donnees_avant=None, donnees_après=None):
        """
        Méthode utilitaire pour enregistrer une activité
        """
        activity_data = {
            'utilisateur': utilisateur,
            'action': action,
            'module': module,
            'description': description,
            'donnees_avant': donnees_avant,
            'donnees_après': donnees_après,
        }
        
        # Ajouter l'objet lié si fourni
        if objet:
            activity_data['content_type'] = ContentType.objects.get_for_model(objet)
            activity_data['object_id'] = objet.pk
        
        # Ajouter les données de la requête si disponible
        if request:
            activity_data['adresse_ip'] = cls.get_client_ip(request)
            activity_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return cls.objects.create(**activity_data)
    
    @staticmethod
    def get_client_ip(request):
        """Récupère l'adresse IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PreferenceNotification(models.Model):
    """
    Modèle pour gérer les préférences de notification des utilisateurs
    """
    utilisateur = models.OneToOneField(
        Collaborateur, 
        on_delete=models.CASCADE, 
        related_name='preferences_notification'
    )
    
    # Types de notifications activées
    notifications_lancements = models.BooleanField(default=True, verbose_name="Notifications lancements")
    notifications_affaires = models.BooleanField(default=True, verbose_name="Notifications affaires")
    notifications_systeme = models.BooleanField(default=True, verbose_name="Notifications système")
    notifications_email = models.BooleanField(default=False, verbose_name="Notifications par email")
    
    # Fréquence des notifications groupées
    FREQUENCES = [
        ('immediate', 'Immédiate'),
        ('hourly', 'Toutes les heures'),
        ('daily', 'Quotidienne'),
        ('weekly', 'Hebdomadaire'),
        ('none', 'Aucune'),
    ]
    frequence_resume = models.CharField(
        max_length=20, 
        choices=FREQUENCES, 
        default='daily',
        verbose_name="Fréquence du résumé"
    )
    
    # Heures de non-dérangement
    heure_debut_silencieux = models.TimeField(
        null=True, 
        blank=True, 
        verbose_name="Début période silencieuse"
    )
    heure_fin_silencieux = models.TimeField(
        null=True, 
        blank=True, 
        verbose_name="Fin période silencieuse"
    )
    
    class Meta:
        db_table = 'preference_notification'
        verbose_name = 'Préférence de notification'
        verbose_name_plural = 'Préférences de notification'
    