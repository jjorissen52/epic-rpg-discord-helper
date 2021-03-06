import inspect
from typing import List, Optional, Callable, Union

from asgiref.sync import sync_to_async

from epic.models import Server
from epic.types.classes import RCDMessage, Namespace


class Handler:
    _server_unset = True  # keep track of whether the server has been queried for
    _server = None
    client = None
    trigger = None
    incoming = None
    content = None
    tokens = []
    content_limit = 250

    def __init__(self, client, incoming, server=None):
        self.client = client
        self.incoming = Namespace.from_collection(incoming)
        self.content = self.incoming.content[: self.content_limit].lower()
        self._server = server

    def should_trigger(self):
        return self.incoming.content.startswith(self.trigger)

    def _get_server(self) -> Optional[Server]:
        if not self._server and self._server_unset:
            self._server = Server.objects.filter(id=self.incoming.channel.guild.id).first()
            self._server_unset = False
        return self._server

    @property
    def server(self) -> Optional[Server]:
        return self._get_server()

    async def aget_server(self):
        return await sync_to_async(self._get_server)()

    def handle(self):
        raise NotImplemented()

    async def send_messages(self, messages: List[Union[str, RCDMessage]]):
        for message in messages:
            if isinstance(message, str):
                await self.incoming.channel.send(message)
            elif isinstance(message, RCDMessage):
                await self.incoming.channel.send(embed=message.to_embed())
            else:
                print(f"expected a string or RCDMessage, got {message}")
        return

    async def perform_coroutine(self, coroutine: Optional[Callable], *args):
        if not coroutine:
            return [], (None, ())
        if not inspect.iscoroutinefunction(coroutine):
            coroutine = sync_to_async(coroutine)
        messages, (next_coroutine, args) = await coroutine(*args)
        if messages:
            await self.send_messages(messages)
        if next_coroutine:
            return await self.perform_coroutine(next_coroutine, *args)
