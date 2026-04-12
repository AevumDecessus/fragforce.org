from django.contrib import admin

from .models import DiscordRoleMapping


@admin.register(DiscordRoleMapping)
class DiscordRoleMappingAdmin(admin.ModelAdmin):
    list_display = ('discord_role_id', 'group', 'description')
    search_fields = ('discord_role_id', 'group__name', 'description')
