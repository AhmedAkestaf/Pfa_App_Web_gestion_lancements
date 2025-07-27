from django.core.management.base import BaseCommand
from apps.core.utils.permissions import create_default_permissions, create_default_roles

class Command(BaseCommand):
    help = 'Initialise le système de permissions avec les données par défaut'

    def add_arguments(self, parser):
        parser.add_argument(
            '--permissions-only',
            action='store_true',
            help='Crée uniquement les permissions, pas les rôles',
        )
        parser.add_argument(
            '--roles-only',
            action='store_true',
            help='Crée uniquement les rôles, pas les permissions',
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Initialisation du système de permissions...')
        
        if not options['roles_only']:
            self.stdout.write('📋 Création des permissions...')
            permissions = create_default_permissions()
            self.stdout.write(
                self.style.SUCCESS(f'✅ {len(permissions)} permissions créées')
            )
        
        if not options['permissions_only']:
            self.stdout.write('👥 Création des rôles par défaut...')
            roles = create_default_roles()
            self.stdout.write(
                self.style.SUCCESS(f'✅ {len(roles)} rôles créés')
            )
        
        self.stdout.write(
            self.style.SUCCESS('🎉 Initialisation terminée avec succès!')
        )
