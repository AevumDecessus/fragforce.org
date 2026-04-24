from django.apps import AppConfig


class FfsiteConfig(AppConfig):
    name = 'ffsite'

    def ready(self):
        import sys
        skip_commands = {'test', 'collectstatic', 'migrate', 'makemigrations', 'check'}
        if any(cmd in sys.argv for cmd in skip_commands):
            return
        from fforg.permissions import seed_permission_groups
        seed_permission_groups()
