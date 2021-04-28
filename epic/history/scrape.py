import asyncio
import json
import time
import discord
import datetime

from aiologger.loggers.json import JsonLogger
from aiologger.handlers.files import AsyncFileHandler

logger = JsonLogger()
handler = AsyncFileHandler(filename="/tmp/message_dump.json")
logger.add_handler(handler)


def get_author(author):
    return (
        {
            "id": author.id,
            "name": author.name,
            "discriminator": author.discriminator,
            "bot": author.bot,
            "icon_url": getattr(author, "icon_url", None),
            "guild": {
                "name": author.guild.name,
                "id": author.guild.id,
            }
            if getattr(author, "guild", None)
            else None,
        }
        if author
        else None
    )


def get_field(field):
    return {
        "name": getattr(field, "name", None),
        "value": getattr(field, "value", None),
        "inline": getattr(field, "inline", False),
    }


def get_channel(channel):
    return (
        {
            "name": channel.name,
            "id": channel.id,
        }
        if channel
        else None
    )


class DiscordEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (discord.Embed, discord.embeds.EmbedProxy)):
            return obj.__repr__()
        elif isinstance(obj, discord.embeds._EmptyEmbed):
            return None
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


async def log_message(message, logger=logger):
    message_basic = {
        "author": get_author(message.author),
        "created_at": message.created_at,
        "content": str(message.content),
        "channel": get_channel(message.channel),
        "embeds": [
            {
                "title": embed.title,
                "description": embed.description,
                "footer": embed.footer,
                "author": get_author(embed.author),
                "fields": [get_field(field) for field in embed.fields],
            }
            for embed in message.embeds
        ],
    }
    await logger.info(json.dumps(message_basic, cls=DiscordEncoder))
    return logger


async def scrape_channel(channel, start, file, limit=None):
    logger = JsonLogger()
    handler = AsyncFileHandler(filename=file)
    logger.add_handler(handler)
    limit = int(limit) if limit and limit.isdigit() else None
    async for m in channel.history(limit=limit):
        logger = await log_message(m, logger=logger)
    await logger.shutdown()
    return file, int(time.time() - start)


async def scrape_channels(channels, limit=None) -> int:
    start = int(time.time())
    files = [f"/tmp/{start}_{c.id}_dump.json" for c in channels]
    await asyncio.gather(*(scrape_channel(c, start, files[i], limit) for i, c in enumerate(channels)))
    return files, int(time.time() - start)
