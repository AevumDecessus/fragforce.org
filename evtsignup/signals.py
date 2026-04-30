import logging

log = logging.getLogger(__name__)


def queue_fundraising_url_resolution(sender, instance, created, **kwargs):
    """Queue resolve_fundraising_url when a fundraising URL is set on an EventInterest."""
    if not instance.fundraising_url:
        return
    from evtsignup.tasks import resolve_fundraising_url
    resolve_fundraising_url.delay(instance.pk)
    log.debug('Queued fundraising URL resolution for EventInterest %s', instance.pk)
