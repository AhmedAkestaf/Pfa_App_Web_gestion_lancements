from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from apps.collaborateurs.models import Collaborateur
from apps.core.models import Role

class Command(BaseCommand):
    help = 'Créer un collaborateur'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Email du collaborateur')
        parser.add_argument('--password', type=str, required=True, help='Mot de passe')
        parser.add_argument('--nom', type=str, required=True, help='Nom de famille')
        parser.add_argument('--prenom', type=str, required=True, help='Prénom')
        parser.add_argument('--role', type=int, help='ID du rôle (optionnel: 1=Super Admin, 2=Responsable Affaire, 3=Responsable Atelier, 4=Collaborateur, 5=Opérateur)')
        parser.add_argument('--admin', action='store_true', help='Créer comme admin')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        nom = options['nom']
        prenom = options['prenom']
        role_name = options.get('role')
        is_admin = options.get('admin', False)

        # Vérifier si l'email existe déjà
        if Collaborateur.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'Un collaborateur avec l\'email {email} existe déjà')
            )
            return

        # Récupérer le rôle si spécifié
        user_role = None
        if role_name:
            try:
                user_role = Role.objects.get(name=role_name)
            except Role.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Le rôle "{role_name}" n\'existe pas. Collaborateur créé sans rôle.')
                )

        # Créer le collaborateur
        collaborateur = Collaborateur.objects.create(
            email=email,
            nom_collaborateur=nom,
            prenom_collaborateur=prenom,
            password=make_password(password),
            is_active=True,
            is_admin=is_admin,
            user_role=user_role
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Collaborateur créé avec succès:\n'
                f'- Email: {email}\n'
                f'- Nom: {nom} {prenom}\n'
                f'- Admin: {is_admin}\n'
                f'- Rôle: {user_role.name if user_role else "Aucun"}'
            )
        )