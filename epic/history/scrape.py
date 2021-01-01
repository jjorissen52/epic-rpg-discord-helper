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


async def scrape(message, limit=None):
    start = time.time()
    print(start)
    limit = int(limit) if limit and limit.isdigit() else None
    print(limit)
    async for m in message.channel.history(limit=limit):
        print(m)
        logger = await log_message(m)
    await logger.shutdown()
    return f"<@!{message.author.id}> Your scrape has completed after {int(time.time() - start):,} seconds."


async def scrape_channels(channels, limit=None) -> int:
    start = time.time()
    files = [f"/tmp/{c.id}_{start}_dump.json" for c in channels]
    limit = int(limit) if limit and limit.isdigit() else None
    for i, c in enumerate(channels):
        logger = JsonLogger()
        handler = AsyncFileHandler(filename=files[i])
        logger.add_handler(handler)
        async for m in c.history(limit=limit):
            logger = await log_message(m, logger=logger)
        await logger.shutdown()
    return files, int(time.time() - start)
