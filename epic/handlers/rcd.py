from epic.cmd import handle_rcd_command
from epic.handlers.base import Handler
from epic.types import HandlerResult
from epic.utils import tokenize


class RCDHandler(Handler):
    def __init__(self, clint, incoming, server=None):
        super().__init__(clint, incoming, server)
        tokens = tokenize(self.content)
        if tokens and tokens[0] in ["rcd", "rrd"]:
            self.tokens = ["rd", *tokens[1:]] if tokens[0] == "rrd" else tokens[1:]
            self.tokens = ["cd"] if not self.tokens else self.tokens

    @property
    def should_trigger(self):
        if self.tokens and self.client.user != self.incoming.author:
            if self.server:
                return self.server.active
            return True
        return False

    def handle(self) -> HandlerResult:
        if not self.should_trigger:
            return [], (None, ())
        return handle_rcd_command(self.client, self.tokens, self.incoming, self.server, None, None)
