import logging

from celery import shared_task

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

    try:
        interest = EventInterest.objects.get(pk=event_interest_id)
    except EventInterest.DoesNotExist:
        log.warning('resolve_fundraising_url: EventInterest %s not found', event_interest_id)
        return

    if not interest.fundraising_url:
        return

    result = parse_fundraising_url(interest.fundraising_url)

    if result.is_participant:
        _resolve_participant(interest, result)
    elif result.is_team:
        log.info(
            'resolve_fundraising_url: EventInterest %s has a team URL (%s) - flagged for coordinator review',
            event_interest_id, interest.fundraising_url,
        )
    else:
        log.info(
            'resolve_fundraising_url: EventInterest %s has unrecognised URL (%s)',
            event_interest_id, interest.fundraising_url,
        )


def _resolve_participant(interest, result):
    """Look up the participant by ID or slug and link to el_participant."""
    from ffdonations.models import ParticipantModel

    id_or_slug = result.id_or_slug
    log.info(
        'resolve_fundraising_url: resolving participant %s for EventInterest %s',
        id_or_slug, interest.pk,
    )

    try:
        from extralifeapi.participants import Participants
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
        participantID=numeric_id,
        defaults={'displayName': api_participant.get('displayName', ''), 'tracked': False},
    )

    interest.el_participant = participant
    interest.save(update_fields=['el_participant'])
    log.info(
        'resolve_fundraising_url: linked EventInterest %s to participant %s (%s)',
        interest.pk, numeric_id, 'created' if created else 'existing',
    )
