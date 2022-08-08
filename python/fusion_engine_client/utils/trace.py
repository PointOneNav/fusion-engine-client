import logging
import sys

__all__ = []

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
        return self.real_setLevel(level - (depth - 1), *args, **kwargs)
    logging.Logger.real_setLevel = logging.Logger.setLevel
    logging.Logger.setLevel = setLevel

    def isEnabledFor(self, level, depth=1, *args, **kwargs):
        return self.real_isEnabledFor(level - (depth - 1), *args, **kwargs)
    logging.Logger.real_isEnabledFor = logging.Logger.isEnabledFor
    logging.Logger.isEnabledFor = isEnabledFor
