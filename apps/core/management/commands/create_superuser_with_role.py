from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from apps.collaborateurs.models import Collaborateur
from apps.core.models import Role

class Command(BaseCommand):
    help = 'Crée un super utilisateur avec le rôle Super Administrateur'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='Email du super utilisateur')
        parser.add_argument('--password', required=True, help='Mot de passe')
        parser.add_argument('--nom', required=True, help='Nom')
        parser.add_argument('--prenom', required=True, help='Prénom')

    def handle(self, *args, **options):
        try:
            # Vérifier si l'utilisateur existe déjà
            if Collaborateur.objects.filter(email=options['email']).exists():
                self.stdout.write(
                    self.style.ERROR(f"Un utilisateur avec l'email {options['email']} existe déjà.")
                )
                return

            # Récupérer le rôle Super Administrateur
            super_admin_role = Role.objects.get(name='Super Administrateur')
            
            # Créer l'utilisateur directement
            user = Collaborateur.objects.create(
                email=options['email'],
                password=make_password(options['password']),  # Hasher le mot de passe
                nom_collaborateur=options['nom'],
                prenom_collaborateur=options['prenom'],
                user_role=super_admin_role
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Super utilisateur créé avec succès: {user}')
            )
            
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Le rôle "Super Administrateur" n\'existe pas. Exécutez d\'abord init_permissions.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erreur lors de la création: {str(e)}')
            )