# Import all logging stuff here locally for caller convenience. That way, the caller can do the following to get both
# built-in logging support and additional trace support:
#   import fusion_engine_client.utils.trace as logging
from logging import *

import logging
import sys

try:
    import colorama

    # This function was added in colorama 0.4.6, but some users may be using an earlier version. It only affects
    # operation in Windows. The deprecated alternative is to call colorama.init().
    try:
        colorama.just_fix_windows_console()
    except AttributeError:
        colorama.init()
except ImportError:
    colorama = None


class HighlightFormatter(logging.Formatter):
    def __init__(self, color=True, color_map=None, standoff_level=None, parent_formatter=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if parent_formatter is not None:
            for key, value in parent_formatter.__dict__.items():
                setattr(self, key, value)

        if color and colorama is None:
            print('WARNING: colorama library not found. Cannot highlight logging output in color.')
            self.color_map = None
        else:
            if color_map is None:
                self.color_map = {
                    logging.FATAL: colorama.Back.RED + colorama.Fore.BLACK,
                    logging.ERROR: colorama.Fore.RED,
                    logging.WARNING: colorama.Fore.CYAN,
                    logging.INFO: None,
                }
            else:
                self.color_map = color_map

        if standoff_level is None:
            # Set to max + 1 to disable.
            self.standoff_level = logging.FATAL + 1
        else:
            self.standoff_level = standoff_level

    def format(self, record):
        text = super().format(record)
        if self.color_map is not None:
            color = None
            for level in (logging.FATAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG, logging.TRACE):
                if record.levelno >= level:
                    color = self.color_map.get(level, None)
                    break

            if color is not None:
                text = f'{color}{text}{colorama.Style.RESET_ALL}'

        if record.levelno >= self.standoff_level:
            text = '\n%s\n' % text

        return text

    @classmethod
    def install(cls, streams=None, *args, **kwargs):
        if streams is None:
            streams = (sys.stdout, sys.stderr)

        streams = [sys.stdout if s == 'stdout' else s for s in streams]
        streams = [sys.stderr if s == 'stderr' else s for s in streams]

        for h in logging.root.handlers:
            if isinstance(h, logging.StreamHandler) and h.stream in streams:
                formatter = HighlightFormatter(parent_formatter=h.formatter, *args, **kwargs)
                h.setFormatter(formatter)


class SilentLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        if isinstance(name, logging.Logger):
            name = name.name
        super().__init__(name=name, level=level)
        self.disabled = True


# Define Logger TRACE level and associated trace() function. These are extensions of the built-in logging library.

if not hasattr(logging, 'TRACE'):
    TRACE = logging.DEBUG - 1
    logging.TRACE = TRACE
    if sys.version_info.major == 2:
        logging._levelNames['TRACE'] = logging.TRACE
        logging._levelNames[logging.TRACE] = 'TRACE'
    else:
        logging._nameToLevel['TRACE'] = logging.TRACE
        logging._levelToName[logging.TRACE] = 'TRACE'
else:
    TRACE = logging.TRACE


def getTraceLevel(depth=1):
    # Trace messages increase in verbosity with increasing depth, starting from 1:
    # - Depth 1 (Level == TRACE): Default
    # - Depth 2 (Level == TRACE - 1): More verbose
    # - etc.
    if depth < 1:
        depth = 1
    return logging.TRACE - (depth - 1)


if not hasattr(logging.Logger, 'trace'):
    def _trace_member(self, msg, depth=1, *args, **kwargs):
        # The stacklevel value (1) tells findCaller() to get the line number one function call up from log() in
        # logging/__init__.py. Since we have an function call (this one) in between log() and the caller, we need to
        # pop up the stack one extra call.
        if 'stacklevel' in kwargs:
            kwargs['stacklevel'] += 1
        else:
            kwargs['stacklevel'] = 2

        self.log(getTraceLevel(depth), msg, *args, **kwargs)
    logging.Logger.trace = _trace_member


def trace(msg, depth=1, *args, **kwargs):
    """
    Log a message with severity 'TRACE' on the root logger. If the logger has
    no handlers, call basicConfig() to add a console handler with a pre-defined
    format.
    """
    if len(logging.root.handlers) == 0:
        logging.basicConfig()
    logging.root.trace(msg, depth=depth, *args, **kwargs)
