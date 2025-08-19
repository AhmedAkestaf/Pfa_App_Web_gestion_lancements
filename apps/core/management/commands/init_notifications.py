from django.core.management.base import BaseCommand
from apps.core.models import Notification, Activite
from apps.collaborateurs.models import Collaborateur
from apps.core.signals import NotificationService


class Command(BaseCommand):
    help = 'Initialise le système de notifications avec des données de test'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-notifications',
            action='store_true',
            help='Créer des notifications de test',
        )
        parser.add_argument(
            '--clean-old-data',
            action='store_true',
            help='Nettoyer les anciennes données',
        )
    
    def handle(self, *args, **options):
        if options['clean_old_data']:
            self.stdout.write('Nettoyage des anciennes données...')
            
            # Nettoyer les notifications
            from apps.core.signals import nettoyer_anciennes_notifications, nettoyer_anciennes_activites
            
            result_notifications = nettoyer_anciennes_notifications()
            result_activites = nettoyer_anciennes_activites()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Nettoyage terminé:\n'
                    f'- {result_notifications["notifications_lues_supprimees"]} notifications lues supprimées\n'
                    f'- {result_notifications["notifications_non_lues_supprimees"]} notifications non lues supprimées\n'
                    f'- {result_notifications["notifications_expirees_supprimees"]} notifications expirées supprimées\n'
                    f'- {result_activites} activités supprimées'
                )
            )
        
        if options['create_test_notifications']:
            self.stdout.write('Création de notifications de test...')
            
            # Récupérer tous les collaborateurs actifs
            collaborateurs = Collaborateur.objects.filter(is_active=True)
            
            if not collaborateurs.exists():
                self.stdout.write(
                    self.style.ERROR('Aucun collaborateur trouvé. Créez d\'abord des collaborateurs.')
                )
                return
            
            notifications_created = 0
            
            for collaborateur in collaborateurs:
                # Notification d'information
                NotificationService.creer_notification_individuelle(
                    utilisateur=collaborateur,
                    type_notif='info',
                    titre='Bienvenue dans le système de notifications',
                    message='Le système de notifications est maintenant opérationnel. Vous recevrez désormais des alertes importantes.',
                )
                notifications_created += 1
                
                # Notification de test système
                NotificationService.creer_notification_individuelle(
                    utilisateur=collaborateur,
                    type_notif='system',
                    titre='Test du système',
                    message='Ceci est une notification de test pour vérifier le bon fonctionnement du système.',
                )
                notifications_created += 1
            
            # Notification pour les managers
            NotificationService.creer_notification_pour_role(
                role_name='Manager',
                type_notif='success',
                titre='Système de notifications activé',
                message='Le système de notifications et de suivi des activités est maintenant actif pour toute l\'équipe.',
            )
            notifications_created += 3  # Approximation
            
            self.stdout.write(
                self.style.SUCCESS(f'{notifications_created} notifications de test créées avec succès.')
            )
        
        if not options['create_test_notifications'] and not options['clean_old_data']:
            self.stdout.write('Utilisation:')
            self.stdout.write('  --create-test-notifications  : Créer des notifications de test')
            self.stdout.write('  --clean-old-data           : Nettoyer les anciennes données')
