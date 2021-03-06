import inspect

from pipeline import execution_pipeline

from epic.cmd import cmd  # must be imported to register commands
from epic.types import HandlerResult
from epic.utils import tokenize
from epic.types.classes import ErrorMessage


@execution_pipeline(pre=cmd.register.registry)
def handle_rcd_command(
    client, tokens, message, server, profile, msg, help=None, error=None, coro=None
) -> HandlerResult:
    _msg, _coro = msg, (None, ())
    if (error and not isinstance(error, str)) or not msg:
        original_tokens = tokenize(message.content[:250], preserve_case=True)
        _msg = ErrorMessage(f"`{' '.join(original_tokens)}` could not be parsed as a valid command.")
    elif error:
        _msg = ErrorMessage(error)
    if coro and inspect.iscoroutinefunction(coro[0]):
        _coro = coro
    return [_msg], _coro
