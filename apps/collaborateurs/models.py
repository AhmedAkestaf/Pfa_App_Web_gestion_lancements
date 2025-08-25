from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser


class CollaborateurManager(BaseUserManager):
    """Manager personnalisé pour le modèle Collaborateur"""
    
    def create_user(self, email, nom_collaborateur, prenom_collaborateur, password=None):
        """Crée et sauvegarde un utilisateur avec email et mot de passe"""
        if not email:
            raise ValueError('L\'utilisateur doit avoir une adresse email')
        
        user = self.model(
            email=self.normalize_email(email),
            nom_collaborateur=nom_collaborateur,
            prenom_collaborateur=prenom_collaborateur,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, nom_collaborateur, prenom_collaborateur, password=None):
        """Crée et sauvegarde un superutilisateur"""
        user = self.create_user(
            email=email,
            nom_collaborateur=nom_collaborateur,
            prenom_collaborateur=prenom_collaborateur,
            password=password,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user
    
    def get_by_natural_key(self, email):
        """Méthode requise pour l'authentification Django"""
        return self.get(email=email)

class Collaborateur(AbstractBaseUser):
    """
    Modèle représentant les collaborateurs de l'entreprise.
    Cette classe gère les informations personnelles et professionnelles
    des employés qui travaillent sur les projets et dans les ateliers.
    """
    # Informations personnelles du collaborateur
    nom_collaborateur = models.CharField(max_length=100, verbose_name="Nom")
    prenom_collaborateur = models.CharField(max_length=100, verbose_name="Prénom")
    
    # Email unique pour l'authentification
    email = models.EmailField(unique=True, verbose_name="Email" , default=None ,blank=True , null=True) 
    
    # Champs pour la compatibilité avec Django Admin
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    
    # Timestamps pour le suivi des modifications
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    user_role = models.ForeignKey(
        'core.Role', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Rôle utilisateur"
    )
    
    # Manager personnalisé
    objects = CollaborateurManager()
    
    # Configuration pour l'authentification
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom_collaborateur', 'prenom_collaborateur']
    
    def has_permission(self, module, action):
        """Vérifie si le collaborateur a une permission spécifique"""
        if self.user_role:
            return self.user_role.has_permission(module, action)
        return False
    
    def get_all_permissions(self):
        """Retourne toutes les permissions du collaborateur"""
        if self.user_role:
            return self.user_role.permissions.all()
        return []

    def __str__(self):
        """Retourne le nom complet du collaborateur"""
        return f"{self.nom_collaborateur} {self.prenom_collaborateur}"
    
    def get_full_name(self):
        """Retourne le nom complet du collaborateur"""
        return f"{self.nom_collaborateur} {self.prenom_collaborateur}"
    
    def get_short_name(self):
        """Retourne le prénom du collaborateur"""
        return self.prenom_collaborateur
    
    # Méthodes requises pour Django Admin
    def has_perm(self, perm, obj=None):
        """L'utilisateur a-t-il une permission spécifique?"""
        return True
    
    def has_module_perms(self, app_label):
        """L'utilisateur a-t-il des permissions pour voir l'app app_label?"""
        return True
    
    @property
    def is_staff(self):
        """L'utilisateur est-il membre du staff?"""
        return self.is_admin

    class Meta:
        db_table = 'collaborateur'
        verbose_name = 'Collaborateur'
        verbose_name_plural = 'Collaborateurs'
        ordering = ['nom_collaborateur', 'prenom_collaborateur']

class RoleHistory(models.Model):
    """Historique des changements de rôles"""
    collaborateur = models.ForeignKey(
        'Collaborateur', 
        on_delete=models.CASCADE
    )
    old_role = models.ForeignKey(
        'core.Role', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='old_assignments'
    )
    new_role = models.ForeignKey(
        'core.Role', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='new_assignments'
    )
    changed_by = models.ForeignKey(
        'Collaborateur', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='role_changes_made'
    )
    change_reason = models.TextField(blank=True, verbose_name="Raison du changement")
    changed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Historique des rôles"
        verbose_name_plural = "Historique des rôles"