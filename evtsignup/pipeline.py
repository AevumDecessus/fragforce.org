from evtsignup.models import DiscordEventUser


def save_discord_id(backend, user, response, *args, **kwargs):
    """Populate DiscordEventUser with the Discord user ID after login."""
    if backend.name != 'discord-oauth2':
        return
    discord_id = str(response.get('id', ''))
    if not discord_id:
        return
    DiscordEventUser.objects.update_or_create(
        user=user,
        defaults={'discord_id': discord_id},
    )
