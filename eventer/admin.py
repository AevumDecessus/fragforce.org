import zoneinfo

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path

from eventer.models import Event, EventPeriod, EventRole, EventSignupSlotConfig, EventSignupSlot, EventScheduleSlot, Game, Team, TeamMember, TeamRole, HOUR_SECONDS
from eventer.slot_generator import _expand_to_hours, generate_slots

SCHEDULE_ROLES = [
    ('participant', 'as_participant', 'Participant'),
    ('streamer', 'as_streamer', 'Streamer'),
    ('moderator', 'as_moderator', 'Moderator'),
    ('tech-manager', 'as_tech', 'Tech'),
]


def _build_schedule_grid(event):
    """
    Build a grid data structure for the schedule views.

    Returns a dict with:
      - rows: list of {hour, local, day, is_day_start, cells}
      - role_headers: list of display names
      - slot_role_available: {(slot.pk, role_slug): [user, ...]}
      - slot_role_assigned: {(slot.pk, role_slug): EventScheduleSlot or None}
      - role_objects: {slug: EventRole}
    """
    from datetime import timedelta
    from evtsignup.models import EventInterest

    tz = zoneinfo.ZoneInfo(event.timezone)
    event_start = event.start
    event_end = event.end

    if not event_start or not event_end:
        return {
            'rows': [], 'role_headers': [r[2] for r in SCHEDULE_ROLES],
            'slot_role_available': {}, 'slot_role_assigned': {}, 'role_objects': {},
        }

    all_hours = []
    cur = event_start.replace(minute=0, second=0, microsecond=0)
    while cur < event_end:
        all_hours.append(cur)
        cur += timedelta(hours=1)

    # hour → {role_slug: set of users}
    hour_role_users = {h: {slug: set() for slug, _, _ in SCHEDULE_ROLES} for h in all_hours}
    interests = (
        EventInterest.objects
        .filter(event=event)
        .select_related('user')
        .prefetch_related('eventavailabilityinterest_set')
    )
    for interest in interests:
        for avail in interest.eventavailabilityinterest_set.all():
            if avail.hour in hour_role_users:
                for slug, field, _ in SCHEDULE_ROLES:
                    if getattr(avail, field):
                        hour_role_users[avail.hour][slug].add(interest.user)

    # role → hour → slot
    role_hour_slot = {slug: {} for slug, _, _ in SCHEDULE_ROLES}
    for slot in event.signup_slots.prefetch_related('roles').order_by('start'):
        for role in slot.roles.all():
            if role.slug in role_hour_slot:
                for hour in _expand_to_hours(slot):
                    role_hour_slot[role.slug][hour] = slot

    # precompute available/assigned per (slot, role)
    role_objects = {r.slug: r for r in EventRole.objects.filter(slug__in=[s for s, _, _ in SCHEDULE_ROLES])}
    slot_role_available = {}
    slot_role_assigned = {}
    seen = set()
    for slug, _, _ in SCHEDULE_ROLES:
        for hour in all_hours:
            slot = role_hour_slot[slug].get(hour)
            if slot and (slot.pk, slug) not in seen:
                seen.add((slot.pk, slug))
                slot_hours = list(_expand_to_hours(slot))
                available = None
                for sh in slot_hours:
                    users = hour_role_users.get(sh, {}).get(slug, set())
                    available = users if available is None else available & users
                role_obj = role_objects.get(slug)
                assigned = None
                if role_obj:
                    assigned = EventScheduleSlot.objects.filter(
                        slot=slot, role=role_obj
                    ).select_related('user').first()
                slot_role_available[(slot.pk, slug)] = sorted(available or [], key=lambda u: u.username)
                slot_role_assigned[(slot.pk, slug)] = assigned

    # build rows
    role_next_hour = {slug: None for slug, _, _ in SCHEDULE_ROLES}
    rows = []
    for hour in all_hours:
        local_hour = hour.astimezone(tz)
        is_day_start = hour == all_hours[0] or local_hour.hour == 0
        cells = []
        for slug, _, _ in SCHEDULE_ROLES:
            slot = role_hour_slot[slug].get(hour)
            if slot is None:
                cells.append({'type': 'empty'})
            elif role_next_hour[slug] is not None and hour < role_next_hour[slug]:
                cells.append({'type': 'skip'})
            else:
                slot_hours = list(_expand_to_hours(slot))
                rowspan = len(slot_hours)
                from datetime import timedelta as _td
                role_next_hour[slug] = slot_hours[-1] + _td(hours=1) if slot_hours else hour + _td(hours=1)
                cells.append({
                    'type': 'slot',
                    'rowspan': rowspan,
                    'slot': slot,
                    'role_slug': slug,
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

    role_headers = [
        {'label': label, 'color': role_objects[slug].color if slug in role_objects else '#417690'}
        for slug, _, label in SCHEDULE_ROLES
    ]

    return {
        'rows': rows,
        'role_headers': role_headers,
        'slot_role_available': slot_role_available,
        'slot_role_assigned': slot_role_assigned,
        'role_objects': role_objects,
    }


SUPERSTREAM_ROLES = [
    {'name': 'Participant', 'slug': 'participant', 'description': 'Game participant - plays games with a streamer'},
    {'name': 'Streamer', 'slug': 'streamer', 'description': 'Streams and leads a time slot'},
    {'name': 'Moderator', 'slug': 'moderator', 'description': 'Moderates chat and provides streamer backup'},
    {'name': 'Tech Manager', 'slug': 'tech-manager', 'description': 'Manages stream tech and coordinates handoffs'},
]


@admin.register(EventPeriod)
class EventPeriodAdmin(admin.ModelAdmin):
    pass


class EventRoleAdminForm(forms.ModelForm):
    color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'style': 'width:4em;height:2em;padding:0;cursor:pointer'}),
        max_length=7,
    )

    class Meta:
        model = EventRole
        fields = '__all__'


@admin.register(EventRole)
class EventRoleAdmin(admin.ModelAdmin):
    change_list_template = 'admin/eventer/eventrole/change_list.html'
    form = EventRoleAdminForm
    list_display = ['name', 'slug', 'color_swatch']

    @admin.display(description='Color')
    def color_swatch(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<span style="display:inline-block;width:1.2em;height:1.2em;background:{};border:1px solid #ccc;vertical-align:middle;border-radius:2px;margin-right:4px"></span>{}',
            obj.color, obj.color
        )

    class Media:
        # Use browser native color input - no extra JS needed
        pass

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('seed-superstream/',
                 self.admin_site.admin_view(self.seed_superstream_view),
                 name='eventer_eventrole_seed_superstream'),
        ]
        return custom + urls

    def seed_superstream_view(self, request):
        created = []
        existing = []
        for role_data in SUPERSTREAM_ROLES:
            _, was_created = EventRole.objects.get_or_create(
                slug=role_data['slug'],
                defaults={'name': role_data['name'], 'description': role_data['description']},
            )
            if was_created:
                created.append(role_data['name'])
            else:
                existing.append(role_data['name'])

        if created:
            self.message_user(request, f"Created roles: {', '.join(created)}", messages.SUCCESS)
        if existing:
            self.message_user(request, f"Already existed: {', '.join(existing)}", messages.INFO)

        return HttpResponseRedirect('../')


class HasEventPeriodFilter(admin.SimpleListFilter):
    title = 'event period'
    parameter_name = 'has_period'

    def lookups(self, request, model_admin):
        return [
            ('yes', 'Scheduled (has period)'),
            ('no', 'Unscheduled (no period)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(eventperiod__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(eventperiod__isnull=True)
        return queryset


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    change_form_template = 'admin/eventer/event/change_form.html'
    list_display = ['name', 'slug', 'event_start']
    list_filter = [HasEventPeriodFilter]
    prepopulated_fields = {'slug': ('name',)}

    def response_add(self, request, obj, post_url_continue=None):
        return HttpResponseRedirect(f'../../eventsignupslotconfig/add/?event={obj.pk}')

    @admin.display(description='Start', ordering='eventperiod__start')
    def event_start(self, obj):
        period = obj.eventperiod_set.order_by('start').first()
        if period is None:
            return '-'
        tz = zoneinfo.ZoneInfo(obj.timezone)
        return period.start.astimezone(tz).strftime('%Y-%m-%d %H:%M %Z')

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:event_id>/setup-superstream/',
                 self.admin_site.admin_view(self.setup_superstream_view),
                 name='eventer_event_setup_superstream'),
            path('<int:event_id>/generate-slots/',
                 self.admin_site.admin_view(self.generate_slots_view),
                 name='eventer_event_generate_slots'),
            path('<int:event_id>/availability/',
                 self.admin_site.admin_view(self.availability_summary_view),
                 name='eventer_event_availability_summary'),
            path('<int:event_id>/build-schedule/',
                 self.admin_site.admin_view(self.build_schedule_view),
                 name='eventer_event_build_schedule'),
            path('<int:event_id>/assign-slot/',
                 self.admin_site.admin_view(self.assign_slot_view),
                 name='eventer_event_assign_slot'),
        ]
        return custom + urls

    def setup_superstream_view(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        existing_periods = list(event.eventperiod_set.all())
        errors = None

        if request.method == 'POST':
            start_str = request.POST.get('start', '').strip()
            duration_str = request.POST.get('duration', '40').strip()
            try:
                duration = int(duration_str)
                if duration < 1:
                    raise ValueError("Duration must be at least 1 hour")
                # Parse the datetime-local value (naive, in event's timezone)
                from datetime import datetime, timedelta
                naive_start = datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
                tz = zoneinfo.ZoneInfo(event.timezone)
                local_start = naive_start.replace(tzinfo=tz)
                utc_start = local_start.astimezone(zoneinfo.ZoneInfo('UTC'))
                utc_stop = utc_start + timedelta(hours=duration)
                EventPeriod.objects.create(event=event, start=utc_start, stop=utc_stop)
                self.message_user(
                    request,
                    f"Added {duration}-hour period starting {local_start.strftime('%Y-%m-%d %H:%M %Z')}",
                    messages.SUCCESS,
                )
                return HttpResponseRedirect(f'../../{event_id}/generate-slots/')
            except (ValueError, KeyError) as e:
                errors = str(e)

        context = {
            **self.admin_site.each_context(request),
            'event': event,
            'existing_periods': existing_periods,
            'errors': errors,
            'form_start': '',
            'title': f'Add Superstream Period - {event.name}',
        }
        return render(request, 'admin/eventer/event/setup_superstream.html', context)

    def generate_slots_view(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        errors = None

        if request.method == 'POST':
            replace = request.POST.get('replace') == '1'
            try:
                result = generate_slots(event, replace=replace)
                self.message_user(
                    request,
                    f"Generated slots: {result['created']} created, "
                    f"{result['skipped']} already existed, "
                    f"{result['deleted']} deleted.",
                    messages.SUCCESS,
                )
                return HttpResponseRedirect(f'../../{event_id}/change/')
            except ValueError as e:
                errors = str(e)

        existing_slots = list(event.signup_slots.prefetch_related('roles').order_by('start'))
        context = {
            **self.admin_site.each_context(request),
            'event': event,
            'existing_slots': existing_slots,
            'existing_count': len(existing_slots),
            'errors': errors,
            'title': f'Generate Signup Slots - {event.name}',
        }
        return render(request, 'admin/eventer/event/generate_slots.html', context)

    def availability_summary_view(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        grid = _build_schedule_grid(event)
        context = {
            **self.admin_site.each_context(request),
            'event': event,
            'rows': grid['rows'],
            'role_headers': grid['role_headers'],
            'title': f'Availability Summary - {event.name}',
        }
        return render(request, 'admin/eventer/event/availability_summary.html', context)

    def build_schedule_view(self, request, event_id):
        from django.db import transaction
        from django_workflow_engine.executor import User
        event = get_object_or_404(Event, pk=event_id)

        if request.method == 'POST':
            with transaction.atomic():
                EventScheduleSlot.objects.filter(event=event).delete()
                created = 0
                for key, user_id in request.POST.items():
                    if not key.startswith('assign_') or not user_id:
                        continue
                    # key format: assign_{slot_pk}_{role_slug}
                    _, slot_pk, role_slug = key.split('_', 2)
                    try:
                        slot = EventSignupSlot.objects.get(pk=int(slot_pk), event=event)
                        role = EventRole.objects.get(slug=role_slug)
                        user = User.objects.get(pk=int(user_id))
                        EventScheduleSlot.objects.create(event=event, slot=slot, role=role, user=user)
                        created += 1
                    except Exception:
                        continue
            self.message_user(request, f"Schedule saved: {created} assignment(s).", messages.SUCCESS)
            return HttpResponseRedirect(f'../../{event_id}/build-schedule/')

        grid = _build_schedule_grid(event)
        context = {
            **self.admin_site.each_context(request),
            'event': event,
            'rows': grid['rows'],
            'role_headers': grid['role_headers'],
            'title': f'Build Schedule - {event.name}',
        }
        return render(request, 'admin/eventer/event/build_schedule.html', context)

    def assign_slot_view(self, request, event_id):
        """Assign or unassign a single slot/role - inline fine-tuning from availability grid."""
        from django_workflow_engine.executor import User
        if request.method != 'POST':
            return HttpResponseRedirect(f'../../{event_id}/availability/')
        event = get_object_or_404(Event, pk=event_id)
        slot_pk = request.POST.get('slot_pk')
        role_slug = request.POST.get('role_slug')
        user_id = request.POST.get('user_id', '').strip()
        try:
            slot = EventSignupSlot.objects.get(pk=int(slot_pk), event=event)
            role = EventRole.objects.get(slug=role_slug)
            EventScheduleSlot.objects.filter(slot=slot, role=role).delete()
            if user_id:
                user = User.objects.get(pk=int(user_id))
                EventScheduleSlot.objects.create(event=event, slot=slot, role=role, user=user)
                self.message_user(request, f"Assigned {user.username} to {slot.label} ({role.name}).", messages.SUCCESS)
            else:
                self.message_user(request, f"Cleared assignment for {slot.label} ({role.name}).", messages.INFO)
        except Exception as e:
            self.message_user(request, f"Error: {e}", messages.ERROR)
        return HttpResponseRedirect(f'../../{event_id}/availability/')

@admin.register(EventSignupSlotConfig)
class EventSignupSlotConfigAdmin(admin.ModelAdmin):
    def response_add(self, request, obj, post_url_continue=None):
        return HttpResponseRedirect(f'../../event/{obj.event_id}/setup-superstream/')


@admin.register(EventSignupSlot)
class EventSignupSlotAdmin(admin.ModelAdmin):
    list_display = ['event', 'role_list', 'label', 'duration_hours', 'start_local', 'stop_local', 'start_utc', 'stop_utc']
    list_filter = ['event', 'roles']
    filter_horizontal = ['roles']

    @admin.display(description='Roles')
    def role_list(self, obj):
        return ', '.join(obj.roles.values_list('name', flat=True))

    @admin.display(description='Duration')
    def duration_hours(self, obj):
        return f'{int((obj.stop - obj.start).total_seconds() / HOUR_SECONDS)}h'

    @admin.display(description='Start (Local)', ordering='start')
    def start_local(self, obj):
        tz = zoneinfo.ZoneInfo(obj.event.timezone)
        return obj.start.astimezone(tz).strftime('%a %b %-d %-I%p %Z')

    @admin.display(description='Stop (Local)', ordering='stop')
    def stop_local(self, obj):
        tz = zoneinfo.ZoneInfo(obj.event.timezone)
        return obj.stop.astimezone(tz).strftime('%a %b %-d %-I%p %Z')

    @admin.display(description='Start (UTC)', ordering='start')
    def start_utc(self, obj):
        return obj.start

    @admin.display(description='Stop (UTC)', ordering='stop')
    def stop_utc(self, obj):
        return obj.stop


@admin.register(EventScheduleSlot)
class EventScheduleSlotAdmin(admin.ModelAdmin):
    list_display = ['event', 'role', 'slot_label', 'slot_start_local', 'user']
    list_filter = ['event', 'role']
    raw_id_fields = ['user']

    @admin.display(description='Slot', ordering='slot__start')
    def slot_label(self, obj):
        return obj.slot.label

    @admin.display(description='Start (Local)', ordering='slot__start')
    def slot_start_local(self, obj):
        tz = zoneinfo.ZoneInfo(obj.event.timezone)
        return obj.slot.start.astimezone(tz).strftime('%a %b %-d %-I%p %Z')


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'suggested', 'multiplayer_max']
    list_filter = ['status', 'suggested']
    search_fields = ['name', 'igdb_slug']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    pass


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    pass


@admin.register(TeamRole)
class TeamRoleAdmin(admin.ModelAdmin):
    pass
