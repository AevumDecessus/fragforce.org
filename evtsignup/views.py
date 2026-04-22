import zoneinfo
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

from eventer.models import Event, EventSignupSlot, EventRole, Game
from evtsignup.models import EventInterest, EventAvailabilityInterest, GameInterestUserEvent


def _slot_ids_for_role(slots_qs, role):
    return list(slots_qs.filter(roles=role).values_list('id', flat=True))


def _expand_to_hours(slot):
    """Yield each UTC hour datetime from slot.start up to (not including) slot.stop."""
    current = slot.start.replace(minute=0, second=0, microsecond=0)
    while current < slot.stop:
        yield current
        current += timedelta(hours=1)


@login_required
def signup_view(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    tz = zoneinfo.ZoneInfo(event.timezone)

    # Determine what's allowed
    is_locked = event.locked
    existing = EventInterest.objects.filter(user=request.user, event=event).first()
    can_signup = event.signups_open and not is_locked
    can_edit = event.edits_open and not is_locked

    if is_locked:
        return render(request, 'evtsignup/signup.html', {
            'event': event,
            'locked': True,
        })

    if existing and not can_edit:
        return render(request, 'evtsignup/signup.html', {
            'event': event,
            'locked': False,
            'edits_closed': True,
            'existing': existing,
        })

    if not existing and not can_signup:
        return render(request, 'evtsignup/signup.html', {
            'event': event,
            'locked': False,
            'signups_closed': True,
        })

    # Load roles and slots
    slots = EventSignupSlot.objects.filter(event=event).prefetch_related('roles').order_by('start')
    try:
        participant_role = EventRole.objects.get(slug='participant')
        streamer_role = EventRole.objects.get(slug='streamer')
        moderator_role = EventRole.objects.get(slug='moderator')
        tech_role = EventRole.objects.get(slug='tech-manager')
    except EventRole.DoesNotExist:
        participant_role = streamer_role = moderator_role = tech_role = None

    participant_slots = slots.filter(roles=participant_role) if participant_role else slots.none()
    streamer_slots = slots.filter(roles=streamer_role) if streamer_role else slots.none()
    moderator_slots = slots.filter(roles=moderator_role) if moderator_role else slots.none()
    tech_slots = slots.filter(roles=tech_role) if tech_role else slots.none()

    participant_games = Game.objects.filter(status='approved', suggested=True).exclude(multiplayer_max=1).order_by('name')
    streamer_games = Game.objects.filter(status='approved', suggested=True).order_by('name')

    errors = []

    if request.method == 'POST':
        display_name = request.POST.get('display_name', '').strip()
        preferences = request.POST.get('preferences', '').strip()
        acknowledged = bool(request.POST.get('acknowledged'))
        fundraising_url = request.POST.get('fundraising_url', '').strip() or None
        participant_notes = request.POST.get('participant_notes', '').strip()
        streamer_notes = request.POST.get('streamer_notes', '').strip()

        if not acknowledged:
            errors.append("You must acknowledge the Fragforce rules to sign up.")

        selected_participant_slots = set(request.POST.getlist('participant_slots'))
        selected_streamer_slots = set(request.POST.getlist('streamer_slots'))
        selected_moderator_slots = set(request.POST.getlist('moderator_slots'))
        selected_tech_slots = set(request.POST.getlist('tech_slots'))
        selected_participant_games = set(request.POST.getlist('participant_games'))
        selected_streamer_games = set(request.POST.getlist('streamer_games'))

        if not errors:
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
            hour_map = {}  # hour -> kwargs dict

            def _add_hours(slot_ids_selected, field):
                for slot_id_str in slot_ids_selected:
                    try:
                        slot = EventSignupSlot.objects.get(pk=int(slot_id_str), event=event)
                    except (EventSignupSlot.DoesNotExist, ValueError):
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

            _add_hours(selected_participant_slots, 'as_participant')
            _add_hours(selected_streamer_slots, 'as_streamer')
            _add_hours(selected_moderator_slots, 'as_moderator')
            _add_hours(selected_tech_slots, 'as_tech')

            EventAvailabilityInterest.objects.bulk_create([
                EventAvailabilityInterest(event_interest=interest, hour=hour, **flags)
                for hour, flags in sorted(hour_map.items())
            ])

            # Sync game selections
            GameInterestUserEvent.objects.filter(event_interest=interest).delete()
            valid_participant_game_ids = set(
                participant_games.filter(pk__in=selected_participant_games).values_list('pk', flat=True)
            )
            valid_streamer_game_ids = set(
                streamer_games.filter(pk__in=selected_streamer_games).values_list('pk', flat=True)
            )
            all_game_ids = valid_participant_game_ids | valid_streamer_game_ids
            GameInterestUserEvent.objects.bulk_create([
                GameInterestUserEvent(event_interest=interest, game_id=gid)
                for gid in all_game_ids
            ])

            if created:
                messages.success(request, "Your signup has been received!")
            else:
                messages.success(request, "Your signup has been updated.")
            return redirect('evtsignup-signup', event_slug=event_slug)

    # Pre-populate: from POST data on validation error, otherwise from saved signup
    prefill = {}
    selected_slot_ids = {'participant': set(), 'streamer': set(), 'moderator': set(), 'tech': set()}
    selected_game_ids = {'participant': set(), 'streamer': set()}

    if errors:
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
    elif existing:
        prefill = {
            'display_name': existing.display_name,
            'preferences': existing.preferences,
            'acknowledged': existing.acknowledged,
            'fundraising_url': existing.fundraising_url or '',
            'participant_notes': existing.participant_notes,
            'streamer_notes': existing.streamer_notes,
        }
        # Reconstruct which slots were selected from hourly rows
        existing_hours = set(
            existing.eventavailabilityinterest_set.values_list('hour', 'as_participant', 'as_streamer', 'as_moderator', 'as_tech')
        )
        participant_hours = {h for h, p, s, m, t in existing_hours if p}
        streamer_hours = {h for h, p, s, m, t in existing_hours if s}
        moderator_hours = {h for h, p, s, m, t in existing_hours if m}
        tech_hours = {h for h, p, s, m, t in existing_hours if t}

        for slot in participant_slots:
            if all(h in participant_hours for h in _expand_to_hours(slot)):
                selected_slot_ids['participant'].add(slot.pk)
        for slot in streamer_slots:
            if all(h in streamer_hours for h in _expand_to_hours(slot)):
                selected_slot_ids['streamer'].add(slot.pk)
        for slot in moderator_slots:
            if all(h in moderator_hours for h in _expand_to_hours(slot)):
                selected_slot_ids['moderator'].add(slot.pk)
        for slot in tech_slots:
            if all(h in tech_hours for h in _expand_to_hours(slot)):
                selected_slot_ids['tech'].add(slot.pk)

        existing_game_ids = set(existing.gameinterestuserevent_set.values_list('game_id', flat=True))
        selected_game_ids['participant'] = existing_game_ids & set(participant_games.values_list('pk', flat=True))
        selected_game_ids['streamer'] = existing_game_ids & set(streamer_games.values_list('pk', flat=True))

    context = {
        'event': event,
        'tz': tz,
        'existing': existing,
        'errors': errors,
        'prefill': prefill,
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
