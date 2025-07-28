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
   # role = models.CharField(max_length=50)   

    email = models.EmailField(unique=True, verbose_name="Email", default= None , blank=True , null=True)

    # Utiliser email comme username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom_collaborateur', 'prenom_collaborateur']
    
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
    
    @property
    def username(self):
        """Propriété pour la compatibilité avec Django Auth"""
        return self.email
    
    def get_full_name(self):
        """Retourne le nom complet du collaborateur"""
        return f"{self.nom_collaborateur} {self.prenom_collaborateur}"
    
    def get_short_name(self):
        """Retourne le prénom du collaborateur"""
        return self.prenom_collaborateur
    
    @property
    def is_anonymous(self):
        """Vérifie si l'utilisateur est anonyme"""
        if not self.email:
            return True
        return False
    
    @property
    def is_authenticated(self):
        """Vérifie si l'utilisateur est authentifié"""
        return self.email is not None and self.password is not None

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