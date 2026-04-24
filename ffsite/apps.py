from django.apps import AppConfig


class FfsiteConfig(AppConfig):
    name = 'ffsite'

    def ready(self):
        import sys
        if 'test' in sys.argv:
            return
        from fforg.permissions import seed_permission_groups
        seed_permission_groups()
