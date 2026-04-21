import zoneinfo

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path

from eventer.models import Event, EventPeriod, EventRole, EventSlotConfig, EventSlotTemplate, Game, Team, TeamMember, TeamRole
from eventer.slot_generator import generate_slots

SUPERSTREAM_ROLES = [
    {'name': 'Participant', 'slug': 'participant', 'description': 'Game participant - plays games with a streamer'},
    {'name': 'Streamer', 'slug': 'streamer', 'description': 'Streams and leads a time slot'},
    {'name': 'Moderator', 'slug': 'moderator', 'description': 'Moderates chat and provides streamer backup'},
    {'name': 'Tech Manager', 'slug': 'tech-manager', 'description': 'Manages stream tech and coordinates handoffs'},
]


@admin.register(EventPeriod)
class EventPeriodAdmin(admin.ModelAdmin):
    pass


@admin.register(EventRole)
class EventRoleAdmin(admin.ModelAdmin):
    change_list_template = 'admin/eventer/eventrole/change_list.html'

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


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    change_form_template = 'admin/eventer/event/change_form.html'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:event_id>/setup-superstream/',
                 self.admin_site.admin_view(self.setup_superstream_view),
                 name='eventer_event_setup_superstream'),
            path('<int:event_id>/generate-slots/',
                 self.admin_site.admin_view(self.generate_slots_view),
                 name='eventer_event_generate_slots'),
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
                return HttpResponseRedirect(f'../../{event_id}/change/')
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

        existing_count = event.slot_templates.count()
        context = {
            **self.admin_site.each_context(request),
            'event': event,
            'existing_count': existing_count,
            'errors': errors,
            'title': f'Generate Slot Templates - {event.name}',
        }
        return render(request, 'admin/eventer/event/generate_slots.html', context)

@admin.register(EventSlotConfig)
class EventSlotConfigAdmin(admin.ModelAdmin):
    pass


@admin.register(EventSlotTemplate)
class EventSlotTemplateAdmin(admin.ModelAdmin):
    list_display = ['event', 'label', 'start', 'stop']
    list_filter = ['event']
    filter_horizontal = ['roles']


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
