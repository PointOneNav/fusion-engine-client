from typing import Dict, Tuple, Union

from datetime import datetime
import io
import logging

import numpy as np

from ..messages.core import *


class MessageData(object):
    def __init__(self, message_type, time_range):
        self.message_type = message_type
        self.message_class = message_type_to_class[self.message_type]
        self.time_range = time_range
        self.messages = []

    def to_numpy(self):
        """!
        @brief Convert the raw FusionEngine message data into numpy arrays that can be used for data analysis.

        On return, this function will add additional member variables to the class containing numpy arrays as returned
        by the `to_numpy()` function in the individual message data class (if supported).

        For example, if called on a @ref fusion_engine_client.messages.solution.PoseMessage "PoseMessage", this function
        will generate new members including `lla_deg`, a 3xN numpy array with the WGS-84 latitude, longitude, and
        altitude data for all available time epochs that can be used as follows:

        ```{.py}
        pose_data.to_numpy()
        mean_lla_deg = np.mean(pose_data.lla_deg, axis=1)
        ```
        """
        if hasattr(self.message_class, 'to_numpy'):
            have_numpy_data = 'p1_time' in self.__dict__
            if have_numpy_data:
                # If we don't have message data we can't do any conversion so the currently cached numpy data is as good
                # as it's gonna get. If it doesn't exist, so be it.
                if len(self.messages) == 0:
                    do_conversion = False
                else:
                    do_conversion = (len(self.messages) != len(self.p1_time) or
                                     float(self.messages[0].p1_time) != self.p1_time[0] or
                                     float(self.messages[-1].p1_time) != self.p1_time[-1])
            else:
                if len(self.messages) == 0:
                    raise ValueError('Raw %s data not available. Cannot convert to numpy.' %
                                     MessageType.get_type_string(self.message_type))
                else:
                    do_conversion = True

            if do_conversion:
                self.__dict__.update(self.message_class.to_numpy(self.messages))
        else:
            raise ValueError('Message type %s does not support numpy conversion.' %
                             MessageType.get_type_string(self.message_type))


class FileReader(object):
    logger = logging.getLogger('point_one.fusion_engine.analysis.file_reader')

    def __init__(self, path=None):
        """!
        @brief Create a new reader instance.

        @param path The path to a FusionEngine binary file to open.
        """
        self.file = None
        self.file_size = 0
        self.data: Dict[MessageType, MessageData] = {}
        self.t0 = None

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

        self.file.seek(0, io.SEEK_END)
        self.file_size = self.file.tell()
        self.file.seek(0, 0)

    def close(self):
        """!
        @brief Close the file.
        """
        if self.file is not None:
            self.file = None

    def read(self, message_types, time_range: Tuple[Union[float, Timestamp], Union[float, Timestamp]] = None,
             absolute_time: bool = False, return_numpy: bool = False, keep_messages: bool = False,
             show_progress: bool = False) \
            -> Dict[MessageType, MessageData]:
        """!
        @brief Read data for one or more desired message types.

        The read data will be cached internally. Subsequent reads for the same data type will return the cached data.

        @param message_types A list of one or more @ref fusion_engine_client.messages.defs.MessageType "MessageTypes" to
               be returned.
        @param time_range An optional length-2 tuple specifying desired start and end bounds on the data timestamps.
               Both the start and end values may be set to `None` to read all data.
        @param absolute_time If `True`, interpret the timestamps in `time_range` as absolute P1 times. Otherwise, treat
               them as relative to the first message in the file.
        @param return_numpy If `True`, convert the results to numpy arrays for analysis.
        @param keep_messages If `return_numpy == True` and `keep_messages == False`, the raw data in the `messages`
               field will be cleared for each @ref MessageData object for which numpy conversion is supported.
        @param show_progress If `True`, print the read progress every 10 MB (useful for large files).

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
            self.data[type] = MessageData(message_type=type, time_range=time_range)

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
        reference_time_sec = 0.0 if absolute_time else self.t0

        last_print_bytes = 0
        start_time = datetime.now()
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

            if total_bytes_read - last_print_bytes > 10e6:
                elapsed_sec = (datetime.now() - start_time).total_seconds()
                self.logger.log(logging.INFO if show_progress else logging.DEBUG,
                                'Processed %d/%d bytes (%.1f%%). [elapsed=%.1f sec, rate=%.1f MB/s]' %
                                (total_bytes_read, self.file_size, 100.0 * float(total_bytes_read) / self.file_size,
                                 elapsed_sec, total_bytes_read / elapsed_sec / 1e6))
                last_print_bytes = total_bytes_read

            # If this isn't one of the requested messages, skip it. If we don't know t0 yet, continue to unpack.
            if not message_needed and self.t0 is not None:
                continue

            # Now decode the payload.
            try:
                # Get the message class for this type and unpack the payload.
                cls = message_type_to_class.get(header.message_type, None)
                if cls is None:
                    self.logger.log(
                        logging.WARNING if int(header.message_type) < int(MessageType.RESERVED) else logging.DEBUG,
                        'Unrecognized message type %s @ %d. Skipping.' % (header.get_type_string(), start_offset))
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
                    if self.t0 is None:
                        self.logger.debug('Received first message. [type=%s, time=%s]' %
                                          (header.get_type_string(), str(p1_time)))
                        self.t0 = p1_time

                        if reference_time_sec is None:
                            reference_time_sec = float(p1_time)

                        # Now skip this message if we don't need it.
                        if not message_needed:
                            continue

                    time_offset_sec = float(p1_time) - reference_time_sec
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

        end_time = datetime.now()
        self.logger.log(logging.INFO if show_progress else logging.DEBUG,
                        'Read %d bytes, used %d bytes. [elapsed=%.1f sec]' %
                        (total_bytes_read, bytes_used, (end_time - start_time).total_seconds()))

        if return_numpy:
            FileReader.to_numpy(result, keep_messages=keep_messages)

        # Done.
        return result

    @classmethod
    def to_numpy(cls, data: dict, keep_messages: bool = True):
        """!
        @brief Convert all (supported) messages in a data dictionary to numpy for analysis.

        See @ref MessageData.to_numpy().

        @param data A data dictionary as returned by @ref read().
        @param keep_messages If `False`, the raw data in the `messages` field will be cleared for each @ref MessageData
               object for which numpy conversion is supported.
        """
        for entry in data.values():
            try:
                entry.to_numpy()
                if not keep_messages:
                    entry.messages = []
            except ValueError:
                pass



