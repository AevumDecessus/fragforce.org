import logging

import requests
from django.conf import settings
from social_core.exceptions import AuthForbidden

log = logging.getLogger(__name__)

from evtsignup.models import DiscordEventUser


def require_discord_guild(backend, response, *args, **kwargs):
    """Deny login if the user is not a member of the required Discord guild."""
    if backend.name != 'discord':
        return
    required_guild_id = settings.DISCORD_REQUIRED_GUILD_ID
    if not required_guild_id:
        return
    access_token = kwargs.get('access_token') or (response or {}).get('access_token', '')
    log.info("require_discord_guild: access_token present=%s length=%d", bool(access_token), len(access_token))
    guilds = requests.get(
        'https://discord.com/api/users/@me/guilds',
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=10,
    ).json()
    if not isinstance(guilds, list):
        log.warning("Discord guilds API returned unexpected response: %r", guilds)
        raise AuthForbidden(backend)
    guild_ids = {str(g['id']) for g in guilds}
    log.info("Discord guild IDs for user: %s", guild_ids)
    if str(required_guild_id) not in guild_ids:
        log.warning("User not in required guild %s, found: %s", required_guild_id, guild_ids)
        raise AuthForbidden(backend)


def save_discord_id(backend, user, response, *args, **kwargs):
    """Populate DiscordEventUser with the Discord user ID after login."""
    if backend.name != 'discord':
        return
    discord_id = str(response.get('id', ''))
    if not discord_id:
        return
    DiscordEventUser.objects.update_or_create(
        user=user,
        defaults={'discord_id': discord_id},
    )
