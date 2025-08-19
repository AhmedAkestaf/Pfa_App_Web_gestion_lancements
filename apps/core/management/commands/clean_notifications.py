from django.core.management.base import BaseCommand
from apps.core.signals import nettoyer_anciennes_notifications, nettoyer_anciennes_activites


class Command(BaseCommand):
    help = 'Nettoie les anciennes notifications et activités'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Afficher ce qui serait supprimé sans effectuer la suppression',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Début du nettoyage...')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Mode DRY-RUN activé - aucune suppression réelle'))
            
            # Compter ce qui serait supprimé
            from django.utils import timezone
            from datetime import timedelta
            from apps.core.models import Notification, Activite
            
            # Notifications
            date_limite_lues = timezone.now() - timedelta(days=30)
            date_limite_non_lues = timezone.now() - timedelta(days=90)
            
            count_lues = Notification.objects.filter(
                lu=True,
                date_lecture__lt=date_limite_lues
            ).count()
            
            count_non_lues = Notification.objects.filter(
                lu=False,
                date_creation__lt=date_limite_non_lues
            ).count()
            
            count_expirees = Notification.objects.filter(
                date_expiration__lt=timezone.now()
            ).count()
            
            # Activités
            date_limite_activites = timezone.now() - timedelta(days=180)
            count_activites = Activite.objects.filter(
                date_creation__lt=date_limite_activites
            ).count()
            
            self.stdout.write(
                f'Éléments qui seraient supprimés:\n'
                f'- {count_lues} notifications lues anciennes\n'
                f'- {count_non_lues} notifications non lues très anciennes\n'
                f'- {count_expirees} notifications expirées\n'
                f'- {count_activites} activités anciennes'
            )
            
        else:
            # Effectuer le nettoyage réel
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
