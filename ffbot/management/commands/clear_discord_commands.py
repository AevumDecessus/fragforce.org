import asyncio
import logging

import discord
from django.conf import settings
from django.core.management.base import BaseCommand

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Remove all registered Discord slash commands for the bot'

    async def _clear(self):
        bot = discord.Bot()
        await bot.login(settings.DISCORD_BOT_TOKEN)
        app_id = int(settings.SOCIAL_AUTH_DISCORD_KEY)

        if settings.DISCORD_REQUIRED_GUILD_ID:
            guild_id = int(settings.DISCORD_REQUIRED_GUILD_ID)
            await bot.http.bulk_upsert_guild_commands(app_id, guild_id, [])
            self.stdout.write(self.style.SUCCESS(f"Cleared guild commands for guild {guild_id}"))
        else:
            await bot.http.bulk_upsert_global_commands(app_id, [])
            self.stdout.write(self.style.SUCCESS("Cleared global commands"))

        await bot.close()

    def handle(self, *args, **options):
        asyncio.run(self._clear())
