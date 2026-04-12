import logging
import warnings

import discord
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand

log = logging.getLogger(__name__)

# Suppress PyNaCl warning - voice is not used
warnings.filterwarnings('ignore', message='PyNaCl is not installed')


class Command(BaseCommand):
    help = 'Run the Fragforce Discord bot'

    def handle(self, *args, **options):
        intents = discord.Intents.default()
        bot = discord.Bot(intents=intents)

        guild_ids = [int(settings.DISCORD_REQUIRED_GUILD_ID)] if settings.DISCORD_REQUIRED_GUILD_ID else None

        @bot.event
        async def on_ready():
            log.info("Fragforce bot logged in as %s (ID: %s)", bot.user, bot.user.id)

        @bot.slash_command(
            name="stream-key",
            description="Fetch your stream key",
            guild_ids=guild_ids,
        )
        async def stream_key(ctx):
            from evtsignup.models import DiscordEventUser
            from ffstream.models import Key

            discord_id = str(ctx.author.id)

            def get_key():
                try:
                    deu = DiscordEventUser.objects.get(discord_id=discord_id)
                    return Key.objects.filter(owner=deu.user).first()
                except DiscordEventUser.DoesNotExist:
                    return None

            key = await sync_to_async(get_key)()

            if key is None:
                await ctx.respond(
                    "No stream key found for your account. "
                    "Log in at https://fragforce.org/stream/my-keys to generate one.",
                    ephemeral=True,
                )
                return

            await ctx.respond(
                f"**Your Stream Key:** `{key.stream_key}`\n"
                f"Super Stream: {'Yes' if key.superstream else 'No'} | "
                f"Direct Livestream: {'Yes' if key.livestream else 'No'}",
                ephemeral=True,
            )

        bot.run(settings.DISCORD_BOT_TOKEN)
