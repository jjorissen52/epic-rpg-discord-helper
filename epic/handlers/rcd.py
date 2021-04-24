from typing import Optional, Tuple, List, Callable

from epic.cmd import handle_rcd_command
from epic.handlers.base import Handler
from epic.utils import tokenize, RCDMessage


class RCDHandler(Handler):
    def __init__(self, clint, incoming, server=None):
        super().__init__(clint, incoming, server)
        tokens = tokenize(self.content)
        if tokens and tokens[0] in ["rcd", "rrd"]:
            self.tokens = ["rd", *tokens[1:]] if tokens[0] == "rrd" else tokens[1:]

    @property
    def should_trigger(self):
        if self.tokens and self.client.user:
            if self.server:
                return self.server.active
            return True
        return False

    def handle(self) -> Tuple[List[RCDMessage], Tuple[Optional[Callable]], tuple]:
        if not self.should_trigger:
            print(1)
            return [], (None, ())
        return handle_rcd_command(self.client, self.tokens, self.incoming, self.server, None, None)
