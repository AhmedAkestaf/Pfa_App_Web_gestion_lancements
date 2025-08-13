from django.apps import AppConfig


class AssociationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.associations'
    verbose_name = 'Associations'
    
    def ready(self):
        """Actions à effectuer quand l'application est prête"""
        pass