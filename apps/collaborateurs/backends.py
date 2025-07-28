from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from .models import Collaborateur

class CollaborateurBackend(BaseBackend):
    """
    Backend d'authentification personnalisé pour le modèle Collaborateur
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authentifie un collaborateur avec son email et mot de passe
        """
        if username is None or password is None:
            return None
            
        try:
            # Rechercher le collaborateur par email
            collaborateur = Collaborateur.objects.get(email=username)
            
            # Vérifier le mot de passe
            if check_password(password, collaborateur.password):
                return collaborateur
                
        except Collaborateur.DoesNotExist:
            # Si l'utilisateur n'existe pas, on retourne None
            return None
            
        return None
    
    def get_user(self, user_id):
        """
        Récupère un utilisateur par son ID
        """
        try:
            return Collaborateur.objects.get(pk=user_id)
        except Collaborateur.DoesNotExist:
            return None