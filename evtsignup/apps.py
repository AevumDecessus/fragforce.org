from django.apps import AppConfig


class EvtsignupConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'evtsignup'

    def ready(self):
        from django.db.models.signals import pre_save, post_save
        from evtsignup.models import EventInterest
        from evtsignup.signals import track_fundraising_url_change, queue_fundraising_url_resolution
        pre_save.connect(track_fundraising_url_change, sender=EventInterest)
        post_save.connect(queue_fundraising_url_resolution, sender=EventInterest)
