import zoneinfo
from collections import defaultdict
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods

from eventer.models import Event, EventSignupSlot, EventRole, Game
from evtsignup.models import EventInterest, EventAvailabilityInterest, GameInterestUserEvent


def _expand_to_hours(slot):
    """Yield each UTC hour datetime from slot.start up to (not including) slot.stop."""
    current = slot.start.replace(minute=0, second=0, microsecond=0)
    while current < slot.stop:
        yield current
        current += timedelta(hours=1)


def _group_slots_by_day(slots_qs, tz):
    """Return an ordered list of (day_label, [slot, ...]) grouped by slot start day in tz."""
    groups = defaultdict(list)
    order = []
    for slot in slots_qs:
        local_start = slot.start.astimezone(tz)
        day_key = local_start.date()
        if day_key not in groups:
            order.append(day_key)
        groups[day_key].append(slot)
    return [(day.strftime('%A, %B %-d'), groups[day]) for day in order]


def _load_roles():
    """Return (participant, streamer, moderator, tech) roles or None for each if missing."""
    try:
        return (
            EventRole.objects.get(slug='participant'),
            EventRole.objects.get(slug='streamer'),
            EventRole.objects.get(slug='moderator'),
            EventRole.objects.get(slug='tech-manager'),
        )
    except EventRole.DoesNotExist:
        return None, None, None, None


def _slot_qs_for_role(slots, role):
    if role is None:
        return slots.none()
    return slots.filter(roles=role)


def _build_hour_map(event, slot_field_pairs):
    """
    Build a dict of {hour: {as_participant, as_streamer, as_moderator, as_tech}}
    from a list of (selected_slot_id_strings, field_name) pairs.
    """
    hour_map = {}
    slot_cache = {s.pk: s for s in EventSignupSlot.objects.filter(event=event)}
    for slot_ids, field in slot_field_pairs:
        for slot_id_str in slot_ids:
            if not slot_id_str.isdigit():
                continue
            slot = slot_cache.get(int(slot_id_str))
            if slot is None:
                continue
            for hour in _expand_to_hours(slot):
                if hour not in hour_map:
                    hour_map[hour] = {
                        'as_participant': False,
                        'as_streamer': False,
                        'as_moderator': False,
                        'as_tech': False,
                    }
                hour_map[hour][field] = True
    return hour_map


def _save_signup(request, event, participant_games, streamer_games, participant_role, streamer_role):
    """
    Validate and save a POST submission.
    Returns (interest, created, errors). On errors, interest/created are None.
    """
    display_name = request.POST.get('display_name', '').strip()
    preferences = request.POST.get('preferences', '').strip()
    acknowledged = bool(request.POST.get('acknowledged'))
    fundraising_url = request.POST.get('fundraising_url', '').strip() or None
    participant_notes = request.POST.get('participant_notes', '').strip()
    streamer_notes = request.POST.get('streamer_notes', '').strip()

    if not acknowledged:
        return None, None, ["You must acknowledge the Fragforce rules to sign up."]

    interest, created = EventInterest.objects.update_or_create(
        user=request.user,
        event=event,
        defaults={
            'display_name': display_name,
            'preferences': preferences,
            'acknowledged': acknowledged,
            'fundraising_url': fundraising_url,
            'participant_notes': participant_notes,
            'streamer_notes': streamer_notes,
        },
    )

    # Rebuild hourly availability
    interest.eventavailabilityinterest_set.all().delete()
    hour_map = _build_hour_map(event, [
        (request.POST.getlist('participant_slots'), 'as_participant'),
        (request.POST.getlist('streamer_slots'), 'as_streamer'),
        (request.POST.getlist('moderator_slots'), 'as_moderator'),
        (request.POST.getlist('tech_slots'), 'as_tech'),
    ])
    EventAvailabilityInterest.objects.bulk_create([
        EventAvailabilityInterest(event_interest=interest, hour=hour, **flags)
        for hour, flags in sorted(hour_map.items())
    ])

    # Sync game selections - one row per (game, role)
    GameInterestUserEvent.objects.filter(event_interest=interest).delete()
    game_role_rows = []
    if participant_role:
        for gid in participant_games.filter(pk__in=request.POST.getlist('participant_games')).values_list('pk', flat=True):
            game_role_rows.append(GameInterestUserEvent(event_interest=interest, game_id=gid, role=participant_role))
    if streamer_role:
        for gid in streamer_games.filter(pk__in=request.POST.getlist('streamer_games')).values_list('pk', flat=True):
            game_role_rows.append(GameInterestUserEvent(event_interest=interest, game_id=gid, role=streamer_role))
    GameInterestUserEvent.objects.bulk_create(game_role_rows, ignore_conflicts=True)

    return interest, created, []


def _prefill_from_post(request):
    """Build prefill and selected dicts from a POST request (used after validation failure)."""
    prefill = {
        'display_name': request.POST.get('display_name', ''),
        'preferences': request.POST.get('preferences', ''),
        'acknowledged': bool(request.POST.get('acknowledged')),
        'fundraising_url': request.POST.get('fundraising_url', ''),
        'participant_notes': request.POST.get('participant_notes', ''),
        'streamer_notes': request.POST.get('streamer_notes', ''),
    }
    selected_slot_ids = {
        'participant': {int(x) for x in request.POST.getlist('participant_slots') if x.isdigit()},
        'streamer': {int(x) for x in request.POST.getlist('streamer_slots') if x.isdigit()},
        'moderator': {int(x) for x in request.POST.getlist('moderator_slots') if x.isdigit()},
        'tech': {int(x) for x in request.POST.getlist('tech_slots') if x.isdigit()},
    }
    selected_game_ids = {
        'participant': {int(x) for x in request.POST.getlist('participant_games') if x.isdigit()},
        'streamer': {int(x) for x in request.POST.getlist('streamer_games') if x.isdigit()},
    }
    return prefill, selected_slot_ids, selected_game_ids


def _prefill_from_existing(existing, slot_qs_by_track, participant_games, streamer_games):
    """Build prefill and selected dicts from a saved EventInterest."""
    prefill = {
        'display_name': existing.display_name,
        'preferences': existing.preferences,
        'acknowledged': existing.acknowledged,
        'fundraising_url': existing.fundraising_url or '',
        'participant_notes': existing.participant_notes,
        'streamer_notes': existing.streamer_notes,
    }

    existing_hours = set(
        existing.eventavailabilityinterest_set.values_list(
            'hour', 'as_participant', 'as_streamer', 'as_moderator', 'as_tech'
        )
    )
    hours_by_track = {
        'participant': {h for h, p, s, m, t in existing_hours if p},
        'streamer': {h for h, p, s, m, t in existing_hours if s},
        'moderator': {h for h, p, s, m, t in existing_hours if m},
        'tech': {h for h, p, s, m, t in existing_hours if t},
    }

    selected_slot_ids = {track: set() for track in hours_by_track}
    for track, slots in slot_qs_by_track.items():
        track_hours = hours_by_track[track]
        for slot in slots:
            if all(h in track_hours for h in _expand_to_hours(slot)):
                selected_slot_ids[track].add(slot.pk)

    participant_game_ids = set(
        existing.gameinterestuserevent_set
        .filter(role__slug='participant')
        .values_list('game_id', flat=True)
    )
    streamer_game_ids = set(
        existing.gameinterestuserevent_set
        .filter(role__slug='streamer')
        .values_list('game_id', flat=True)
    )
    selected_game_ids = {
        'participant': participant_game_ids & set(participant_games.values_list('pk', flat=True)),
        'streamer': streamer_game_ids & set(streamer_games.values_list('pk', flat=True)),
    }

    return prefill, selected_slot_ids, selected_game_ids


@login_required
@require_http_methods(["GET", "POST"])
def signup_view(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)

    is_locked = event.locked
    existing = EventInterest.objects.filter(user=request.user, event=event).first()
    can_signup = event.signups_open and not is_locked
    can_edit = event.edits_open and not is_locked

    if is_locked:
        return render(request, 'evtsignup/signup.html', {'event': event, 'locked': True})

    if existing and not can_edit:
        return render(request, 'evtsignup/signup.html', {
            'event': event, 'locked': False, 'edits_closed': True, 'existing': existing,
        })

    slots = EventSignupSlot.objects.filter(event=event).prefetch_related('roles').order_by('start')
    if not slots.exists():
        can_signup = False

    if not existing and not can_signup:
        return render(request, 'evtsignup/signup.html', {
            'event': event, 'locked': False, 'signups_closed': True,
        })

    tz = zoneinfo.ZoneInfo(event.timezone)
    participant_role, streamer_role, moderator_role, tech_role = _load_roles()
    participant_slots = _slot_qs_for_role(slots, participant_role)
    streamer_slots = _slot_qs_for_role(slots, streamer_role)
    moderator_slots = _slot_qs_for_role(slots, moderator_role)
    tech_slots = _slot_qs_for_role(slots, tech_role)

    participant_games = Game.objects.filter(status='approved', suggested=True).exclude(multiplayer_max=1).order_by('name')
    streamer_games = Game.objects.filter(status='approved', suggested=True).order_by('name')

    errors = []

    if request.method == 'POST':
        _, created, errors = _save_signup(request, event, participant_games, streamer_games, participant_role, streamer_role)
        if not errors:
            if created:
                messages.success(request, "Your signup has been received!")
            else:
                messages.success(request, "Your signup has been updated.")
            return redirect('evtsignup-signup', event_slug=event_slug)

    slot_qs_by_track = {
        'participant': participant_slots,
        'streamer': streamer_slots,
        'moderator': moderator_slots,
        'tech': tech_slots,
    }

    if errors:
        prefill, selected_slot_ids, selected_game_ids = _prefill_from_post(request)
    elif existing:
        prefill, selected_slot_ids, selected_game_ids = _prefill_from_existing(
            existing, slot_qs_by_track, participant_games, streamer_games
        )
    else:
        prefill = {}
        selected_slot_ids = {track: set() for track in slot_qs_by_track}
        selected_game_ids = {'participant': set(), 'streamer': set()}

    context = {
        'event': event,
        'existing': existing,
        'errors': errors,
        'prefill': prefill,
        'participant_slot_days': _group_slots_by_day(participant_slots, tz),
        'streamer_slot_days': _group_slots_by_day(streamer_slots, tz),
        'moderator_slot_days': _group_slots_by_day(moderator_slots, tz),
        'tech_slot_days': _group_slots_by_day(tech_slots, tz),
        # flat lists still needed for track visibility checks
        'participant_slots': participant_slots,
        'streamer_slots': streamer_slots,
        'moderator_slots': moderator_slots,
        'tech_slots': tech_slots,
        'participant_games': participant_games,
        'streamer_games': streamer_games,
        'selected_slot_ids': selected_slot_ids,
        'selected_game_ids': selected_game_ids,
    }
    return render(request, 'evtsignup/signup.html', context)
