import sys

from django.apps import AppConfig


def _is_server_process():
    """Return True only when running as a gunicorn web server process."""
    return sys.argv[0].endswith('gunicorn')


class FfsiteConfig(AppConfig):
    name = 'ffsite'

    def ready(self):
        if not _is_server_process():
            return
        from fforg.permissions import seed_permission_groups
        seed_permission_groups()
