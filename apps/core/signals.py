# apps/core/signals.py - VERSION CORRIGÉE COMPLÈTE

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.contenttypes.models import ContentType
from .models import Notification, Activite, Affaire
from apps.collaborateurs.models import Collaborateur
import threading

# Variable pour stocker les données avant modification
_thread_locals = threading.local()


def get_current_request():
    """Récupère la requête courante depuis le middleware"""
    return getattr(_thread_locals, 'request', None)


def set_current_request(request):
    """Stocke la requête courante pour les signaux"""
    _thread_locals.request = request


class NotificationService:
    """Service pour créer des notifications intelligentes"""
    
    @staticmethod
    def creer_notification_pour_role(role_name, type_notif, titre, message, url_action=None, objet=None):
        """Crée des notifications pour tous les utilisateurs ayant un rôle spécifique"""
        try:
            from apps.core.models import Role
            role = Role.objects.get(name=role_name)
            collaborateurs = Collaborateur.objects.filter(user_role=role, is_active=True)
            
            notifications = []
            for collaborateur in collaborateurs:
                notification = Notification(
                    destinataire=collaborateur,
                    type_notification=type_notif,
                    titre=titre,
                    message=message,
                    url_action=url_action
                )
                
                if objet:
                    notification.content_type = ContentType.objects.get_for_model(objet)
                    notification.object_id = objet.pk
                
                notifications.append(notification)
            
            if notifications:  # CORRECTION: Vérifier avant bulk_create
                Notification.objects.bulk_create(notifications)
            return len(notifications)
        except Exception as e:
            print(f"Erreur lors de la création des notifications pour le rôle {role_name}: {e}")
            return 0
    
    @staticmethod
    def creer_notification_individuelle(utilisateur, type_notif, titre, message, url_action=None, objet=None):
        """Crée une notification pour un utilisateur spécifique"""
        try:
            notification = Notification.objects.create(
                destinataire=utilisateur,
                type_notification=type_notif,
                titre=titre,
                message=message,
                url_action=url_action
            )
            
            if objet:
                notification.content_type = ContentType.objects.get_for_model(objet)
                notification.object_id = objet.pk
                notification.save()
            
            return notification
        except Exception as e:
            print(f"Erreur lors de la création de la notification: {e}")
            return None


# ========== SIGNAUX POUR LES ACTIVITÉS ==========

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Enregistre les connexions utilisateur"""
    try:
        # CORRECTION: Gérer le fait que user EST un Collaborateur (AUTH_USER_MODEL)
        utilisateur = user if isinstance(user, Collaborateur) else getattr(user, 'collaborateur', None)
        
        if utilisateur:
            Activite.log_activity(
                utilisateur=utilisateur,
                action='login',
                module='system',
                description=f"Connexion de {user.get_full_name() if hasattr(user, 'get_full_name') else str(user)}",
                request=request
            )
    except Exception as e:
        print(f"Erreur lors de l'enregistrement de la connexion: {e}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Enregistre les déconnexions utilisateur"""
    if user:
        try:
            # CORRECTION: Même logique pour la déconnexion
            utilisateur = user if isinstance(user, Collaborateur) else getattr(user, 'collaborateur', None)
            
            if utilisateur:
                Activite.log_activity(
                    utilisateur=utilisateur,
                    action='logout',
                    module='system',
                    description=f"Déconnexion de {user.get_full_name() if hasattr(user, 'get_full_name') else str(user)}",
                    request=request
                )
        except Exception as e:
            print(f"Erreur lors de l'enregistrement de la déconnexion: {e}")


# ========== SIGNAUX POUR LES LANCEMENTS ==========

@receiver(pre_save, sender='lancements.Lancement')  # CORRECTION: Utilisation du string pour éviter l'import circulaire
def store_lancement_before_save(sender, instance, **kwargs):
    """Stocke les données avant modification d'un lancement"""
    if instance.pk:
        try:
            from apps.lancements.models import Lancement
            old_instance = Lancement.objects.get(pk=instance.pk)
            _thread_locals.old_lancement = {
                'num_lanc': old_instance.num_lanc,
                'statut': old_instance.statut,
                'atelier': str(old_instance.atelier),
                'collaborateur': str(old_instance.collaborateur),
                'poids_debitage': float(old_instance.poids_debitage) if old_instance.poids_debitage else 0,
                'poids_assemblage': float(old_instance.poids_assemblage) if old_instance.poids_assemblage else 0,
            }
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des données avant modification: {e}")
            _thread_locals.old_lancement = None


@receiver(post_save, sender='lancements.Lancement')
def handle_lancement_save(sender, instance, created, **kwargs):
    """Gère la création/modification des lancements"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # CORRECTION: Récupérer le bon utilisateur
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        if created:
            # Nouveau lancement créé
            Activite.log_activity(
                utilisateur=utilisateur,
                action='create',
                module='lancements',
                description=f"Création du lancement {instance.num_lanc} pour l'affaire {instance.affaire.code_affaire if instance.affaire else 'N/A'}",
                objet=instance,
                request=request
            )
            
            # Notification au responsable de l'atelier
            if hasattr(instance, 'atelier') and instance.atelier and hasattr(instance.atelier, 'responsable_atelier') and instance.atelier.responsable_atelier:
                NotificationService.creer_notification_individuelle(
                    utilisateur=instance.atelier.responsable_atelier,
                    type_notif='info',
                    titre='Nouveau lancement assigné',
                    message=f'Le lancement {instance.num_lanc} a été assigné à votre atelier {instance.atelier.nom_atelier}',
                    url_action=f'/lancements/{instance.pk}/',
                    objet=instance
                )
            
            # Notification au collaborateur assigné
            if hasattr(instance, 'collaborateur') and instance.collaborateur and instance.collaborateur != utilisateur:
                NotificationService.creer_notification_individuelle(
                    utilisateur=instance.collaborateur,
                    type_notif='success',
                    titre='Nouveau lancement assigné',
                    message=f'Le lancement {instance.num_lanc} vous a été assigné',
                    url_action=f'/lancements/{instance.pk}/',
                    objet=instance
                )
            
            # Notification aux managers pour les gros lancements
            if hasattr(instance, 'get_poids_total'):
                try:
                    poids_total = instance.get_poids_total()
                    if poids_total > 1000:  # Plus d'une tonne
                        NotificationService.creer_notification_pour_role(
                            role_name='Manager',
                            type_notif='warning',
                            titre='Lancement important créé',
                            message=f'Lancement {instance.num_lanc} créé avec un poids de {poids_total:.2f} kg',
                            url_action=f'/lancements/{instance.pk}/',
                            objet=instance
                        )
                except Exception as e:
                    print(f"Erreur lors du calcul du poids total: {e}")
        
        else:
            # Lancement modifié
            old_data = getattr(_thread_locals, 'old_lancement', {})
            changes = []
            
            # Détecter les changements significatifs
            if old_data.get('statut') != instance.statut:
                changes.append(f"Statut: {old_data.get('statut')} → {instance.statut}")
                
                # Notification spéciale pour changement de statut
                if instance.statut == 'termine':
                    NotificationService.creer_notification_pour_role(
                        role_name='Manager',
                        type_notif='success',
                        titre='Lancement terminé',
                        message=f'Le lancement {instance.num_lanc} a été marqué comme terminé',
                        url_action=f'/lancements/{instance.pk}/',
                        objet=instance
                    )
            
            if old_data.get('collaborateur') != str(instance.collaborateur):
                changes.append(f"Collaborateur: {old_data.get('collaborateur')} → {instance.collaborateur}")
                
                # Notification au nouveau collaborateur
                if hasattr(instance, 'collaborateur') and instance.collaborateur:
                    NotificationService.creer_notification_individuelle(
                        utilisateur=instance.collaborateur,
                        type_notif='info',
                        titre='Lancement réassigné',
                        message=f'Le lancement {instance.num_lanc} vous a été réassigné',
                        url_action=f'/lancements/{instance.pk}/',
                        objet=instance
                    )
            
            if changes:
                Activite.log_activity(
                    utilisateur=utilisateur,
                    action='update',
                    module='lancements',
                    description=f"Modification du lancement {instance.num_lanc}: {', '.join(changes)}",
                    objet=instance,
                    request=request,
                    donnees_avant=old_data,
                    donnees_après={
                        'num_lanc': instance.num_lanc,
                        'statut': instance.statut,
                        'atelier': str(instance.atelier) if hasattr(instance, 'atelier') else '',
                        'collaborateur': str(instance.collaborateur) if hasattr(instance, 'collaborateur') else '',
                        'poids_debitage': float(instance.poids_debitage) if hasattr(instance, 'poids_debitage') and instance.poids_debitage else 0,
                        'poids_assemblage': float(instance.poids_assemblage) if hasattr(instance, 'poids_assemblage') and instance.poids_assemblage else 0,
                    }
                )
    
    except Exception as e:
        print(f"Erreur dans handle_lancement_save: {e}")


@receiver(post_delete, sender='lancements.Lancement')
def handle_lancement_delete(sender, instance, **kwargs):
    """Gère la suppression des lancements"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        Activite.log_activity(
            utilisateur=utilisateur,
            action='delete',
            module='lancements',
            description=f"Suppression du lancement {instance.num_lanc}",
            request=request
        )
        
        # Notification aux managers
        NotificationService.creer_notification_pour_role(
            role_name='Manager',
            type_notif='warning',
            titre='Lancement supprimé',
            message=f'Le lancement {instance.num_lanc} a été supprimé',
        )
    
    except Exception as e:
        print(f"Erreur dans handle_lancement_delete: {e}")


# ========== SIGNAUX POUR LES AFFAIRES ==========

@receiver(post_save, sender=Affaire)
def handle_affaire_save(sender, instance, created, **kwargs):
    """Gère la création/modification des affaires"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        if created:
            Activite.log_activity(
                utilisateur=utilisateur,
                action='create',
                module='affaires',
                description=f"Création de l'affaire {instance.code_affaire} pour le client {instance.client or 'Non défini'}",
                objet=instance,
                request=request
            )
            
            # Notification au responsable de l'affaire
            if instance.responsable_affaire and instance.responsable_affaire != utilisateur:
                NotificationService.creer_notification_individuelle(
                    utilisateur=instance.responsable_affaire,
                    type_notif='info',
                    titre='Nouvelle affaire assignée',
                    message=f'L\'affaire {instance.code_affaire} vous a été assignée',
                    url_action=f'/core/affaires/{instance.pk}/',  # CORRECTION: URL corrigée
                    objet=instance
                )
    
    except Exception as e:
        print(f"Erreur dans handle_affaire_save: {e}")


@receiver(post_save, sender=Collaborateur)
def handle_collaborateur_save(sender, instance, created, **kwargs):
    """Gère la création/modification des collaborateurs"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        if created:
            # Créer une activité
            Activite.log_activity(
                utilisateur=utilisateur,
                action='create',
                module='collaborateurs',
                description=f"Nouveau collaborateur créé: {instance.get_full_name()}",
                objet=instance,
                request=request
            )
            
            # Créer une notification de bienvenue pour le nouveau collaborateur
            NotificationService.creer_notification_individuelle(
                utilisateur=instance,
                type_notif='info',
                titre='Bienvenue !',
                message=f'Bienvenue dans le système AIC Métallurgie, {instance.get_full_name()}. Votre compte a été créé avec succès.',
            )
            
            # Notification aux managers
            NotificationService.creer_notification_pour_role(
                role_name='Manager',
                type_notif='info',
                titre='Nouveau collaborateur',
                message=f'{instance.get_full_name()} a été ajouté à l\'équipe',
                url_action=f'/collaborateurs/{instance.pk}/',
                objet=instance
            )
    
    except Exception as e:
        print(f"Erreur dans handle_collaborateur_save: {e}")


# ========== SIGNAUX POUR LES ATELIERS ==========

@receiver(post_save, sender='ateliers.Atelier')
def handle_atelier_save(sender, instance, created, **kwargs):
    """Gère la création/modification des ateliers"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        if created:
            Activite.log_activity(
                utilisateur=utilisateur,
                action='create',
                module='ateliers',
                description=f"Nouvel atelier créé: {instance.nom_atelier} ({instance.get_type_atelier_display() if hasattr(instance, 'get_type_atelier_display') else 'Type non défini'})",
                objet=instance,
                request=request
            )
    
    except Exception as e:
        print(f"Erreur dans handle_atelier_save: {e}")


# ========== SIGNAL POUR CRÉER DES DONNÉES DE TEST (DÉVELOPPEMENT) ==========

@receiver(post_save, sender=Collaborateur)
def creer_donnees_test_si_premier_collaborateur(sender, instance, created, **kwargs):
    """Crée des données de test si c'est le premier collaborateur (pour développement)"""
    if created and not kwargs.get('raw', False):  # Éviter pendant les fixtures
        try:
            # Vérifier si c'est le premier collaborateur actif
            nb_collaborateurs = Collaborateur.objects.filter(is_active=True).count()
            
            if nb_collaborateurs <= 3:  # Créer des données de test pour les premiers collaborateurs
                # Créer quelques activités de test
                for i in range(3):
                    Activite.objects.create(
                        utilisateur=instance,
                        action='create',
                        module='system',
                        description=f'Activité de test #{i+1} pour {instance.get_full_name()}',
                    )
                
                # Créer quelques notifications de test
                types_notif = ['info', 'success', 'warning']
                for i, type_notif in enumerate(types_notif):
                    NotificationService.creer_notification_individuelle(
                        utilisateur=instance,
                        type_notif=type_notif,
                        titre=f'Notification de test {i+1}',
                        message=f'Ceci est une notification de test de type {type_notif} pour vérifier le système.',
                    )
                
                print(f"Données de test créées pour {instance.get_full_name()}")
        
        except Exception as e:
            print(f"Erreur lors de la création des données de test: {e}")


# ========== MIDDLEWARE POUR CAPTURER LES REQUÊTES ==========

class ActivityMiddleware:
    """Middleware pour capturer les requêtes dans les signaux"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        set_current_request(request)
        try:
            response = self.get_response(request)
        finally:
            set_current_request(None)
        return response


# ========== NETTOYAGE AUTOMATIQUE ==========

def nettoyer_anciennes_notifications():
    """Nettoie les notifications anciennes (à exécuter via cron ou celery)"""
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Supprimer les notifications lues de plus de 30 jours
        date_limite_lues = timezone.now() - timedelta(days=30)
        notifications_lues = Notification.objects.filter(
            lu=True,
            date_lecture__lt=date_limite_lues
        )
        count_lues = notifications_lues.count()
        notifications_lues.delete()
        
        # Supprimer les notifications non lues de plus de 90 jours
        date_limite_non_lues = timezone.now() - timedelta(days=90)
        notifications_non_lues = Notification.objects.filter(
            lu=False,
            date_creation__lt=date_limite_non_lues
        )
        count_non_lues = notifications_non_lues.count()
        notifications_non_lues.delete()
        
        # Supprimer les notifications expirées
        notifications_expirees = Notification.objects.filter(
            date_expiration__lt=timezone.now()
        )
        count_expirees = notifications_expirees.count()
        notifications_expirees.delete()
        
        return {
            'notifications_lues_supprimees': count_lues,
            'notifications_non_lues_supprimees': count_non_lues,
            'notifications_expirees_supprimees': count_expirees
        }
    
    except Exception as e:
        print(f"Erreur lors du nettoyage des notifications: {e}")
        return {
            'notifications_lues_supprimees': 0,
            'notifications_non_lues_supprimees': 0,
            'notifications_expirees_supprimees': 0
        }


def nettoyer_anciennes_activites():
    """Nettoie les activités anciennes"""
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Garder seulement les activités des 6 derniers mois
        date_limite = timezone.now() - timedelta(days=180)
        activites_anciennes = Activite.objects.filter(date_creation__lt=date_limite)
        count = activites_anciennes.count()
        activites_anciennes.delete()
        
        return count
    
    except Exception as e:
        print(f"Erreur lors du nettoyage des activités: {e}")
        return 0
# ========== SIGNAUX POUR LES MODIFICATIONS DE COLLABORATEURS ==========

@receiver(pre_save, sender=Collaborateur)
def store_collaborateur_before_save(sender, instance, **kwargs):
    """Stocke les données avant modification d'un collaborateur"""
    if instance.pk:
        try:
            old_instance = Collaborateur.objects.get(pk=instance.pk)
            _thread_locals.old_collaborateur = {
                'nom_collaborateur': old_instance.nom_collaborateur,
                'prenom_collaborateur': old_instance.prenom_collaborateur,
                'email': old_instance.email,
                'is_active': old_instance.is_active,
                'user_role': str(old_instance.user_role) if old_instance.user_role else None,
                'poste': getattr(old_instance, 'poste', None),
                'telephone': getattr(old_instance, 'telephone', None),
            }
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des données collaborateur: {e}")
            _thread_locals.old_collaborateur = None


@receiver(post_save, sender=Collaborateur)
def handle_collaborateur_update(sender, instance, created, **kwargs):
    """Gère les modifications de collaborateurs (complément du signal existant)"""
    if not created:  # Modification uniquement
        try:
            request = get_current_request()
            utilisateur = None
            
            if request and hasattr(request, 'user') and request.user.is_authenticated:
                utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
            
            old_data = getattr(_thread_locals, 'old_collaborateur', {})
            changes = []
            
            # Détecter les changements significatifs
            if old_data.get('nom_collaborateur') != instance.nom_collaborateur:
                changes.append(f"Nom: {old_data.get('nom_collaborateur')} → {instance.nom_collaborateur}")
            
            if old_data.get('prenom_collaborateur') != instance.prenom_collaborateur:
                changes.append(f"Prénom: {old_data.get('prenom_collaborateur')} → {instance.prenom_collaborateur}")
            
            if old_data.get('email') != instance.email:
                changes.append(f"Email: {old_data.get('email')} → {instance.email}")
            
            if old_data.get('is_active') != instance.is_active:
                status = "activé" if instance.is_active else "désactivé"
                changes.append(f"Compte {status}")
                
                # Notification spéciale pour changement de statut
                if instance.is_active:
                    NotificationService.creer_notification_individuelle(
                        utilisateur=instance,
                        type_notif='success',
                        titre='Compte réactivé',
                        message='Votre compte a été réactivé. Vous pouvez maintenant vous connecter.',
                    )
                else:
                    NotificationService.creer_notification_pour_role(
                        role_name='Admin',
                        type_notif='warning',
                        titre='Compte désactivé',
                        message=f'Le compte de {instance.get_full_name()} a été désactivé',
                    )
            
            if old_data.get('user_role') != str(instance.user_role):
                changes.append(f"Rôle: {old_data.get('user_role')} → {instance.user_role}")
                
                # Notification au collaborateur pour changement de rôle
                if instance.user_role:
                    NotificationService.creer_notification_individuelle(
                        utilisateur=instance,
                        type_notif='info',
                        titre='Rôle mis à jour',
                        message=f'Votre rôle a été mis à jour : {instance.user_role.name}',
                    )
            
            if changes:
                Activite.log_activity(
                    utilisateur=utilisateur,
                    action='update',
                    module='collaborateurs',
                    description=f"Modification du collaborateur {instance.get_full_name()}: {', '.join(changes)}",
                    objet=instance,
                    request=request,
                    donnees_avant=old_data,
                    donnees_après={
                        'nom_collaborateur': instance.nom_collaborateur,
                        'prenom_collaborateur': instance.prenom_collaborateur,
                        'email': instance.email,
                        'is_active': instance.is_active,
                        'user_role': str(instance.user_role) if instance.user_role else None,
                    }
                )
        
        except Exception as e:
            print(f"Erreur dans handle_collaborateur_update: {e}")


@receiver(post_delete, sender=Collaborateur)
def handle_collaborateur_delete(sender, instance, **kwargs):
    """Gère la suppression des collaborateurs"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        Activite.log_activity(
            utilisateur=utilisateur,
            action='delete',
            module='collaborateurs',
            description=f"Suppression du collaborateur {instance.get_full_name()} (Email: {instance.email})",
            request=request
        )
        
        # Notification aux administrateurs
        NotificationService.creer_notification_pour_role(
            role_name='Admin',
            type_notif='warning',
            titre='Collaborateur supprimé',
            message=f'Le collaborateur {instance.get_full_name()} a été supprimé du système',
        )
    
    except Exception as e:
        print(f"Erreur dans handle_collaborateur_delete: {e}")


# ========== SIGNAUX POUR LES ATELIERS (COMPLÉTER) ==========

@receiver(pre_save, sender='ateliers.Atelier')
def store_atelier_before_save(sender, instance, **kwargs):
    """Stocke les données avant modification d'un atelier"""
    if instance.pk:
        try:
            from apps.ateliers.models import Atelier
            old_instance = Atelier.objects.get(pk=instance.pk)
            _thread_locals.old_atelier = {
                'nom_atelier': old_instance.nom_atelier,
                'type_atelier': old_instance.type_atelier,
                'responsable_atelier': str(old_instance.responsable_atelier) if old_instance.responsable_atelier else None,
                'localisation': getattr(old_instance, 'localisation', None),
                'capacite': getattr(old_instance, 'capacite', None),
            }
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des données atelier: {e}")
            _thread_locals.old_atelier = None


@receiver(post_save, sender='ateliers.Atelier')
def handle_atelier_update(sender, instance, created, **kwargs):
    """Gère les créations/modifications d'ateliers"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        if created:
            # Déjà géré dans le signal existant, mais on peut ajouter des notifications
            if hasattr(instance, 'responsable_atelier') and instance.responsable_atelier:
                NotificationService.creer_notification_individuelle(
                    utilisateur=instance.responsable_atelier,
                    type_notif='info',
                    titre='Nouvel atelier assigné',
                    message=f'Vous êtes maintenant responsable de l\'atelier {instance.nom_atelier}',
                    url_action=f'/ateliers/{instance.pk}/',
                    objet=instance
                )
        else:
            # Modification
            old_data = getattr(_thread_locals, 'old_atelier', {})
            changes = []
            
            if old_data.get('nom_atelier') != instance.nom_atelier:
                changes.append(f"Nom: {old_data.get('nom_atelier')} → {instance.nom_atelier}")
            
            if old_data.get('responsable_atelier') != str(instance.responsable_atelier):
                changes.append(f"Responsable: {old_data.get('responsable_atelier')} → {instance.responsable_atelier}")
                
                # Notification au nouveau responsable
                if hasattr(instance, 'responsable_atelier') and instance.responsable_atelier:
                    NotificationService.creer_notification_individuelle(
                        utilisateur=instance.responsable_atelier,
                        type_notif='info',
                        titre='Responsabilité d\'atelier assignée',
                        message=f'Vous êtes maintenant responsable de l\'atelier {instance.nom_atelier}',
                        url_action=f'/ateliers/{instance.pk}/',
                        objet=instance
                    )
            
            if changes:
                Activite.log_activity(
                    utilisateur=utilisateur,
                    action='update',
                    module='ateliers',
                    description=f"Modification de l'atelier {instance.nom_atelier}: {', '.join(changes)}",
                    objet=instance,
                    request=request,
                    donnees_avant=old_data,
                    donnees_après={
                        'nom_atelier': instance.nom_atelier,
                        'type_atelier': instance.type_atelier,
                        'responsable_atelier': str(instance.responsable_atelier) if instance.responsable_atelier else None,
                    }
                )
    
    except Exception as e:
        print(f"Erreur dans handle_atelier_update: {e}")


@receiver(post_delete, sender='ateliers.Atelier')
def handle_atelier_delete(sender, instance, **kwargs):
    """Gère la suppression des ateliers"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        Activite.log_activity(
            utilisateur=utilisateur,
            action='delete',
            module='ateliers',
            description=f"Suppression de l'atelier {instance.nom_atelier} ({instance.get_type_atelier_display() if hasattr(instance, 'get_type_atelier_display') else 'Type non défini'})",
            request=request
        )
        
        # Notification aux managers et à l'ancien responsable
        NotificationService.creer_notification_pour_role(
            role_name='Manager',
            type_notif='warning',
            titre='Atelier supprimé',
            message=f'L\'atelier {instance.nom_atelier} a été supprimé',
        )
        
        if hasattr(instance, 'responsable_atelier') and instance.responsable_atelier:
            NotificationService.creer_notification_individuelle(
                utilisateur=instance.responsable_atelier,
                type_notif='warning',
                titre='Atelier supprimé',
                message=f'L\'atelier {instance.nom_atelier} dont vous étiez responsable a été supprimé',
            )
    
    except Exception as e:
        print(f"Erreur dans handle_atelier_delete: {e}")


# ========== SIGNAUX POUR LES CATÉGORIES ==========

@receiver(post_save, sender='ateliers.Categorie')
def handle_categorie_save(sender, instance, created, **kwargs):
    """Gère les créations/modifications de catégories"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        if created:
            Activite.log_activity(
                utilisateur=utilisateur,
                action='create',
                module='categories',
                description=f"Nouvelle catégorie créée: {instance.nom_categorie}",
                objet=instance,
                request=request
            )
        else:
            Activite.log_activity(
                utilisateur=utilisateur,
                action='update',
                module='categories',
                description=f"Modification de la catégorie: {instance.nom_categorie}",
                objet=instance,
                request=request
            )
    
    except Exception as e:
        print(f"Erreur dans handle_categorie_save: {e}")


@receiver(post_delete, sender='ateliers.Categorie')
def handle_categorie_delete(sender, instance, **kwargs):
    """Gère la suppression des catégories"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        Activite.log_activity(
            utilisateur=utilisateur,
            action='delete',
            module='categories',
            description=f"Suppression de la catégorie: {instance.nom_categorie}",
            request=request
        )
        
        # Notification aux managers
        NotificationService.creer_notification_pour_role(
            role_name='Manager',
            type_notif='info',
            titre='Catégorie supprimée',
            message=f'La catégorie {instance.nom_categorie} a été supprimée',
        )
    
    except Exception as e:
        print(f"Erreur dans handle_categorie_delete: {e}")


# ========== SIGNAUX POUR LES ASSOCIATIONS (DANS ATELIERS) ==========

@receiver(post_save, sender='ateliers.CollaborateurAtelier')
def handle_collaborateur_atelier_save(sender, instance, created, **kwargs):
    """Gère les affectations collaborateur-atelier"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        if created:
            Activite.log_activity(
                utilisateur=utilisateur,
                action='assign',
                module='collaborateurs',
                description=f"Affectation de {instance.collaborateur.get_full_name()} à l'atelier {instance.atelier.nom_atelier}",
                objet=instance,
                request=request
            )
            
            # Notification au collaborateur
            NotificationService.creer_notification_individuelle(
                utilisateur=instance.collaborateur,
                type_notif='info',
                titre='Nouvelle affectation d\'atelier',
                message=f'Vous avez été affecté(e) à l\'atelier {instance.atelier.nom_atelier}',
                url_action=f'/ateliers/{instance.atelier.pk}/',
                objet=instance.atelier
            )
    
    except Exception as e:
        print(f"Erreur dans handle_collaborateur_atelier_save: {e}")


@receiver(post_save, sender='ateliers.CollaborateurCategorie')
def handle_collaborateur_categorie_save(sender, instance, created, **kwargs):
    """Gère les compétences collaborateur-catégorie"""
    try:
        request = get_current_request()
        utilisateur = None
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            utilisateur = request.user if isinstance(request.user, Collaborateur) else getattr(request.user, 'collaborateur', None)
        
        if created:
            Activite.log_activity(
                utilisateur=utilisateur,
                action='assign',
                module='collaborateurs',
                description=f"Attribution de compétence {instance.categorie.nom_categorie} à {instance.collaborateur.get_full_name()} (Niveau: {instance.niveau_competence})",
                objet=instance,
                request=request
            )
            
            # Notification au collaborateur
            NotificationService.creer_notification_individuelle(
                utilisateur=instance.collaborateur,
                type_notif='success',
                titre='Nouvelle compétence validée',
                message=f'Votre compétence en {instance.categorie.nom_categorie} a été validée (Niveau: {instance.get_niveau_competence_display()})',
            )
    
    except Exception as e:
        print(f"Erreur dans handle_collaborateur_categorie_save: {e}")


# ========== SIGNAUX POUR LES EXPORTS/IMPORTS ==========

def log_export_activity(utilisateur, module, description, request=None):
    """Fonction utilitaire pour enregistrer les activités d'export"""
    try:
        Activite.log_activity(
            utilisateur=utilisateur,
            action='export',
            module=module,
            description=description,
            request=request
        )
        
        # Notification aux administrateurs pour les exports sensibles
        if module in ['collaborateurs', 'rapports']:
            NotificationService.creer_notification_pour_role(
                role_name='Admin',
                type_notif='info',
                titre='Export de données effectué',
                message=f'{utilisateur.get_full_name() if utilisateur else "Système"} a exporté des données: {description}',
            )
    except Exception as e:
        print(f"Erreur lors de l'enregistrement de l'export: {e}")


def log_import_activity(utilisateur, module, description, request=None):
    """Fonction utilitaire pour enregistrer les activités d'import"""
    try:
        Activite.log_activity(
            utilisateur=utilisateur,
            action='import',
            module=module,
            description=description,
            request=request
        )
        
        # Notification aux administrateurs
        NotificationService.creer_notification_pour_role(
            role_name='Admin',
            type_notif='warning',
            titre='Import de données effectué',
            message=f'{utilisateur.get_full_name() if utilisateur else "Système"} a importé des données: {description}',
        )
    except Exception as e:
        print(f"Erreur lors de l'enregistrement de l'import: {e}")


# ========== SIGNAL POUR LES CHANGEMENTS DE RÔLE ==========

@receiver(post_save, sender='collaborateurs.RoleHistory')
def handle_role_change(sender, instance, created, **kwargs):
    """Gère l'historique des changements de rôle"""
    if created:
        try:
            request = get_current_request()
            
            Activite.log_activity(
                utilisateur=instance.changed_by,
                action='assign',
                module='administration',
                description=f"Changement de rôle pour {instance.collaborateur.get_full_name()}: {instance.old_role} → {instance.new_role}",
                objet=instance.collaborateur,
                request=request
            )
        
        except Exception as e:
            print(f"Erreur dans handle_role_change: {e}")