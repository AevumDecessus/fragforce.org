import zoneinfo
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods

from eventer.models import Event, EventSignupSlot, EventRole, Game
from eventer.slot_generator import _expand_to_hours
from evtsignup.models import EventInterest, EventAvailabilityHour, GameInterestUserEvent

SIGNUP_TEMPLATE = 'evtsignup/signup.html'


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


def _game_qs_for_role(role):
    """Return the approved/suggested game queryset for a role, filtered by game_min_players."""
    qs = Game.objects.filter(status='approved', suggested=True)
    if role.game_min_players is not None:
        qs = qs.exclude(Q(multiplayer_max__lt=role.game_min_players) & Q(multiplayer_max__isnull=False))
    return qs


def _build_hour_role_set(event, roles_with_slots, post_data):
    """Build a set of (hour, role) tuples from POST data. Field per role is '{slug}_slots'."""
    result = set()
    slot_cache = {s.pk: s for s in EventSignupSlot.objects.filter(event=event)}
    for role in roles_with_slots:
        for slot_id_str in post_data.getlist(f'{role.slug}_slots'):
            if not slot_id_str.isdigit():
                continue
            slot = slot_cache.get(int(slot_id_str))
            if slot is None:
                continue
            for hour in _expand_to_hours(slot):
                result.add((hour, role))
    return result


def _save_signup(request, event, roles_with_slots, game_qs_by_slug):
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
    interest.eventavailabilityhour_set.all().delete()
    hour_role_pairs = _build_hour_role_set(event, roles_with_slots, request.POST)
    EventAvailabilityHour.objects.bulk_create([
        EventAvailabilityHour(event_interest=interest, hour=hour, role=role)
        for hour, role in sorted(hour_role_pairs, key=lambda x: (x[0], x[1].slug))
    ])

    # Sync game selections - one row per (game, role)
    roles_by_slug = {r.slug: r for r in roles_with_slots}
    GameInterestUserEvent.objects.filter(event_interest=interest).delete()
    game_rows = []
    for slug, games_qs in game_qs_by_slug.items():
        role = roles_by_slug.get(slug)
        if role:
            for gid in games_qs.filter(pk__in=request.POST.getlist(f'{slug}_games')).values_list('pk', flat=True):
                game_rows.append(GameInterestUserEvent(event_interest=interest, game_id=gid, role=role))
    GameInterestUserEvent.objects.bulk_create(game_rows, ignore_conflicts=True)

    return interest, created, []


def _prefill_from_post(request, roles_with_slots, game_qs_by_slug):
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
        role.slug: {int(x) for x in request.POST.getlist(f'{role.slug}_slots') if x.isdigit()}
        for role in roles_with_slots
    }
    selected_game_ids = {
        slug: {int(x) for x in request.POST.getlist(f'{slug}_games') if x.isdigit()}
        for slug in game_qs_by_slug
    }
    return prefill, selected_slot_ids, selected_game_ids


def _prefill_from_existing(existing, slots_by_slug, game_qs_by_slug):
    """Build prefill and selected dicts from a saved EventInterest."""
    prefill = {
        'display_name': existing.display_name,
        'preferences': existing.preferences,
        'acknowledged': existing.acknowledged,
        'fundraising_url': existing.fundraising_url or '',
        'participant_notes': existing.participant_notes,
        'streamer_notes': existing.streamer_notes,
    }

    hours_by_slug = defaultdict(set)
    for hour, slug in existing.eventavailabilityhour_set.values_list('hour', 'role__slug'):
        hours_by_slug[slug].add(hour)

    selected_slot_ids = {
        slug: {
            slot.pk for slot in slots
            if all(h in hours_by_slug.get(slug, set()) for h in _expand_to_hours(slot))
        }
        for slug, slots in slots_by_slug.items()
    }

    # Fetch all game selections in one query then partition by slug
    game_selections_by_slug = defaultdict(set)
    for slug, game_id in existing.gameinterestuserevent_set.filter(
        role__slug__in=list(game_qs_by_slug.keys())
    ).values_list('role__slug', 'game_id'):
        game_selections_by_slug[slug].add(game_id)
    selected_game_ids = {
        slug: game_selections_by_slug[slug] & set(games_qs.values_list('pk', flat=True))
        for slug, games_qs in game_qs_by_slug.items()
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

    if existing and (is_locked or not can_edit):
        if request.method == 'POST':
            existing.display_name = request.POST.get('display_name', '').strip()
            existing.fundraising_url = request.POST.get('fundraising_url', '').strip() or None
            existing.save(update_fields=['display_name', 'fundraising_url'])
            messages.success(request, "Your profile has been updated.")
            return redirect('evtsignup-signup', event_slug=event_slug)
        return render(request, SIGNUP_TEMPLATE, {
            'event': event,
            'locked': is_locked,
            'profile_only': True,
            'existing': existing,
            'prefill': {
                'display_name': existing.display_name,
                'fundraising_url': existing.fundraising_url or '',
            },
        })

    if not existing and is_locked:
        return render(request, SIGNUP_TEMPLATE, {'event': event, 'locked': True})

    slots = EventSignupSlot.objects.filter(event=event).prefetch_related('roles').order_by('start')
    if not slots.exists():
        can_signup = False

    if not existing and not can_signup:
        return render(request, SIGNUP_TEMPLATE, {
            'event': event, 'locked': False, 'signups_closed': True,
        })

    tz = zoneinfo.ZoneInfo(event.timezone)

    # Only include roles that have slots on this event, preserving display_order
    all_roles = list(EventRole.objects.all())
    slot_role_ids = set(slots.values_list('roles', flat=True))
    roles_with_slots = [r for r in all_roles if r.pk in slot_role_ids]
    slots_by_slug = {r.slug: slots.filter(roles=r) for r in roles_with_slots}

    # Game querysets for roles that have game selection enabled
    game_qs_by_slug = {}
    for role in roles_with_slots:
        if not role.has_game_selection:
            continue
        qs = _game_qs_for_role(role)
        if existing:
            linked_ids = existing.gameinterestuserevent_set.filter(role=role).values_list('game_id', flat=True)
            qs = (qs | Game.objects.filter(pk__in=linked_ids).exclude(status='rejected')).distinct()
        game_qs_by_slug[role.slug] = qs.order_by('name')

    errors = []

    if request.method == 'POST':
        _, created, errors = _save_signup(request, event, roles_with_slots, game_qs_by_slug)
        if not errors:
            if created:
                messages.success(request, "Your signup has been received!")
            else:
                messages.success(request, "Your signup has been updated.")
            return redirect('evtsignup-signup', event_slug=event_slug)

    if errors:
        prefill, selected_slot_ids, selected_game_ids = _prefill_from_post(request, roles_with_slots, game_qs_by_slug)
    elif existing:
        prefill, selected_slot_ids, selected_game_ids = _prefill_from_existing(existing, slots_by_slug, game_qs_by_slug)
    else:
        prefill = {}
        selected_slot_ids = {r.slug: set() for r in roles_with_slots}
        selected_game_ids = {slug: set() for slug in game_qs_by_slug}

    # Notes fields are stored as named columns on EventInterest; map slug -> prefill value
    notes_by_slug = {
        'participant': prefill.get('participant_notes', ''),
        'streamer': prefill.get('streamer_notes', ''),
    }

    # Build per-role context list for template, preserving display_order
    role_tracks = []
    for role in roles_with_slots:
        slug = role.slug
        role_tracks.append({
            'role': role,
            'slug': slug,
            'slot_days': _group_slots_by_day(slots_by_slug[slug], tz),
            'slots': slots_by_slug[slug],
            'selected_slot_ids': selected_slot_ids.get(slug, set()),
            'games': game_qs_by_slug.get(slug),
            'selected_game_ids': selected_game_ids.get(slug, set()),
            'notes_prefill': notes_by_slug.get(slug, ''),
            'is_active': bool(
                selected_slot_ids.get(slug) or
                selected_game_ids.get(slug) or
                (role.show_fundraising_url and prefill.get('fundraising_url'))
            ),
        })

    context = {
        'event': event,
        'existing': existing,
        'errors': errors,
        'prefill': prefill,
        'role_tracks': role_tracks,
    }
    return render(request, SIGNUP_TEMPLATE, context)
