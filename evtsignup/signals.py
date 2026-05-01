import logging

log = logging.getLogger(__name__)


def track_fundraising_url_change(sender, instance, **kwargs):
    """
    pre_save: capture previous fundraising_url on the instance so post_save can compare.
    """
    if instance.pk:
        try:
            from evtsignup.models import EventInterest
            prev = EventInterest.objects.filter(pk=instance.pk).values('fundraising_url').first()
            instance._prev_fundraising_url = prev['fundraising_url'] if prev else None
        except Exception:
            instance._prev_fundraising_url = None
    else:
        instance._prev_fundraising_url = None


def queue_fundraising_url_resolution(sender, instance, created, update_fields=None, **kwargs):
    """
    post_save: queue resolve_fundraising_url when fundraising URL is set or changed.

    Skips if:
    - No fundraising URL set
    - update_fields specified and fundraising_url not among them
    - URL unchanged and el_participant already resolved
    """
    if not instance.fundraising_url:
        return

    # Profile-only save (e.g. display_name update) that didn't touch fundraising_url
    if update_fields is not None and 'fundraising_url' not in update_fields:
        return

    # URL unchanged and already resolved - no need to re-queue
    prev_url = getattr(instance, '_prev_fundraising_url', None)
    url_changed = prev_url != instance.fundraising_url
    if not created and instance.el_participant_id and not url_changed:
        log.debug(
            'Skipping re-queue for EventInterest %s - URL unchanged and already resolved',
            instance.pk,
        )
        return

    # Reset attempt counter when URL changes so new URL gets fresh attempts.
    # Use queryset.update() to bypass signals and avoid re-entrant pre_save
    # corrupting _prev_fundraising_url change-detection state.
    if not created and url_changed and instance.url_resolution_attempts > 0:
        from evtsignup.models import EventInterest
        EventInterest.objects.filter(pk=instance.pk).update(url_resolution_attempts=0)
        instance.url_resolution_attempts = 0  # keep in-memory state consistent

    from evtsignup.tasks import resolve_fundraising_url
    resolve_fundraising_url.delay(instance.pk)
    log.debug('Queued fundraising URL resolution for EventInterest %s', instance.pk)
