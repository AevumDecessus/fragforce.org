from django.contrib import admin

from .models import DiscordRole, DiscordRoleMapping


@admin.register(DiscordRole)
class DiscordRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'discord_role_id')
    search_fields = ('name', 'discord_role_id')


@admin.register(DiscordRoleMapping)
class DiscordRoleMappingAdmin(admin.ModelAdmin):
    list_display = ('role', 'group', 'grants_staff_access', 'description')
    search_fields = ('role__name', 'role__discord_role_id', 'group__name', 'description')
