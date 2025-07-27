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
    role = models.CharField(max_length=50)   
    
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