#!/usr/bin/env python3

import os
import sys

try:
    import serial
except ImportError:
    print("This application requires pyserial. Please install (pip install pyserial) and run again.")
    sys.exit(1)

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.messages import MessagePayload
from fusion_engine_client.parsers import FusionEngineDecoder


if __name__ == "__main__":
    # Parse command-line arguments.
    parser = ArgumentParser(description="""\
Connect to a Point One device over serial and print out the incoming message
contents.
""")
    parser.add_argument('-b', '--baud', type=int, default=460800,
                        help="The serial baud rate to be used.")
    parser.add_argument('port',
                        help="The serial device to use (e.g., /dev/ttyUSB0, COM1)")
    options = parser.parse_args()

    # Connect to the device.
    transport = serial.Serial(port=options.port, baudrate=options.baud)

    # Listen for incoming data and parse FusionEngine messages.
    try:
        decoder = FusionEngineDecoder()
        while True:
            received_data = transport.read(1024)
            messages = decoder.on_data(received_data)
            for header, message in messages:
                if isinstance(message, MessagePayload):
                    print(str(message))
                else:
                    print(f'{header.message_type} message (not supported)')
    except KeyboardInterrupt:
        pass
    except serial.SerialException as e:
        print('Unexpected error reading from device:\r%s' % str(e))

    # Close the transport when finished.
    transport.close()
