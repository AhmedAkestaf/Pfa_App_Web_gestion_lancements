from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = "Core"

    def ready(self):
        """Cette méthode est appelée quand l'application est prête"""
        # Importer les signaux pour qu'ils soient enregistrés
        import apps.core.signals


