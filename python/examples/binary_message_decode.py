#!/usr/bin/env python3

import logging
import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.messages.core import MessageHeader, MessagePayload
from fusion_engine_client.parsers import FusionEngineDecoder
from fusion_engine_client.utils import trace
from fusion_engine_client.utils.argument_parser import ArgumentParser

from examples.message_decode import print_message


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Decode and print the contents of one or more FusionEngine messages contained
in a binary string. For example:

> python3 binary_message_decode.py \\
  2e31 0000 0acf ee8f 0200 ca32 0000 0000 0400 0000 0000 0000 ff0f 0001

Successfully decoded 1 FusionEngine messages.
Header: RESET_REQUEST (13002) Message (version 0):
  Sequence #: 0
  Payload: 4 B
  Source: 0
  CRC: 0x8feecf0a
Payload: Reset Request [mask=0x01000fff]
""")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")
    parser.add_argument('contents', nargs='+',
                        help="Binary FusionEngine message contents, specified as a hex string. All spaces will be "
                             "ignored.")
    options = parser.parse_args()

    # Configure logging.
    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s',
                            stream=sys.stdout)
        if options.verbose == 1:
            logging.getLogger('point_one.fusion_engine').setLevel(logging.DEBUG)
        else:
            logging.getLogger('point_one.fusion_engine').setLevel(
                logging.getTraceLevel(depth=options.verbose - 1))
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)

    logger = logging.getLogger('point_one.fusion_engine')

    # Concatenate all hex characters and convert to bytes.
    contents_str = ''.join(options.contents).replace(' ', '')
    if len(contents_str) % 2 != 0:
        logger.error("Error: Contents must contain an even number of hex characters.")
        sys.exit(1)

    contents = bytes.fromhex(contents_str)

    # Decode the incoming data and print the contents of any complete messages.
    decoder = FusionEngineDecoder(warn_on_error=FusionEngineDecoder.WarnOnError.ALL, warn_on_unrecognized=True)
    messages = decoder.on_data(contents)
    if len(messages) > 0:
        logger.info("Successfully decoded %d FusionEngine messages." % len(messages))
        for i, (header, message) in enumerate(messages):
            if i > 0:
                logger.info('\n')

            logger.info("Header: " + str(header))
            if isinstance(message, MessagePayload):
                logger.info("Payload: " + str(message))
    else:
        # If we didn't detect any complete messages, see if maybe they didn't provide enough bytes?
        if len(contents) < MessageHeader.calcsize():
            logger.warning("Warning: Specified byte string too small to contain a valid FusionEngine message. "
                           "[size=%d B, minimum=%d B]" % (len(contents), MessageHeader.calcsize()))
        else:
            try:
                header = MessageHeader()
                header.unpack(contents)
                if len(contents) < header.get_message_size():
                    logger.warning('Warning: Specified byte string too small. [expected=%d B, got=%d B]' %
                                   (header.get_message_size(), len(contents)))
                    logger.warning("Header: " + str(header))
            except ValueError as e:
                logger.warning("No valid FusionEngine messages decoded.")

        sys.exit(2)
