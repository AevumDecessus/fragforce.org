from django.apps import AppConfig


class EvtsignupConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'evtsignup'

    def ready(self):
        from django.db.models.signals import post_save
        from evtsignup.models import EventInterest
        from evtsignup.signals import queue_fundraising_url_resolution
        post_save.connect(queue_fundraising_url_resolution, sender=EventInterest)
