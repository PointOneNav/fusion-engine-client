from typing import Dict, Tuple, Union

import io
import logging

from ..messages.core import *


class MessageData(object):
    def __init__(self, time_range):
        self.time_range = time_range
        self.messages = []


class FileReader(object):
    logger = logging.getLogger('point_one.fusion_engine.analysis.file_reader')

    def __init__(self, path=None):
        """!
        @brief Create a new reader instance.

        @param path The path to a FusionEngine binary file to open.
        """
        self.file = None
        self.data: Dict[MessageType, MessageData] = {}

        if path is not None:
            self.open(path)

    def open(self, path):
        """!
        @brief Open a FusionEngine binary file.

        @param path The path to the file, or an existing Python file object.
        """
        self.close()

        if isinstance(path, io.IOBase):
            self.file = path
        else:
            self.file = open(path, 'rb')

    def close(self):
        """!
        @brief Close the file.
        """
        if self.file is not None:
            self.file = None

    def read(self, message_types, time_range: Tuple[Union[float, Timestamp], Union[float, Timestamp]] = None,
             absolute_time: bool = False) -> Dict[MessageType, MessageData]:
        """!
        @brief Read data for one or more desired message types.

        The read data will be cached internally. Subsequent reads for the same data type will return the cached data.

        @param message_types A list of one or more @ref fusion_engine_client.messages.defs.MessageType "MessageTypes" to
               be returned.
        @param time_range An optional length-2 tuple specifying desired start and end bounds on the data timestamps.
               Both the start and end values may be set to `None` to read all data.
        @param absolute_time If `True`, interpret the timestamps in `time_range` as absolute P1 times. Otherwise, treat
               them as relative to the first message in the file.

        @return A dictionary, keyed by @ref fusion_engine_client.messages.defs.MessageType "MessageType", containing
               @ref MessageData objects with the data read for each of the requested message types.
        """
        if not isinstance(message_types, (list, tuple)):
            message_types = (message_types,)

        if time_range is None:
            time_range = (None, None)

        # Allow the user to pass in a list of message classes for convenience and convert them to message types
        # automatically.
        message_types = [(t if isinstance(t, MessageType) else t.MESSAGE_TYPE) for t in message_types]

        # If any of the requested types were already read from the file for the requested time range, skip them.
        needed_message_types = [t for t in message_types
                                if (t not in self.data or self.data[t].time_range != time_range)]
        needed_message_types = set(needed_message_types)

        # Make cache entries for the messages to be read.
        for type in needed_message_types:
            self.data[type] = MessageData(time_range)

        # Create a dict with references to the requested types only to be returned below.
        result = {t: self.data[t] for t in message_types}

        num_needed = len(needed_message_types)
        if num_needed == 0:
            # Nothing to read. Return cached data.
            return result
        elif self.file is None:
            raise IOError("File not open.")

        # Seek to the start of the file, then read all messages.
        num_total = len(message_types)
        self.logger.debug('Reading data for %d message types. [cached=%d, start=%s, end=%s]' %
                          (num_total, num_total - num_needed, str(time_range[0]), str(time_range[1])))

        HEADER_SIZE = MessageHeader.calcsize()
        self.file.seek(0, 0)

        total_bytes_read = 0
        bytes_used = 0
        start_time_sec = 0.0 if absolute_time else None
        while True:
            # Read the next message header.
            start_offset = self.file.tell()
            buffer = self.file.read(HEADER_SIZE)
            if len(buffer) == 0:
                break

            # Deserialize the header.
            try:
                header = MessageHeader()
                header.unpack(buffer=buffer)
                message_size_bytes = HEADER_SIZE + header.payload_size_bytes

                # Check if this is one of the message types we need. If not, continue to read the payload and then skip
                # the message below.
                try:
                    message_needed = header.message_type.value in needed_message_types
                except AttributeError:
                    # If the message type was not recognized, header.message_type will be an int instead of MessageType
                    # enum. If it's not in MessageType, there's definitely no message class for it so skip it.
                    message_needed = False

                self.logger.debug('  Deserializing %s message @ %d. [length=%d B]%s' %
                                  (header.get_type_string(), start_offset, message_size_bytes,
                                   '' if message_needed else ' [skip]'))
            except Exception as e:
                self.logger.error('Error decoding header @ %d: %s' % (start_offset, repr(e)))
                break

            # Read the message payload and append it to the header.
            try:
                buffer += self.file.read(header.payload_size_bytes)
            except Exception as e:
                self.logger.error('Error reading %s payload @ %d: %s' %
                                  (header.get_type_string(), start_offset, repr(e)))
                break

            if len(buffer) != message_size_bytes:
                self.logger.warning('Unexpected EOF.')
                break

            # Validate the CRC.
            try:
                header.validate_crc(buffer)
            except ValueError as e:
                self.logger.error('Error reading %s message @ %d: %s' %
                                  (header.get_type_string(), start_offset, repr(e)))
                break

            total_bytes_read += message_size_bytes

            # If this isn't one of the requested messages, skip it.
            if not message_needed:
                continue

            # Now decode the payload.
            try:
                # Get the message class for this type and unpack the payload.
                cls = message_type_to_class.get(header.message_type, None)
                if cls is None:
                    self.logger.warning('Unrecognized message type %s @ %d. Skipping.' %
                                        (header.get_type_string(), start_offset))
                    continue

                contents = cls()
                contents.unpack(buffer=buffer, offset=HEADER_SIZE)

                # If this message has P1 time, test it against the specified range. If not, if a time range was
                # specified, skip this message since we can't be sure it's in the correct range.
                p1_time = contents.__dict__.get('p1_time', None)
                if p1_time is None:
                    if time_range[0] is not None or time_range[1] is not None:
                        continue
                else:
                    if start_time_sec is None:
                        self.logger.debug('Received first message. [time=%s]' % str(p1_time))
                        start_time_sec = float(p1_time)

                    time_offset_sec = float(p1_time) - start_time_sec
                    if time_range[0] is not None and time_offset_sec < float(time_range[0]):
                        self.logger.debug('Message before requested time range. Discarding. [time=%s]' % str(p1_time))
                        continue
                    elif time_range[1] is not None and time_offset_sec > float(time_range[1]):
                        # Assuming data is in order so if we pass the end of the time range we're done.
                        self.logger.debug('Message past requested time range. Done reading. [time=%s]' % str(p1_time))
                        break

                # Store the message.
                self.data[header.message_type].messages.append(contents)
                bytes_used += message_size_bytes
            except Exception as e:
                # Since the CRC passed we know we read the correct number of bytes, so if the decode fails because of
                # a format version mismatch or something, we can simply skip this message. No need to stop reading the
                # file.
                self.logger.warning('Error decoding %s payload @ %d: %s' %
                                    (header.get_type_string(), start_offset, repr(e)))

        self.logger.debug('Read %d bytes, used %d bytes.' % (total_bytes_read, bytes_used))

        # Done.
        return result
