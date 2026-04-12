import logging

from django.contrib.auth.models import User

from ffdiscord.models import DiscordRoleMapping

log = logging.getLogger(__name__)


def sync_user_roles(user: User, discord_role_ids: list[str]) -> None:
    """Sync a user's Django group membership from their Discord role IDs.

    Adds groups for Discord roles that have a mapping and removes groups
    that are mapped but no longer held by the user.
    """
    mappings = DiscordRoleMapping.objects.select_related('group').all()
    if not mappings:
        return

    mapped_groups = {m.group for m in mappings}
    entitled_groups = {m.group for m in mappings if m.discord_role_id in discord_role_ids}

    current_groups = set(user.groups.filter(id__in=[g.id for g in mapped_groups]))

    to_add = entitled_groups - current_groups
    to_remove = current_groups - entitled_groups

    if to_add:
        user.groups.add(*to_add)
        log.info("Added groups %s to user %s", [g.name for g in to_add], user.username)

    if to_remove:
        user.groups.remove(*to_remove)
        log.info("Removed groups %s from user %s", [g.name for g in to_remove], user.username)
