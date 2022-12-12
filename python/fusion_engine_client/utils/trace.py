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


# Define Logger TRACE level and associated trace() function if it doesn't exist.
if not hasattr(logging, 'TRACE'):
    logging.TRACE = logging.DEBUG - 1
    if sys.version_info.major == 2:
        logging._levelNames['TRACE'] = logging.TRACE
        logging._levelNames[logging.TRACE] = 'TRACE'
    else:
        logging._nameToLevel['TRACE'] = logging.TRACE
        logging._levelToName[logging.TRACE] = 'TRACE'

    def trace(self, msg, depth=1, *args, **kwargs):
        # Trace messages increase in verbosity with increasing depth, starting from 1:
        # - Depth 1 (Level == TRACE): Default
        # - Depth 2 (Level == TRACE - 1): More verbose
        # - etc.
        if depth < 1:
            depth = 1
        self.log(logging.TRACE - (depth - 1), msg, *args, **kwargs)
    logging.Logger.trace = trace

    def setLevel(self, level, depth=1, *args, **kwargs):
        return self.real_setLevel(logging._checkLevel(level) - (depth - 1), *args, **kwargs)
    logging.Logger.real_setLevel = logging.Logger.setLevel
    logging.Logger.setLevel = setLevel

    def isEnabledFor(self, level, depth=1, *args, **kwargs):
        return self.real_isEnabledFor(logging._checkLevel(level) - (depth - 1), *args, **kwargs)
    logging.Logger.real_isEnabledFor = logging.Logger.isEnabledFor
    logging.Logger.isEnabledFor = isEnabledFor


__all__ = [HighlightFormatter]
