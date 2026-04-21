from django.contrib import admin, messages

from eventer.models import Event, EventPeriod, EventRole, Game, Team, TeamMember, TeamRole

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
    pass


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    actions = ['ensure_superstream_roles']

    @admin.action(description='Ensure Superstream event roles exist (Participant, Streamer, Moderator, Tech Manager)')
    def ensure_superstream_roles(self, request, queryset):
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
