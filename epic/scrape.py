import json
import asyncio
import discord

from aiologger.loggers.json import JsonLogger
from aiologger.handlers.files import AsyncFileHandler

logger = JsonLogger()
handler = AsyncFileHandler(filename="./epic/import/history/message_dump.json")
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
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


async def log_message(message):
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
