from .models import Notification, Activite
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

def user_permissions(request):
    """Ajoute les permissions de l'utilisateur au contexte de tous les templates"""
    if request.user.is_authenticated:
        permissions = {}
        for perm in request.user.get_all_permissions():
            if perm.module not in permissions:
                permissions[perm.module] = []
            permissions[perm.module].append(perm.action)
        
        return {
            'user_permissions': permissions,
            'user_role': request.user.user_role,
        }
    return {}


def notifications_and_activities(request):
    """
    Context processor pour fournir les notifications et activités à tous les templates
    """
    context = {
        'notifications_non_lues': [],
        'nb_notifications_non_lues': 0,
        'activites_recentes': [],
        'stats_dashboard': {},
    }
    
    if request.user.is_authenticated:
        # CORRECTION: Vérifier si l'utilisateur est un Collaborateur
        collaborateur = None
        if hasattr(request.user, 'collaborateur'):
            collaborateur = request.user.collaborateur
        elif hasattr(request.user, 'id'):
            # Si l'utilisateur EST un collaborateur (AUTH_USER_MODEL)
            collaborateur = request.user
        
        if collaborateur:
            # Notifications non lues (limité à 10 pour la navbar)
            notifications = Notification.objects.filter(
                destinataire=collaborateur,
                lu=False
            ).order_by('-date_creation')[:10]
            
            context.update({
                'notifications_non_lues': notifications,
                'nb_notifications_non_lues': notifications.count(),
            })
        
        # Activités récentes pour le dashboard (dernières 15)
        activites_recentes = Activite.objects.select_related(
            'utilisateur', 'content_type'
        ).order_by('-date_creation')[:15]
        
        context['activites_recentes'] = activites_recentes
        
        # Statistiques pour le dashboard
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        try:
            # CORRECTION: Import avec gestion d'erreur
            from apps.lancements.models import Lancement
            from apps.collaborateurs.models import Collaborateur
            from apps.ateliers.models import Atelier
            from .models import Affaire
            
            # Stats des lancements
            lancements_stats = {
                'total_lancements': Lancement.objects.count(),
                'lancements_en_cours': Lancement.objects.filter(statut='en_cours').count(),
                'lancements_termines': Lancement.objects.filter(statut='termine').count(),
                'lancements_cette_semaine': Lancement.objects.filter(
                    date_lancement__gte=week_ago
                ).count(),
            }
            
            # Stats des collaborateurs
            collaborateurs_stats = {
                'total_collaborateurs': Collaborateur.objects.count(),
                'collaborateurs_actifs': Collaborateur.objects.filter(is_active=True).count(),
            }
            
            # Stats des ateliers
            ateliers_stats = {
                'total_ateliers': Atelier.objects.count(),
            }
            
            # Stats des affaires
            affaires_stats = {
                'total_affaires': Affaire.objects.count(),
                'affaires_actives': Affaire.objects.filter(statut='en_cours').count(),
            }
            
            context['stats_dashboard'] = {
                **lancements_stats,
                **collaborateurs_stats,
                **ateliers_stats,
                **affaires_stats,
            }
            
        except ImportError as e:
            # En cas d'erreur d'import (migrations non effectuées, etc.)
            print(f"Erreur d'import dans context_processor: {e}")
            context['stats_dashboard'] = {
                'total_lancements': 0,
                'lancements_en_cours': 0,
                'lancements_termines': 0,
                'lancements_cette_semaine': 0,
                'total_collaborateurs': 0,
                'collaborateurs_actifs': 0,
                'total_ateliers': 0,
                'total_affaires': 0,
                'affaires_actives': 0,
            }
    
    return context


def user_permissions(request):
    """
    Context processor pour les permissions utilisateur
    """
    context = {}
    
    if request.user.is_authenticated and hasattr(request.user, 'user_role') and request.user.user_role:
        permissions_dict = request.user.user_role.get_permissions_by_module()
        context['user_permissions'] = permissions_dict
        context['user_role'] = request.user.user_role
    else:
        context['user_permissions'] = {}
        context['user_role'] = None
    
    return context