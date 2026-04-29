import zoneinfo
from collections import defaultdict

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_safe

from eventer.models import Event, EventScheduleAssignment
from eventer.schedule import build_schedule_grid, generate_twitch_commands


def _signup_link_context(event, user):
    """Return show_signup_link, show_edit_link, and show_profile_link for an event."""
    has_signup = (
        user.is_authenticated and
        event.eventinterest_set.filter(user=user).exists()
    )
    is_locked = event.locked
    can_signup = event.signups_open and not is_locked
    can_edit = event.edits_open and not is_locked
    # Profile link shown when user has a signup but full edits are unavailable
    show_profile = has_signup and not can_edit
    return {
        'show_signup_link': can_signup and not has_signup,
        'show_edit_link': can_edit and has_signup,
        'show_profile_link': show_profile,
    }


@require_safe
def event_list(request):
    # Show events that are in progress or haven't ended yet
    now = timezone.now()
    events = (
        Event.objects
        .filter(public=True, eventperiod__isnull=False, eventperiod__stop__gte=now)
        .distinct()
        .prefetch_related('eventperiod_set')
        .order_by('eventperiod__start')
    )
    return render(request, 'eventer/event_list.html', {'events': events})


@require_safe
def event_detail(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    context = {
        'event': event,
        **_signup_link_context(event, request.user),
    }
    return render(request, 'eventer/event_detail.html', context)


def _assignments_by_slot(assignments, tz):
    """
    Group assignments by local day then slot.
    Returns (days, role_names) where days is a list of
    {day_label, rows: [{slot, local_label, assignments: {role_name: user_or_None}}]}
    """
    role_names_ordered = []
    role_names_seen = set()
    slot_role_user = defaultdict(dict)
    slots_ordered = []
    slots_seen = set()

    for a in assignments:
        if a.role.name not in role_names_seen:
            role_names_seen.add(a.role.name)
            role_names_ordered.append(a.role.name)
        slot_role_user[a.slot.pk][a.role.name] = a.user
        if a.slot.pk not in slots_seen:
            slots_seen.add(a.slot.pk)
            slots_ordered.append(a.slot)

    days = defaultdict(list)
    day_order = []
    for slot in slots_ordered:
        local_start = slot.start.astimezone(tz)
        day_key = local_start.date()
        if day_key not in days:
            day_order.append(day_key)
        days[day_key].append({
            'slot': slot,
            'local_label': local_start.strftime('%-I%p').lower(),
            'assignments': {rn: slot_role_user[slot.pk].get(rn) for rn in role_names_ordered},
        })

    result = []
    for day in day_order:
        rows = []
        for row in days[day]:
            # Convert assignments dict to ordered list matching role_names_ordered
            row['cells'] = [
                row['assignments'].get(rn)
                for rn in role_names_ordered
            ]
            rows.append(row)
        result.append({'day_label': day.strftime('%A, %B %-d'), 'rows': rows})
    return result, role_names_ordered


def _display_name_map(event, user_ids):
    """Return {user_id: display_name} using EventInterest.display_name, falling back to username."""
    from evtsignup.models import EventInterest
    interests = (
        EventInterest.objects
        .filter(event=event, user_id__in=user_ids)
        .select_related('user')
        .values('user_id', 'display_name', 'user__username')
    )
    return {
        row['user_id']: row['display_name'] or row['user__username']
        for row in interests
    }


@require_safe
def public_schedule_view(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    is_coordinator = request.user.has_perm('eventer.view_coordinator_schedule')
    if not event.schedule_published and not is_coordinator:
        return render(request, 'eventer/schedule_not_published.html', {'event': event})

    tz = zoneinfo.ZoneInfo(event.timezone)

    streamer_assignments = list(
        EventScheduleAssignment.objects
        .filter(event=event, role__slug='streamer')
        .select_related('slot', 'role', 'user', 'game')
        .order_by('slot__start')
    )

    # Build display name map for all assigned users
    user_ids = {a.user_id for a in streamer_assignments}
    if request.user.is_authenticated:
        user_ids.add(request.user.pk)
    display_names = _display_name_map(event, user_ids)

    my_slots = []
    if request.user.is_authenticated:
        my_slots = list(
            EventScheduleAssignment.objects
            .filter(event=event, user=request.user)
            .select_related('slot', 'role')
            .order_by('slot__start')
        )

    # Annotate assignments with display names for the template
    for a in streamer_assignments:
        a.display_name = display_names.get(a.user_id, a.user.username)
    for s in my_slots:
        s.display_name = display_names.get(s.user_id, s.user.username) if hasattr(s, 'user') else ''

    context = {
        'event': event,
        'tz': tz,
        'streamer_assignments': streamer_assignments,
        'my_slots': my_slots,
    }
    return render(request, 'eventer/public_schedule.html', context)


@require_safe
@login_required
@permission_required('eventer.view_coordinator_schedule', raise_exception=True)
def coordinator_schedule_view(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    grid = build_schedule_grid(event)

    # Annotate assigned users with display names
    from evtsignup.models import EventInterest
    user_ids = {
        a.user_id
        for row in grid['rows']
        for cell in row['cells']
        if cell['type'] == 'slot' and cell.get('assigned')
        for a in [cell['assigned']]
    } | {
        a.user_id
        for row in grid['rows']
        for mcell in row.get('multi_cells_list', [])
        if mcell.get('type') == 'slot'
        for a in mcell.get('assigned', [])
    }
    display_names = {}
    if user_ids:
        for row in EventInterest.objects.filter(event=event, user_id__in=user_ids).values('user_id', 'display_name', 'user__username'):
            display_names[row['user_id']] = row['display_name'] or row['user__username']

    for row in grid['rows']:
        for cell in row['cells']:
            if cell['type'] == 'slot' and cell.get('assigned'):
                a = cell['assigned']
                display = display_names.get(a.user_id, a.user.username)
                cell['assigned_display'] = display
                if cell['role_slug'] == 'streamer':
                    game_name = a.game.name if a.game else ''
                    title_cmd, game_cmd, donate_cmd = generate_twitch_commands(
                        event, cell['slot'], display, game_name
                    )
                    cell['title_cmd'] = title_cmd
                    cell['game_cmd'] = game_cmd
                    cell['donate_cmd'] = donate_cmd

    # Annotate multi-assignment cells with display names
    for row in grid['rows']:
        for mcell in row.get('multi_cells_list', []):
            if mcell.get('type') == 'slot' and mcell.get('assigned'):
                for a in mcell['assigned']:
                    a.display_name = display_names.get(a.user_id, a.user.username)

    streamer_color = next(
        (r['color'] for r in grid['role_headers'] if r['label'] == 'Streamer'),
        '#417690'
    )
    context = {
        'event': event,
        'rows': grid['rows'],
        'role_headers': grid['role_headers'],
        'multi_role_headers': grid['multi_role_headers'],
        'streamer_color': streamer_color,
    }
    return render(request, 'eventer/coordinator_schedule.html', context)
