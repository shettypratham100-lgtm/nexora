from django.apps import AppConfig


class ResourceManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.resource_manager'
    verbose_name = "Resource Manager"

    def ready(self):
        import apps.resource_manager.signals
