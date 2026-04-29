"""
Shared schedule grid building utilities used by both admin views and public/coordinator views.
"""
import zoneinfo
from datetime import timedelta

from eventer.models import EventRole, EventScheduleAssignment, EventScheduleMultiAssignment
from eventer.slot_generator import _expand_to_hours

LOCAL_TIME_FMT = '%a %b %-d %-I%p %Z'

# Singular roles - enforced one user per (slot, role) via EventScheduleAssignment
SINGLE_ASSIGNMENT_ROLES = [
    ('streamer', 'as_streamer', 'Streamer'),
    ('moderator', 'as_moderator', 'Moderator'),
    ('tech-manager', 'as_tech', 'Tech'),
]

# Multi-user roles - multiple users per slot via EventScheduleMultiAssignment
MULTI_ASSIGNMENT_ROLES = [
    ('participant', 'as_participant', 'Participant'),
]


def _event_all_hours(event_start, event_end):
    hours = []
    cur = event_start.replace(minute=0, second=0, microsecond=0)
    while cur < event_end:
        hours.append(cur)
        cur += timedelta(hours=1)
    return hours


def _build_hour_role_users(event, all_hours):
    from evtsignup.models import EventInterest
    all_roles = SINGLE_ASSIGNMENT_ROLES + MULTI_ASSIGNMENT_ROLES
    hour_role_users = {h: {slug: set() for slug, _, _ in all_roles} for h in all_hours}
    interests = (
        EventInterest.objects
        .filter(event=event)
        .select_related('user')
        .prefetch_related('eventavailabilityinterest_set')
    )
    for interest in interests:
        for avail in interest.eventavailabilityinterest_set.all():
            if avail.hour in hour_role_users:
                for slug, field, _ in all_roles:
                    if getattr(avail, field):
                        hour_role_users[avail.hour][slug].add(interest.user)
    return hour_role_users


def _build_role_hour_slot(event):
    all_role_slugs = {slug for slug, _, _ in SINGLE_ASSIGNMENT_ROLES} | {slug for slug, _, _ in MULTI_ASSIGNMENT_ROLES}
    role_hour_slot = {slug: {} for slug in all_role_slugs}
    for slot in event.signup_slots.prefetch_related('roles').order_by('start'):
        for role in slot.roles.all():
            if role.slug in role_hour_slot:
                for hour in _expand_to_hours(slot):
                    role_hour_slot[role.slug][hour] = slot
    return role_hour_slot


def _build_slot_role_data(all_hours, role_hour_slot, hour_role_users, role_objects):
    slot_role_available = {}
    slot_role_assigned = {}
    seen = set()
    for slug, _, _ in SINGLE_ASSIGNMENT_ROLES:
        for hour in all_hours:
            slot = role_hour_slot[slug].get(hour)
            if not slot or (slot.pk, slug) in seen:
                continue
            seen.add((slot.pk, slug))
            available = None
            for sh in _expand_to_hours(slot):
                users = hour_role_users.get(sh, {}).get(slug, set())
                available = users if available is None else available & users
            role_obj = role_objects.get(slug)
            assigned = EventScheduleAssignment.objects.filter(
                slot=slot, role=role_obj
            ).select_related('user').first() if role_obj else None
            slot_role_available[(slot.pk, slug)] = sorted(available or [], key=lambda u: u.username)
            slot_role_assigned[(slot.pk, slug)] = assigned
    return slot_role_available, slot_role_assigned


def _build_grid_rows(all_hours, tz, role_hour_slot, role_objects, slot_role_available, slot_role_assigned):
    role_next_hour = {slug: None for slug, _, _ in SINGLE_ASSIGNMENT_ROLES}
    role_alt = {slug: False for slug, _, _ in SINGLE_ASSIGNMENT_ROLES}
    rows = []
    for hour in all_hours:
        local_hour = hour.astimezone(tz)
        is_day_start = hour == all_hours[0] or local_hour.hour == 0
        cells = []
        for slug, _, _ in SINGLE_ASSIGNMENT_ROLES:
            slot = role_hour_slot[slug].get(hour)
            if slot is None:
                cells.append({'type': 'empty'})
            elif role_next_hour[slug] is not None and hour < role_next_hour[slug]:
                cells.append({'type': 'skip'})
            else:
                slot_hours = list(_expand_to_hours(slot))
                role_next_hour[slug] = slot_hours[-1] + timedelta(hours=1) if slot_hours else hour + timedelta(hours=1)
                role_obj = role_objects.get(slug)
                role_alt[slug] = not role_alt[slug]
                cells.append({
                    'type': 'slot', 'rowspan': len(slot_hours),
                    'slot': slot, 'role_slug': slug,
                    'role_color': role_obj.color if role_obj else '#417690',
                    'alt': role_alt[slug],
                    'available': slot_role_available.get((slot.pk, slug), []),
                    'assigned': slot_role_assigned.get((slot.pk, slug)),
                })
        rows.append({
            'hour': hour,
            'local': local_hour.strftime('%-I%p'),
            'day': local_hour.strftime('%a %b %-d'),
            'is_day_start': is_day_start,
            'cells': cells,
        })
    return rows


def _build_multi_slot_data(event, all_hours, role_hour_slot, hour_role_users, role_objects):
    """
    Build available/assigned data for multi-assignment roles (e.g. Participant).
    Returns {(slot.pk, slug): {'available': [...], 'assigned': [...]}}
    """
    data = {}
    seen = set()
    for slug, _, _ in MULTI_ASSIGNMENT_ROLES:
        for hour in all_hours:
            slot = role_hour_slot.get(slug, {}).get(hour)
            if not slot or (slot.pk, slug) in seen:
                continue
            seen.add((slot.pk, slug))
            available = None
            for sh in _expand_to_hours(slot):
                users = hour_role_users.get(sh, {}).get(slug, set())
                available = users if available is None else available & users
            role_obj = role_objects.get(slug)
            assigned = list(EventScheduleMultiAssignment.objects.filter(
                slot=slot, role=role_obj
            ).select_related('user')) if role_obj else []
            data[(slot.pk, slug)] = {
                'available': sorted(available or [], key=lambda u: u.username),
                'assigned': assigned,
            }
    return data


def slot_hour_range(event_start, slot):
    """Return (start_hour, end_hour) 1-indexed relative to event start."""
    start_hour = int((slot.start - event_start).total_seconds() // 3600) + 1
    end_hour = int((slot.stop - event_start).total_seconds() // 3600)
    return start_hour, end_hour


def generate_twitch_commands(event, slot, streamer_display_name, game_name):
    """Generate the three Twitch bot command strings for a streamer slot."""
    if event.start:
        h_start, h_end = slot_hour_range(event.start, slot)
        hour_str = f'Hours {h_start}-{h_end}'
    else:
        hour_str = slot.label

    title_cmd = f'!settitle {event.name} | {hour_str}'
    game_cmd = f'!setgame {game_name}' if game_name else ''
    donate_cmd = f'!setteam {streamer_display_name}' if streamer_display_name else ''
    return title_cmd, game_cmd, donate_cmd


def build_schedule_grid(event):
    """
    Build hourly grid data structure for schedule views.
    Used by admin (availability summary, build schedule) and public coordinator view.
    """
    tz = zoneinfo.ZoneInfo(event.timezone)
    if not event.start or not event.end:
        return {
            'rows': [],
            'role_headers': [{'label': r[2], 'color': '#417690'} for r in SINGLE_ASSIGNMENT_ROLES],
            'multi_role_headers': [{'label': r[2], 'color': '#417690', 'slug': r[0]} for r in MULTI_ASSIGNMENT_ROLES],
            'slot_role_available': {}, 'slot_role_assigned': {},
            'multi_slot_data': {}, 'role_objects': {},
        }

    all_hours = _event_all_hours(event.start, event.end)
    hour_role_users = _build_hour_role_users(event, all_hours)
    role_hour_slot = _build_role_hour_slot(event)
    all_slugs = [s for s, _, _ in SINGLE_ASSIGNMENT_ROLES + MULTI_ASSIGNMENT_ROLES]
    role_objects = {r.slug: r for r in EventRole.objects.filter(slug__in=all_slugs)}
    slot_role_available, slot_role_assigned = _build_slot_role_data(
        all_hours, role_hour_slot, hour_role_users, role_objects
    )
    multi_slot_data = _build_multi_slot_data(
        event, all_hours, role_hour_slot, hour_role_users, role_objects
    )
    rows = _build_grid_rows(all_hours, tz, role_hour_slot, role_objects, slot_role_available, slot_role_assigned)
    role_headers = [
        {'label': label, 'color': role_objects[slug].color if slug in role_objects else '#417690'}
        for slug, _, label in SINGLE_ASSIGNMENT_ROLES
    ]
    multi_role_headers = [
        {'label': label, 'color': role_objects[slug].color if slug in role_objects else '#417690', 'slug': slug}
        for slug, _, label in MULTI_ASSIGNMENT_ROLES
    ]
    # Attach multi-assignment data to rows for template use
    for row in rows:
        row['multi_cells'] = {}
        for slug, _, _ in MULTI_ASSIGNMENT_ROLES:
            slot = role_hour_slot.get(slug, {}).get(row['hour'])
            if slot is None:
                row['multi_cells'][slug] = {'type': 'empty'}
            else:
                key = (slot.pk, slug)
                # Track rowspan for multi cells
                row['multi_cells'][slug] = {
                    'type': 'slot',
                    'slot': slot,
                    'role_slug': slug,
                    'role_color': role_objects[slug].color if slug in role_objects else '#417690',
                    'available': multi_slot_data.get(key, {}).get('available', []),
                    'assigned': multi_slot_data.get(key, {}).get('assigned', []),
                }

    # Compute rowspan for multi cells and build ordered list matching multi_role_headers
    multi_next_hour = {slug: None for slug, _, _ in MULTI_ASSIGNMENT_ROLES}
    multi_alt = {slug: False for slug, _, _ in MULTI_ASSIGNMENT_ROLES}
    for row in rows:
        for slug, _, _ in MULTI_ASSIGNMENT_ROLES:
            cell = row['multi_cells'].get(slug, {'type': 'empty'})
            if cell['type'] != 'empty':
                slot = cell['slot']
                if multi_next_hour[slug] is not None and row['hour'] < multi_next_hour[slug]:
                    row['multi_cells'][slug] = {'type': 'skip'}
                else:
                    slot_hours = list(_expand_to_hours(slot))
                    from datetime import timedelta
                    multi_next_hour[slug] = slot_hours[-1] + timedelta(hours=1) if slot_hours else row['hour'] + timedelta(hours=1)
                    multi_alt[slug] = not multi_alt[slug]
                    cell['rowspan'] = len(slot_hours)
                    cell['alt'] = multi_alt[slug]
        # Build ordered list for template (same order as multi_role_headers)
        row['multi_cells_list'] = [row['multi_cells'].get(slug, {'type': 'empty'}) for slug, _, _ in MULTI_ASSIGNMENT_ROLES]

    return {
        'rows': rows, 'role_headers': role_headers,
        'multi_role_headers': multi_role_headers,
        'slot_role_available': slot_role_available,
        'slot_role_assigned': slot_role_assigned,
        'multi_slot_data': multi_slot_data,
        'role_objects': role_objects,
    }
