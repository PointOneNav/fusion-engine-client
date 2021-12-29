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

    def trace(self, msg, *args, **kwargs):
        self.log(logging.TRACE, msg, *args, **kwargs)
    logging.Logger.trace = trace
