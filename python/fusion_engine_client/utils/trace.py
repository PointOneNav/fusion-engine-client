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
