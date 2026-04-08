import requests
from django.conf import settings
from social_core.exceptions import AuthForbidden

from evtsignup.models import DiscordEventUser


def require_discord_guild(backend, response, *args, **kwargs):
    """Deny login if the user is not a member of the required Discord guild."""
    if backend.name != 'discord-oauth2':
        return
    required_guild_id = settings.DISCORD_REQUIRED_GUILD_ID
    if not required_guild_id:
        return
    access_token = kwargs.get('access_token', '')
    guilds = requests.get(
        'https://discord.com/api/users/@me/guilds',
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=10,
    ).json()
    guild_ids = {str(g['id']) for g in guilds} if isinstance(guilds, list) else set()
    if str(required_guild_id) not in guild_ids:
        raise AuthForbidden(backend)


def save_discord_id(backend, user, response, *args, **kwargs):
    """Populate DiscordEventUser with the Discord user ID and display name after login."""
    if backend.name != 'discord-oauth2':
        return
    discord_id = str(response.get('id', ''))
    if not discord_id:
        return
    display_name = response.get('global_name') or response.get('username', '')
    DiscordEventUser.objects.update_or_create(
        user=user,
        defaults={'discord_id': discord_id, 'discord_display_name': display_name},
    )
