from django.core.management.base import BaseCommand
from apps.core.models import Activite
from apps.collaborateurs.models import Collaborateur
from apps.lancements.models import Lancement
from apps.core.models import Affaire
import random


class Command(BaseCommand):
    help = 'Crée des activités de test pour le dashboard'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Nombre d\'activités à créer (défaut: 20)',
        )
    
    def handle(self, *args, **options):
        count = options['count']
        
        # Récupérer des données existantes
        collaborateurs = list(Collaborateur.objects.filter(is_active=True))
        lancements = list(Lancement.objects.all()[:10])
        affaires = list(Affaire.objects.all()[:5])
        
        if not collaborateurs:
            self.stdout.write(
                self.style.ERROR('Aucun collaborateur trouvé. Créez d\'abord des collaborateurs.')
            )
            return
        
        actions = ['create', 'update', 'delete', 'login', 'logout', 'assign', 'status_change']
        modules = ['lancements', 'affaires', 'collaborateurs', 'ateliers', 'system']
        
        activities_created = 0
        
        for i in range(count):
            utilisateur = random.choice(collaborateurs)
            action = random.choice(actions)
            module = random.choice(modules)
            
            # Générer une description appropriée
            descriptions = {
                'create': [
                    f'Création d\'un nouvel élément dans {module}',
                    f'Ajout d\'une nouvelle entrée en {module}',
                ],
                'update': [
                    f'Modification des données en {module}',
                    f'Mise à jour d\'un élément en {module}',
                ],
                'delete': [
                    f'Suppression d\'un élément en {module}',
                    f'Effacement d\'une entrée en {module}',
                ],
                'login': [
                    f'Connexion de {utilisateur.get_full_name()}',
                ],
                'logout': [
                    f'Déconnexion de {utilisateur.get_full_name()}',
                ],
                'assign': [
                    f'Assignation en {module}',
                    f'Attribution d\'une tâche en {module}',
                ],
                'status_change': [
                    f'Changement de statut en {module}',
                    f'Modification d\'état en {module}',
                ]
            }
            
            description = random.choice(descriptions.get(action, [f'Action {action} en {module}']))
            
            # Choisir un objet lié aléatoirement
            objet = None
            if module == 'lancements' and lancements:
                objet = random.choice(lancements)
            elif module == 'affaires' and affaires:
                objet = random.choice(affaires)
            
            Activite.log_activity(
                utilisateur=utilisateur,
                action=action,
                module=module,
                description=description,
                objet=objet
            )
            
            activities_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'{activities_created} activités de test créées avec succès.')
        )