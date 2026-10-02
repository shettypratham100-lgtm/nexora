from django.contrib.admin.apps import AdminConfig


class NexoraAdminConfig(AdminConfig):
    default_site = "nexora.admin_site.NexoraAdminSite"