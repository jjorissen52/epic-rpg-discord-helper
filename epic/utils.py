import datetime
import inspect
import re
import shlex
import operator
import functools
import sys
import traceback


def tokenize(cmd, preserve_case=False):
    if not cmd:
        return cmd
    if not preserve_case:
        cmd = cmd.lower()
    return shlex.split(cmd)


def int_from_token(token):
    token = token.strip()
    if re.match(r"^([0-9\* ]+)$", token):
        int_tokens, prod = token.replace(" ", "").split("*"), 1
        prod = functools.reduce(operator.mul, [int(t) for t in int_tokens], 1)
        return prod
    elif token.isdigit():
        return int(token)


def to_human_readable(delta: datetime.timedelta):
    total_seconds = int(delta.total_seconds())
    seconds = total_seconds % 60
    minutes = (total_seconds % 3600 - seconds) // 60
    hours = (total_seconds % (3600 * 24) - minutes - seconds) // 3600
    days = (total_seconds - hours - minutes - seconds) // (3600 * 24)
    return days, hours, minutes, seconds


def defaults_from(dict_obj, defaults):
    return [dict_obj.get(key, defaults[key]) for key in defaults]


def remove_span(string: str, span: tuple):
    span_begin, span_end = span
    return f"{string[:span_begin]}{string[span_end:]}"


def replace_span(string: str, new_string: str, span: tuple):
    span_begin, span_end = span
    return f"{string[:span_begin]}{new_string}{string[span_end:]}"


def ignore_broken_pipe(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BrokenPipeError:
            pass
        except SystemExit:
            raise
        except:  # noqa
            traceback.print_exc()
            exit(1)
        finally:
            try:
                sys.stdout.flush()
            finally:
                try:
                    sys.stdout.close()
                finally:
                    try:
                        sys.stderr.flush()
                    finally:
                        sys.stderr.close()

    # don't mask our function signature
    wrapper.__signature__ = inspect.signature(func)
    return wrapper
