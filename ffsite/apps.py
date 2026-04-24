from django.apps import AppConfig


class FfsiteConfig(AppConfig):
    name = 'ffsite'

    def ready(self):
        from django.db.models.signals import post_migrate
        from fforg.permissions import seed_permission_groups
        post_migrate.connect(seed_permission_groups)
