"""
Slot template generator for Superstream events.

Generates EventSignupSlot records from an event's EventPeriod and EventSignupSlotConfig.
"""
import zoneinfo
from datetime import timedelta

from eventer.models import Event, EventRole, EventSignupSlotConfig, EventSignupSlot


def _format_label(start_local, stop_local):
    """
    Format a human-readable slot label.
    e.g. "Friday 8pm - 11pm" or "Friday 11pm - Saturday 2am"
    """
    def fmt_time(dt):
        return dt.strftime('%-I%p').lower()

    start_day = start_local.strftime('%A')
    stop_day = stop_local.strftime('%A')

    if start_day == stop_day:
        return f"{start_day} {fmt_time(start_local)} - {fmt_time(stop_local)}"
    return f"{start_day} {fmt_time(start_local)} - {stop_day} {fmt_time(stop_local)}"


def _variable_block_hours(local_dt, config):
    """ Return block size based on whether local_dt falls in prime time. """
    t = local_dt.time()
    if config.prime_time_start <= t < config.prime_time_end:
        return config.prime_block_hours
    return config.standard_block_hours


def _generate_grid(event, tz, start, stop, config, use_prime_time, roles, first_block_hours=None):
    """
    Generate slot templates for one role grid.

    Args:
        event: The Event
        tz: zoneinfo.ZoneInfo for label formatting
        start: UTC datetime for grid start
        stop: UTC datetime for grid end
        config: EventSignupSlotConfig instance
        use_prime_time: if True use variable block sizes, otherwise use management_block_hours
        roles: list of EventRole instances to assign
        first_block_hours: if set, override the block size for the first slot only

    Returns:
        (created, skipped) counts
    """
    created = skipped = 0
    current = start
    is_first = True

    while current < stop:
        local = current.astimezone(tz)

        if is_first and first_block_hours is not None:
            hours = first_block_hours
        elif use_prime_time:
            hours = _variable_block_hours(local, config)
        else:
            hours = config.management_block_hours

        is_first = False
        slot_stop = min(current + timedelta(hours=hours), stop)

        # If the remaining time after this slot is less than the minimum slot length,
        # absorb it into this slot rather than creating a stub at the end.
        min_slot_hours = max(config.prime_block_hours, 2)
        remaining = stop - slot_stop
        if timedelta(0) < remaining < timedelta(hours=min_slot_hours):
            slot_stop = stop

        label = _format_label(local, slot_stop.astimezone(tz))

        template, was_created = EventSignupSlot.objects.get_or_create(
            event=event,
            start=current,
            stop=slot_stop,
            defaults={'label': label},
        )
        if was_created:
            template.roles.set(roles)
            created += 1
        else:
            template.roles.add(*roles)
            skipped += 1

        current = slot_stop

    return created, skipped


def generate_slots(event: Event, replace: bool = False) -> dict:
    """
    Generate EventSignupSlot records for an event.

    Args:
        event: The Event to generate slots for
        replace: If True, delete existing slot templates before generating

    Returns:
        dict with keys 'created', 'skipped', 'deleted'

    Raises:
        ValueError: if required EventRoles are missing or event has no periods
    """
    if not event.eventperiod_set.exists():
        raise ValueError("Event has no periods. Add a period first.")

    try:
        participant_role = EventRole.objects.get(slug='participant')
        streamer_role = EventRole.objects.get(slug='streamer')
        moderator_role = EventRole.objects.get(slug='moderator')
        tech_role = EventRole.objects.get(slug='tech-manager')
    except EventRole.DoesNotExist as e:
        raise ValueError(
            f"Required EventRole not found: {e}. "
            "Run 'Seed Superstream Roles' first."
        )

    config, _ = EventSignupSlotConfig.objects.get_or_create(event=event)
    tz = zoneinfo.ZoneInfo(event.timezone)
    event_start = event.start
    event_stop = event.end

    deleted = 0
    if replace:
        deleted, _ = EventSignupSlot.objects.filter(event=event).delete()

    total_created = total_skipped = 0

    # Participant/Streamer: variable block sizes based on prime time
    c, s = _generate_grid(
        event, tz, event_start, event_stop, config,
        use_prime_time=True,
        roles=[participant_role, streamer_role],
    )
    total_created += c
    total_skipped += s

    # Tech: uniform management_block_hours blocks from event start
    c, s = _generate_grid(
        event, tz, event_start, event_stop, config,
        use_prime_time=False,
        roles=[tech_role],
    )
    total_created += c
    total_skipped += s

    # Moderator: shorter first block to stagger changeovers with tech
    c, s = _generate_grid(
        event, tz, event_start, event_stop, config,
        use_prime_time=False,
        roles=[moderator_role],
        first_block_hours=config.mod_first_block_hours,
    )
    total_created += c
    total_skipped += s

    return {'created': total_created, 'skipped': total_skipped, 'deleted': deleted}
