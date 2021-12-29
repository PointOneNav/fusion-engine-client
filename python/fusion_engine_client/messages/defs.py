from datetime import datetime, timedelta, timezone
from enum import IntEnum
import logging
import math
import struct
from zlib import crc32

import numpy as np

_logger = logging.getLogger('point_one.fusion_engine.messages.defs')


class SatelliteType(IntEnum):
    UNKNOWN = 1
    GPS = 1
    GLONASS = 2
    LEO = 3
    GALILEO = 4
    BEIDOU = 5
    QZSS = 6
    MIXED = 7
    SBAS = 8
    IRNSS = 9


class SolutionType(IntEnum):
    # Invalid, no position available.
    Invalid = 0
    # Standalone GNSS fix, no correction data used.
    AutonomousGPS = 1
    # Differential GNSS pseudorange solution using a local RTK base station or SSR or SBAS corrections.
    DGPS = 2
    # GNSS RTK solution with fixed integer carrier phase ambiguities (one or more signals fixed).
    RTKFixed = 4
    # GNSS RTK solution with floating point carrier phase ambiguities.
    RTKFloat = 5
    # Integrated position using dead reckoning.
    Integrate = 6
    # Using vision measurements.
    Visual = 9
    # GNSS precise point positioning (PPP) pseudorange/carrier phase solution.
    PPP = 10


class Response(IntEnum):
    ## Command succeeded.
    OK = 0
    ## A version specified in the command or subcommand could not be handled. This could mean that the version was
    ## too new and not supported by the device, or it was older than the version used by the device and there was no
    ## translation for it.
    UNSUPPORTED_CMD_VERSION = 1
    ## The command interacts with a feature that is not present on the target device (e.g., setting the baud rate on
    ## a device without a serial port).
    UNSUPPORTED_FEATURE = 2
    ## One or more values in the command were not in acceptable ranges (e.g., an undefined enum value, or an invalid
    ## baud rate).
    VALUE_ERROR = 3
    ## The command would require adding too many elements to internal storage.
    INSUFFICIENT_SPACE = 4
    ## There was a runtime failure executing the command.
    EXECUTION_FAILURE = 5
    ## The header `payload_size_bytes` is in conflict with the size of the message based on its type or type
    ## specific length fields.
    INCONSISTENT_PAYLOAD_LENGTH = 6,
    ## Requested data was corrupted and not available.
    DATA_CORRUPTED = 7,


class MessageType(IntEnum):
    INVALID = 0

    # Navigation solution messages.
    POSE = 10000
    GNSS_INFO = 10001
    GNSS_SATELLITE = 10002
    POSE_AUX = 10003

    # Sensor measurement messages.
    IMU_MEASUREMENT = 11000

    # ROS messages.
    ROS_POSE = 12000
    ROS_GPS_FIX = 12010
    ROS_IMU = 12011

    # Command and control messages.
    COMMAND_RESPONSE = 13000
    MESSAGE_REQUEST = 13001
    RESET_REQUEST = 13002
    VERSION_INFO = 13003
    EVENT_NOTIFICATION = 13004

    SET_CONFIG = 13100
    GET_CONFIG = 13101
    SAVE_CONFIG = 13102
    CONFIG_DATA = 13103

    SET_OUTPUT_INFERFACE_STREAMS = 13200
    GET_OUTPUT_INFERFACE_STREAMS = 13201
    OUTPUT_INFERFACE_STREAMS_DATA = 13202

    RESERVED = 20000

    @classmethod
    def get_type_string(cls, type):
        try:
            if isinstance(type, str):
                # Convert a string name to a message type (e.g., 'POSE' -> MessageType.POSE).
                type = MessageType[type.upper()]
            else:
                # Convert an int to a MessageType. If `type` is already a MessageType, it'll pass through.
                type = MessageType(type)

            return '%s (%d)' % (type.name, type.value)
        except (KeyError, ValueError):
            try:
                if int(type) >= MessageType.RESERVED:
                    return 'RESERVED (%s)' % str(type)
            except BaseException:
                pass

            return 'UNKNOWN (%s)' % str(type)


class Timestamp:
    _INVALID = 0xFFFFFFFF

    _FORMAT = '<II'
    _SIZE: int = struct.calcsize(_FORMAT)

    _GPS_EPOCH = datetime(1980, 1, 6, tzinfo=timezone.utc)

    def __init__(self, time_sec=math.nan):
        self.seconds = float(time_sec)

    def as_gps(self) -> datetime:
        if math.isnan(self.seconds):
            return None
        else:
            return Timestamp._GPS_EPOCH + timedelta(seconds=self.seconds)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = False) -> (bytes, int):
        if math.isnan(self.seconds):
            int_part = Timestamp._INVALID
            frac_part_ns = Timestamp._INVALID
        else:
            int_part = int(self.seconds)
            frac_part_ns = int((self.seconds - int_part) * 1e9)

        if buffer is None:
            buffer = struct.pack(Timestamp._FORMAT, int_part, frac_part_ns)
        else:
            args = (int_part, frac_part_ns)
            struct.pack_into(Timestamp._FORMAT, buffer, offset, *args)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        (int_part, frac_part_ns) = struct.unpack_from(Timestamp._FORMAT, buffer, offset)
        if int_part == Timestamp._INVALID or frac_part_ns == Timestamp._INVALID:
            self.seconds = math.nan
        else:
            self.seconds = int_part + (frac_part_ns * 1e-9)
        return Timestamp._SIZE

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp._SIZE

    def __eq__(self, other):
        return self.seconds == other.seconds

    def __ne__(self, other):
        return self.seconds != other.seconds

    def __lt__(self, other):
        return self.seconds < other.seconds

    def __le__(self, other):
        return self.seconds <= other.seconds

    def __gt__(self, other):
        return self.seconds > other.seconds

    def __ge__(self, other):
        return self.seconds >= other.seconds

    def __bool__(self):
        return not math.isnan(self.seconds)

    def __float__(self):
        return self.seconds

    def __str__(self):
        return '%.3f seconds' % self.seconds


class MessageHeader:
    INVALID_SOURCE_ID = 0xFFFFFFFF

    _SYNC0 = 0x2E  # '.'
    _SYNC1 = 0x31  # '1'

    _FORMAT = '<BB2xIBBHIII'
    _SIZE: int = struct.calcsize(_FORMAT)

    _MAX_EXPECTED_SIZE_BYTES = (1 << 24)

    def __init__(self, message_type: MessageType = MessageType.INVALID):
        self.crc: int = 0
        self.protocol_version: int = 2
        self.sequence_number: int = 0
        self.message_version: int = 0
        self.message_type: MessageType = message_type
        self.payload_size_bytes: int = 0
        self.source_identifier: int = MessageHeader.INVALID_SOURCE_ID

    def get_type_string(self):
        return MessageType.get_type_string(self.message_type)

    def calculate_crc(self, payload: bytes):
        """!
        @brief Calculate the CRC for this header and the specified payload.

        @post
        @ref crc and @ref payload_size_bytes will be populated automatically on return.

        @return The computed CRC.
        """
        # Set the payload length and then pack the header so we can compute the CRC on the header fields starting with
        # protocol_version, then add the payload into the CRC.
        self.payload_size_bytes = len(payload)
        header_buffer = self.pack()
        self.crc = crc32(header_buffer[8:])
        self.crc = crc32(payload, self.crc)
        return self.crc

    def validate_crc(self, buffer: bytes, offset: int = 0):
        # Sanity check the message payload length before calculating the CRC.
        if self.payload_size_bytes > MessageHeader._MAX_EXPECTED_SIZE_BYTES:
            raise ValueError('Payload length failed sanity check. [%d bytes > %d bytes]' %
                             (self.payload_size_bytes, MessageHeader._MAX_EXPECTED_SIZE_BYTES))

        message_size_bytes = MessageHeader._SIZE + self.payload_size_bytes
        crc = crc32(buffer[(offset + 8):(offset + message_size_bytes)])
        if crc != self.crc:
            raise ValueError('CRC mismatch. [expected=0x%08x, computed=0x%08x]' % (self.crc, crc))

    def pack(self, buffer: bytes = None, offset: int = 0, payload: bytes = None, return_buffer: bool = True) ->\
            (bytes, int):
        """!
        @brief Serialize this header, or a complete header + payload, into a byte buffer.

        @post
        If `payload is not None`, @ref payload_size_bytes will be set automatically and @ref crc will be populated with
        the computed CRC.

        @param buffer If specified, serialize into the provided buffer. Otherwise, create a new buffer.
        @param offset The offset into the buffer (in bytes) at which the message header will be written. Ignored if
               `buffer is None`.
        @param payload If specified, include the provided message payload in the serialized result.
        @param return_buffer If `True`, return the `bytes` buffer object. Otherwise, return the size of the serialized
               content (in bytes).

        @return A `bytes` object containing the serialized message, or the size of the serialized content (in bytes).
        """
        # If the payload is specified, set the CRC and payload length, and then append the payload to the returned
        # result.
        if payload is not None:
            self.calculate_crc(payload)

        args = (MessageHeader._SYNC0, MessageHeader._SYNC1, self.crc, self.protocol_version, self.message_version,
                int(self.message_type), self.sequence_number, self.payload_size_bytes, self.source_identifier)
        if buffer is None:
            buffer = struct.pack(MessageHeader._FORMAT, *args)
            if payload is not None:
                buffer += payload
        else:
            struct.pack_into(MessageHeader._FORMAT, buffer, offset, *args)
            if payload is not None:
                offset += MessageHeader._SIZE
                buffer[offset:offset + len(payload)] = payload

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0, validate_crc: bool = False,
               warn_on_unrecognized: bool = True) -> int:
        """!
        @brief Deserialize a message header and validate its sync bytes and CRC.

        @note
        If CRC validation is enabled, the complete message payload is assumed to follow the header in `buffer`.

        @param buffer A byte buffer containing a serialized message.
        @param offset The offset into the buffer (in bytes) at which the message header begins.
        @param validate_crc If `True`, validate the deserialized CRC against the data in the buffer.

        @return The size of the serialized header (in bytes).
        """
        (sync0, sync1,
         self.crc, self.protocol_version,
         self.message_version, message_type_int,
         self.sequence_number, self.payload_size_bytes, self.source_identifier) = \
            struct.unpack_from(MessageHeader._FORMAT, buffer, offset)

        if sync0 != MessageHeader._SYNC0 or sync1 != MessageHeader._SYNC1:
            raise ValueError('Received invalid sync bytes. [sync0=0x%02x, sync1=0x%02x]' % (sync0, sync1))

        # Validate the CRC, assuming the message payload follows in the buffer.
        if validate_crc:
            self.validate_crc(buffer, offset)

        try:
            self.message_type = MessageType(message_type_int)
        except ValueError:
            if warn_on_unrecognized:
                _logger.log(logging.WARNING if message_type_int < int(MessageType.RESERVED) else logging.DEBUG,
                            'Unrecognized message type %d.' % message_type_int)
            self.message_type = message_type_int

        return MessageHeader._SIZE

    def get_message_size(self) -> int:
        """!
        @brief Calculate the total message size (header + payload).

        @return The message size (in bytes).
        """
        return MessageHeader._SIZE + self.payload_size_bytes

    @classmethod
    def calcsize(cls) -> int:
        """!
        @brief Calculate the size of the header.

        @return The size of the header (in bytes).
        """
        return MessageHeader._SIZE

    @classmethod
    def unpack_values(cls, format, buffer, offset=0, *args):
        values = struct.unpack_from(format, buffer, offset)

        args = list(args)
        value_idx = 0
        for arg_idx in range(len(args)):
            arg = args[arg_idx]
            if isinstance(arg, np.ndarray):
                for i in range(arg.size):
                    arg.flat[i] = values[value_idx]
                    value_idx += 1
            else:
                args[arg_idx] = values[value_idx]
                value_idx += 1

        return tuple(args)


class MessagePayload:
    """!
    @brief Message payload API.
    """

    def __init__(self):
        pass

    @classmethod
    def get_type(cls) -> MessageType:
        return cls.MESSAGE_TYPE

    @classmethod
    def get_version(cls) -> int:
        return cls.MESSAGE_VERSION

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        raise NotImplementedError('pack() not implemented.')

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        raise NotImplementedError('unpack() not implemented.')

    def __repr__(self):
        try:
            return '%s message' % MessageType.get_type_string(self.get_type())
        except NotImplementedError:
            return 'Unknown message payload.'

    def __str__(self):
        return repr(self)


def PackedDataToBuffer(packed_data: bytes, buffer: bytes = None, offset: int = 0,
                       return_buffer: bool = True) -> (bytes, int):
    if buffer is None:
        buffer = packed_data
    else:
        buffer[offset:(offset + len(packed_data))] = packed_data

    if return_buffer:
        return buffer
    else:
        return len(packed_data)
