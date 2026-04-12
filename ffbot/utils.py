import logging

from django.contrib.auth.models import User
from django.utils.text import slugify

from evtsignup.models import DiscordEventUser
from social_django.models import UserSocialAuth

log = logging.getLogger(__name__)


def get_or_register_user(discord_id: str, discord_username: str) -> User:
    """Get or create a Django User for a Discord user.

    If the user already exists (via previous bot interaction or web OAuth),
    return them. Otherwise create a new account and link it to the Discord ID
    so that a future web OAuth login will associate the same account.
    """
    # Already linked via DiscordEventUser
    try:
        return DiscordEventUser.objects.get(discord_id=discord_id).user
    except DiscordEventUser.DoesNotExist:
        pass

    # Already linked via social auth (e.g. from a previous partial setup)
    try:
        return UserSocialAuth.objects.get(provider='discord', uid=discord_id).user
    except UserSocialAuth.DoesNotExist:
        pass

    # New user - create account
    base_username = slugify(discord_username.replace('.', '-'))
    username = base_username
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}-{suffix}"
        suffix += 1

    user = User.objects.create_user(username=username, email='')
    DiscordEventUser.objects.create(user=user, discord_id=discord_id)
    UserSocialAuth.objects.create(user=user, provider='discord', uid=discord_id, extra_data={})

    log.info("Registered new user %s from Discord ID %s", username, discord_id)
    return user
