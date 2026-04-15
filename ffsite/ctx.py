import datetime
from datetime import timezone

from django.conf import settings

from ffdiscord.validators import discord_oauth_credentials_valid


def common_org(request):
    """ Context processors for all ffsite pages """
    return dict(
        now=datetime.datetime.now(tz=timezone.utc),
        gaid=settings.GOOGLE_ANALYTICS_ID,
        discord_login_enabled=discord_oauth_credentials_valid(
            settings.SOCIAL_AUTH_DISCORD_KEY,
            settings.SOCIAL_AUTH_DISCORD_SECRET,
        ),
    )
