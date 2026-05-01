import logging

import requests
from celery import shared_task
from extralifeapi.participants import Participants

log = logging.getLogger(__name__)


@shared_task
def resolve_fundraising_url(event_interest_id):
    """
    Resolve a fundraising URL on an EventInterest to a canonical participant or team record.

    - If the URL is a participant page: find or create a ParticipantModel and link via el_participant.
    - If the URL is a team page: log for coordinator review (no automated action).
    - If the URL is unrecognised or empty: log and exit.
    """
    from evtsignup.models import EventInterest
    from evtsignup.utils import parse_fundraising_url

    from django.conf import settings
    max_attempts = settings.URL_RESOLUTION_MAX_ATTEMPTS

    try:
        interest = EventInterest.objects.get(pk=event_interest_id)
    except EventInterest.DoesNotExist:
        log.warning('resolve_fundraising_url: EventInterest %s not found', event_interest_id)
        return

    if not interest.fundraising_url:
        return

    if interest.url_resolution_attempts >= max_attempts:
        log.info(
            'resolve_fundraising_url: EventInterest %s has reached max attempts (%d), skipping',
            event_interest_id, max_attempts,
        )
        return

    interest.url_resolution_attempts += 1
    interest.save(update_fields=['url_resolution_attempts'])

    result = parse_fundraising_url(interest.fundraising_url)

    if result.is_participant:
        _resolve_participant(interest, result)
    elif result.is_team:
        log.info(
            'resolve_fundraising_url: EventInterest %s has a team URL (%s) - flagged for coordinator review',
            event_interest_id, interest.fundraising_url,
        )
    else:
        # Try following redirects - may be a vanity link pointing to Extra Life
        if _is_followable_url(interest.fundraising_url):
            resolved = _follow_redirect(interest.fundraising_url)
            if resolved and resolved != interest.fundraising_url:
                redirected_result = parse_fundraising_url(resolved)
                if redirected_result.is_participant:
                    log.info(
                        'resolve_fundraising_url: EventInterest %s resolved via redirect %s → %s',
                        event_interest_id, interest.fundraising_url, resolved,
                    )
                    _resolve_participant(interest, redirected_result)
                    return
                elif redirected_result.is_team:
                    log.info(
                        'resolve_fundraising_url: EventInterest %s redirect resolves to team URL (%s) - flagged for coordinator review',
                        event_interest_id, resolved,
                    )
                    return
        log.info(
            'resolve_fundraising_url: EventInterest %s has unrecognised URL (%s)',
            event_interest_id, interest.fundraising_url,
        )


def _is_followable_url(url):
    """Return True if the URL is a valid http/https URL worth attempting to follow."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url if '://' in url else f'https://{url}')
        return (
            parsed.scheme in ('http', 'https')
            and bool(parsed.netloc)
            and ' ' not in parsed.netloc
            and '.' in parsed.netloc
        )
    except Exception:
        return False


def _follow_redirect(url):
    """Follow HTTP redirects and return the final URL, or None on failure."""
    try:
        resp = requests.get(
            url if '://' in url else f'https://{url}',
            allow_redirects=True,
            timeout=10,
            headers={'User-Agent': 'Fragforce/1.0'},
        )
        return resp.url
    except Exception as e:
        log.debug('_follow_redirect: failed to follow %s: %s', url, e)
        return None


def _resolve_participant(interest, result):
    """Look up the participant by ID or slug and link to el_participant."""
    from ffdonations.models import ParticipantModel

    id_or_slug = result.id_or_slug
    log.info(
        'resolve_fundraising_url: resolving participant %s for EventInterest %s',
        id_or_slug, interest.pk,
    )

    try:
        api_participant = Participants.participant(id_or_slug)
    except Exception as e:
        log.warning(
            'resolve_fundraising_url: failed to fetch participant %s: %s',
            id_or_slug, e,
        )
        return

    if not api_participant:
        log.warning(
            'resolve_fundraising_url: participant %s not found in Extra Life API',
            id_or_slug,
        )
        return

    numeric_id = api_participant.get('participantID')
    if not numeric_id:
        log.warning('resolve_fundraising_url: no participantID in API response for %s', id_or_slug)
        return

    participant, created = ParticipantModel.objects.get_or_create(
        id=numeric_id,
        defaults={'displayName': api_participant.get('displayName', ''), 'tracked': False},
    )

    interest.el_participant = participant
    interest.save(update_fields=['el_participant'])
    log.info(
        'resolve_fundraising_url: linked EventInterest %s to participant %s (%s)',
        interest.pk, numeric_id, 'created' if created else 'existing',
    )


@shared_task
def retry_pending_url_resolutions():
    """
    Re-queue resolve_fundraising_url for any EventInterest records where:
    - fundraising_url is set
    - el_participant is not yet resolved
    This catches cases where the signal fired but the task failed or Celery was down.
    """
    from django.conf import settings
    from evtsignup.models import EventInterest
    max_attempts = settings.URL_RESOLUTION_MAX_ATTEMPTS
    pending = EventInterest.objects.filter(
        fundraising_url__isnull=False,
        el_participant__isnull=True,
        url_resolution_attempts__lt=max_attempts,
    ).exclude(fundraising_url='')
    count = pending.count()
    if count == 0:
        log.info('retry_pending_url_resolutions: nothing to retry')
        return
    log.info('retry_pending_url_resolutions: re-queuing %d records', count)
    for interest in pending:
        resolve_fundraising_url.delay(interest.pk)
