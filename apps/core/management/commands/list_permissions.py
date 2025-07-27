from django.core.management.base import BaseCommand
from apps.core.models import Permission, Role

class Command(BaseCommand):
    help = 'Liste toutes les permissions et rôles du système'

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            help='Affiche les permissions d\'un rôle spécifique',
        )

    def handle(self, *args, **options):
        if options['role']:
            self.show_role_permissions(options['role'])
        else:
            self.show_all_permissions()

    def show_all_permissions(self):
        self.stdout.write('📊 MATRICE DES PERMISSIONS')
        self.stdout.write('=' * 50)
        
        modules = {}
        for perm in Permission.objects.all().order_by('module', 'action'):
            if perm.module not in modules:
                modules[perm.module] = []
            modules[perm.module].append(perm.get_action_display())
        
        for module, actions in modules.items():
            self.stdout.write(f'\n🏢 {module.upper()}:')
            for action in actions:
                self.stdout.write(f'   ✓ {action}')
        
        self.stdout.write('\n👥 RÔLES DISPONIBLES:')
        self.stdout.write('-' * 30)
        for role in Role.objects.all():
            status = '🟢' if role.is_active else '🔴'
            system = '⚙️' if role.is_system_role else '👤'
            perm_count = role.permissions.count()
            self.stdout.write(f'{status} {system} {role.name} ({perm_count} permissions)')

    def show_role_permissions(self, role_name):
        try:
            role = Role.objects.get(name__icontains=role_name)
            self.stdout.write(f'👤 PERMISSIONS DU RÔLE: {role.name}')
            self.stdout.write('=' * 50)
            self.stdout.write(f'📝 Description: {role.description}')
            self.stdout.write(f'🟢 Statut: {"Actif" if role.is_active else "Inactif"}')
            self.stdout.write(f'⚙️ Rôle système: {"Oui" if role.is_system_role else "Non"}')
            
            permissions_by_module = role.get_permissions_by_module()
            
            if not permissions_by_module:
                self.stdout.write('❌ Aucune permission assignée')
                return
            
            for module, actions in permissions_by_module.items():
                self.stdout.write(f'\n🏢 {module.upper()}:')
                for action in actions:
                    action_display = dict(Permission.ACTION_CHOICES).get(action, action)
                    self.stdout.write(f'   ✓ {action_display}')
                    
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ Rôle "{role_name}" non trouvé')
            )
            self.stdout.write('Rôles disponibles:')
            for role in Role.objects.all():
                self.stdout.write(f'  - {role.name}')