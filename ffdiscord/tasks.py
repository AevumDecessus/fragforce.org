import asyncio
import logging

from asgiref.sync import sync_to_async
from celery import shared_task
from django.conf import settings

from ffbot.utils import get_or_register_user
from ffdiscord.utils import sync_guild_roles, sync_user_roles

log = logging.getLogger(__name__)


@shared_task
def sync_discord_roles():
    """Fetch all guild roles from Discord and upsert DiscordRole records."""
    asyncio.run(_sync_roles())


@shared_task
def sync_all_guild_members():
    """Fetch all guild members from Discord, register any new users, and sync roles."""
    asyncio.run(_sync_members())


async def _sync_roles():
    import discord
    intents = discord.Intents.default()
    bot = discord.Bot(intents=intents)

    @bot.event
    async def on_ready():
        try:
            guild = bot.get_guild(int(settings.DISCORD_REQUIRED_GUILD_ID))
            if guild is None:
                log.error("Guild %s not found", settings.DISCORD_REQUIRED_GUILD_ID)
                return
            all_roles = [(str(r.id), r.name) for r in guild.roles if not r.is_default()]
            await sync_to_async(sync_guild_roles)(all_roles)
            log.info("Synced %d guild roles", len(all_roles))
        finally:
            await bot.close()

    await bot.start(settings.DISCORD_BOT_TOKEN, reconnect=False)


async def _sync_members():
    import discord
    intents = discord.Intents.default()
    intents.members = True
    bot = discord.Bot(intents=intents)

    @bot.event
    async def on_ready():
        try:
            guild = bot.get_guild(int(settings.DISCORD_REQUIRED_GUILD_ID))
            if guild is None:
                log.error("Guild %s not found", settings.DISCORD_REQUIRED_GUILD_ID)
                return

            synced = 0
            async for member in guild.fetch_members(limit=None):
                if member.bot:
                    continue
                discord_id = str(member.id)
                role_ids = [str(r.id) for r in member.roles]

                def _sync(discord_id=discord_id, role_ids=role_ids, name=member.name):
                    user = get_or_register_user(discord_id, name)
                    sync_user_roles(user, role_ids)

                await sync_to_async(_sync)()
                synced += 1

            log.info("Synced roles for %d guild members", synced)
        finally:
            await bot.close()

    await bot.start(settings.DISCORD_BOT_TOKEN, reconnect=False)
