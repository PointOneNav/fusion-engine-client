import inspect
import re
import struct
import sys
from typing import Dict, List, Optional, Set, Type, Union
from zlib import crc32

import numpy as np

from .measurement_details import *
from .signal_defs import *
from .timestamp import *
from ..utils import trace as logging
from ..utils.enum_utils import IntEnum

_logger = logging.getLogger('point_one.fusion_engine.messages.defs')

if sys.version_info >= (3, 9):
    def _remove_suffix(s, suffix):
        return s.removesuffix(suffix)
else:
    def _remove_suffix(s, suffix):
        if s.endswith(suffix):
            return s[:-len(suffix)]
        else:
            return s


def _remove_suffixes(s, suffixes):
    result = s
    for suffix in suffixes:
        result = _remove_suffix(result, suffix)
    return result


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
    INCONSISTENT_PAYLOAD_LENGTH = 6
    ## Requested data was corrupted and not available.
    DATA_CORRUPTED = 7
    ## The requested data isn't available.
    NO_DATA_STORED = 8
    ## The device is in a state where it can't process the command.
    UNAVAILABLE = 9


class MessageType(IntEnum):
    INVALID = 0

    # Navigation solution messages.
    POSE = 10000
    GNSS_INFO = 10001
    GNSS_SATELLITE = 10002
    POSE_AUX = 10003
    CALIBRATION_STATUS = 10004
    RELATIVE_ENU_POSITION = 10005

    # Device status messages.
    SYSTEM_STATUS = 10500

    # Sensor measurement messages.
    IMU_OUTPUT = 11000
    RAW_HEADING_OUTPUT = 11001
    RAW_IMU_OUTPUT = 11002
    HEADING_OUTPUT = 11003
    IMU_INPUT = 11004

    # Vehicle measurement messages.
    DEPRECATED_WHEEL_SPEED_MEASUREMENT = 11101
    DEPRECATED_VEHICLE_SPEED_MEASUREMENT = 11102

    WHEEL_TICK_INPUT = 11103
    VEHICLE_TICK_INPUT = 11104
    WHEEL_SPEED_INPUT = 11105
    VEHICLE_SPEED_INPUT = 11106

    RAW_WHEEL_TICK_OUTPUT = 11123
    RAW_VEHICLE_TICK_OUTPUT = 11124
    RAW_WHEEL_SPEED_OUTPUT = 11125
    RAW_VEHICLE_SPEED_OUTPUT = 11126

    WHEEL_SPEED_OUTPUT = 11135
    VEHICLE_SPEED_OUTPUT = 11136

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
    SHUTDOWN_REQUEST = 13005
    FAULT_CONTROL = 13006
    DEVICE_ID = 13007
    STARTUP_REQUEST = 13008

    SET_CONFIG = 13100
    GET_CONFIG = 13101
    SAVE_CONFIG = 13102
    CONFIG_RESPONSE = 13103

    IMPORT_DATA = 13110
    EXPORT_DATA = 13111
    PLATFORM_STORAGE_DATA = 13113

    SET_MESSAGE_RATE = 13220
    GET_MESSAGE_RATE = 13221
    MESSAGE_RATE_RESPONSE = 13222
    SUPPORTED_IO_INTERFACES = 13223

    LBAND_FRAME = 14000

    RESERVED = 20000

    @classmethod
    def get_type_string(cls, value, include_value=True, raise_on_unrecognized=False):
        try:
            return cls(value, raise_on_unrecognized=True).to_string(include_value=include_value)
        except (KeyError, ValueError) as e:
            # For MessageType, if the user specifies an unrecognized value, we return:
            # - RESERVED - Value defined for internal use only
            # - UNKNOWN - Value not recognized
            #
            # We don't use the default IntEnum behavior of returning "<Unrecognized>".
            string_name = None
            try:
                int_value = int(value)
                if value >= MessageType.RESERVED:
                    string_name = 'RESERVED'
            except BaseException:
                # Value was not an integer. Let it pass through and print its str() representation below.
                int_value = value

            if string_name is None:
                if raise_on_unrecognized:
                    raise e
                else:
                    string_name = 'UNKNOWN'

            if include_value:
                return '%s (%s)' % (string_name, str(int_value))
            else:
                return string_name


COMMAND_MESSAGES = {
    MessageType.MESSAGE_REQUEST,
    MessageType.RESET_REQUEST,
    MessageType.SHUTDOWN_REQUEST,
    MessageType.FAULT_CONTROL,
    MessageType.SET_CONFIG,
    MessageType.GET_CONFIG,
    MessageType.SAVE_CONFIG,
    MessageType.IMPORT_DATA,
    MessageType.EXPORT_DATA,
    MessageType.SET_MESSAGE_RATE,
    MessageType.GET_MESSAGE_RATE,
}


def is_command(message_type: MessageType) -> bool:
    return message_type in COMMAND_MESSAGES


RESPONSE_MESSAGES = {
    MessageType.COMMAND_RESPONSE,
    MessageType.CONFIG_RESPONSE,
    MessageType.MESSAGE_RATE_RESPONSE,
}


def is_response(message_type: MessageType) -> bool:
    return message_type in RESPONSE_MESSAGES


class MessageHeader:
    INVALID_SOURCE_ID = 0xFFFFFFFF

    SYNC0 = 0x2E  # '.'
    SYNC1 = 0x31  # '1'

    SYNC = bytes((SYNC0, SYNC1))

    _FORMAT = '<BBHIBBHIII'
    _SIZE: int = struct.calcsize(_FORMAT)

    _MAX_EXPECTED_SIZE_BYTES = (1 << 24)

    def __init__(self, message_type: MessageType = MessageType.INVALID):
        self.reserved: int = 0
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
            raise ValueError('CRC mismatch. [type=%s, payload_size=%d B, expected=0x%08x, computed=0x%08x]' %
                             (self.get_type_string(), self.payload_size_bytes, self.crc, crc))

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
        if self.reserved != 0:
            self.reserved = 0

        # If the payload is specified, set the CRC and payload length, and then append the payload to the returned
        # result.
        if payload is not None:
            self.calculate_crc(payload)

        args = (MessageHeader.SYNC0, MessageHeader.SYNC1, self.reserved, self.crc, self.protocol_version,
                self.message_version, int(self.message_type), self.sequence_number, self.payload_size_bytes,
                self.source_identifier)
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

    def unpack(self, buffer: bytes, offset: int = 0, validate_sync: bool = False, validate_crc: bool = False,
               warn_on_unrecognized: bool = True) -> int:
        """!
        @brief Deserialize a message header and validate its sync bytes and CRC.

        @note
        If CRC validation is enabled, the complete message payload is assumed to follow the header in `buffer`.

        @param buffer A byte buffer containing a serialized message.
        @param offset The offset into the buffer (in bytes) at which the message header begins.
        @param validate_sync If `True`, validate the sync bytes contained in the data buffer.
        @param validate_crc If `True`, validate the deserialized CRC against the data in the buffer.
        @param warn_on_unrecognized If `True`, print a warning if the message type is not listed in @ref MessageType.

        @return The size of the serialized header (in bytes).
        """
        (sync0, sync1, self.reserved,
         self.crc, self.protocol_version,
         self.message_version, message_type_int,
         self.sequence_number, self.payload_size_bytes, self.source_identifier) = \
            struct.unpack_from(MessageHeader._FORMAT, buffer, offset)

        if validate_sync and (sync0 != MessageHeader.SYNC0 or sync1 != MessageHeader.SYNC1):
            raise ValueError('Received invalid sync bytes. [sync0=0x%02x, sync1=0x%02x]' % (sync0, sync1))

        # Validate the CRC, assuming the message payload follows in the buffer.
        if validate_crc:
            self.validate_crc(buffer, offset)

        try:
            self.message_type = MessageType(message_type_int)
        except (ValueError, KeyError):
            if warn_on_unrecognized:
                _logger.log(logging.WARNING if message_type_int < int(MessageType.RESERVED) else logging.DEBUG,
                            'Unrecognized message type %d.' % message_type_int)
            self.message_type = MessageType(message_type_int, raise_on_unrecognized=False)

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

    def __str__(self):
        return f"""\
{self.get_type_string()} Message (version {self.message_version}):
  Sequence #: {self.sequence_number}
  Payload: {self.payload_size_bytes} B
  Source: {self.source_identifier}
  CRC: 0x{self.crc:08x}"""

    def __repr__(self):
        return f"[type={self.get_type_string()}, seq={self.sequence_number}, payload={self.payload_size_bytes} B, " \
               f"crc=0x{self.crc:08x}]"


class MessagePayload:
    """!
    @brief Message payload API.
    """

    _UNSPECIFIED_VERSION = 0x100

    message_type_to_class: Dict[MessageType, Type['MessagePayload']] = {}
    message_type_by_name: Dict[str, MessageType] = {}

    def __init__(self):
        pass

    def __init_subclass__(cls, **kwargs):
        MessagePayload.message_type_to_class[cls.get_type()] = cls
        MessagePayload.message_type_by_name[cls.__name__] = cls.get_type()

    @classmethod
    def get_message_class(cls, message_type: MessageType) -> Type['MessagePayload']:
        return MessagePayload.message_type_to_class.get(message_type, None)

    @classmethod
    def find_matching_message_types(cls, pattern: Union[str, List[str]], return_class: bool = False) -> \
        Union[Set[MessageType], Set['MessagePayload']]:
        """!
        @brief Find one or more @ref MessageType%s that match the specified pattern(s).

        Examples:
        ```py
        find_matching_message_types('pose')  # {MessageType.POSE}
        find_matching_message_types('posemessage')  # {MessageType.POSE}
        find_matching_message_types('PoseMessage')  # {MessageType.POSE}
        find_matching_message_types('pos')  # ValueError - multiple possible matches
        find_matching_message_types('pos*')  # {MessageType.POSE, MessageType.POSE_AUX}
        find_matching_message_types('pose,poseaux')  # {MessageType.POSE, MessageType.POSE_AUX}
        find_matching_message_types(['pose', 'poseaux'])  # {MessageType.POSE, MessageType.POSE_AUX}
        ```

        @param pattern A `list` or a comma-separated string containing one or more search patterns. Patterns may match
               part or all of a class name. Patterns may include wildcards (`*`) to match multiple classes. If no
               wildcards are specified and multiple classes match, a single result will be returned if there is an exact
               match (e.g., `pose` will match to @ref MessageType.POSE, not @ref MessageType.POSE_AUX). All matches are
               case-insensitive.
        @param return_class If `True`, return classes for each matching message type (derived from @ref MessagePayload).
               Otherwise, return @ref MessageType enum values.

        @return A set containing the matching @ref MessageType or @ref MessagePayload instances.
        """
        # Generate a list of requested types.
        requested_types = []

        if isinstance(pattern, str):
            patterns = [pattern]
        else:
            patterns = pattern

        # Split and flatten comma-separated lists of names/patterns:
        #   ['VersionInfoMessage', 'PoseMessage,GNSS*'] ->
        #   ['VersionInfoMessage', 'PoseMessage', 'GNSS*']
        requested_types = [p.strip() for entry in patterns for p in entry.split(',')]

        # Now find matches to each pattern.
        result = set()
        for pattern in requested_types:
            # Check if pattern is the message integer value.
            try:
                int_val = int(pattern)
                result.add(MessageType(int_val))
            except:
                allow_multiple = '*' in pattern
                re_pattern = pattern.replace('*', '.*')
                # if pattern[0] != '^':
                #     re_pattern = r'.*' + re_pattern
                # if pattern[-1] != '$':
                #     re_pattern += '.*'

                # Check for matches.
                matched_types = [v for k, v in cls.message_type_by_name.items()
                                if re.match(re_pattern, k, flags=re.IGNORECASE)]
                if len(matched_types) == 0:
                    _logger.warning("No message types matching pattern '%s'." % pattern)
                    continue

                # Check for exact matches with "Message" and "Measurement" suffixes removed.
                if len(matched_types) > 1 and not allow_multiple:
                    def _remove_message_suffixes(s):
                        return _remove_suffixes(s.lower(), ['message', 'measurement', 'input', 'output'])
                    pattern_no_suffix = _remove_message_suffixes(pattern)
                    exact_matches = [t for t in matched_types
                                    if _remove_message_suffixes(cls.message_type_to_class[t].__name__) ==
                                    pattern_no_suffix]
                    if len(exact_matches) == 1:
                        matched_types = exact_matches

                # If there are still too many matches, fail.
                if len(matched_types) > 1 and not allow_multiple:
                    class_names = [cls.message_type_to_class[t].__name__ for t in matched_types]
                    raise ValueError("Pattern '%s' matches multiple message types:%s\n\nAdd a wildcard (%s*) to display "
                                    "all matching types." %
                                    (pattern, ''.join(['\n  %s' % c for c in class_names]), pattern))
                # Otherwise, update the set of message types.
                else:
                    result.update(matched_types)

        if return_class:
            result = {cls.message_type_to_class[t] for t in result}

        return result

    @classmethod
    def get_type(cls) -> MessageType:
        return cls.MESSAGE_TYPE

    @classmethod
    def get_type_string(cls):
        return MessageType.get_type_string(cls.get_type())

    @classmethod
    def get_version(cls) -> int:
        return cls.MESSAGE_VERSION

    @classmethod
    def is_subclass(cls, obj) -> bool:
        """!
        @brief Check if an object is a _class_, which is derived from @ref MessagePayload.

        This function calls the built-in `issubclass()` operator to check if a specified object is a class derived from
        @ref MessagePayload. Unlike the operator, which raises a `TypeError` if the object is not a class (e.g., if you
        pass in a `None`, or any other object), this function accepts any type for its argument:
        ```py
        issubclass(None, MessagePayload)        # TypeError
        issubclass(float, MessagePayload)       # False
        issubclass(dict, MessagePayload)        # False
        issubclass(PoseMessage, MessagePayload) # True

        MessagePayload.is_subclass(None)        # False
        MessagePayload.is_subclass(float)       # False
        MessagePayload.is_subclass(dict)        # False
        MessagePayload.is_subclass(PoseMessage) # True
        ```

        Note that this function is specifically meant to check classes, not class _instances_. To test if an object is
        an instance of a class derived from @ref MessagePayload, use the `isinstance()` operator instead:
        ```py
        isinstance(None, MessagePayload)          # False
        isinstance(3.6, MessagePayload)           # False
        isinstance(dict(), MessagePayload)        # False
        isinstance(PoseMessage(), MessagePayload) # True
        ```

        @param obj The object to be tested.

        @return `True` if obj is a class type that is derived from @ref MessagePayload.
        """
        return inspect.isclass(obj) and issubclass(obj, MessagePayload)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        raise NotImplementedError('pack() not implemented.')

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = _UNSPECIFIED_VERSION) -> int:
        raise NotImplementedError('unpack() not implemented.')

    def get_p1_time(self) -> Timestamp:
        measurement_details = getattr(self, 'details', None)
        if isinstance(measurement_details, MeasurementDetails):
            if measurement_details.measurement_time_source == SystemTimeSource.P1_TIME:
                return measurement_details.measurement_time
            else:
                return measurement_details.p1_time
        else:
            return getattr(self, 'p1_time', None)

    def get_system_time_ns(self) -> float:
        measurement_details = getattr(self, 'details', None)
        if isinstance(measurement_details, MeasurementDetails):
            if measurement_details.measurement_time_source == SystemTimeSource.TIMESTAMPED_ON_RECEPTION:
                return float(measurement_details.measurement_time) * 1e9
            else:
                return np.nan
        else:
            return getattr(self, 'system_time_ns', None)

    def get_system_time_sec(self) -> float:
        system_time_ns = self.get_system_time_ns()
        if system_time_ns is None:
            return None
        else:
            return system_time_ns * 1e-9

    def __repr__(self):
        result = f'[{self.get_type().to_string(include_value=True)}'

        p1_time = self.get_p1_time()
        if p1_time is not None:
            result += f', p1_time={float(p1_time):.3f} sec'

        system_time_sec = self.get_system_time_sec()
        if system_time_sec is not None:
            result += f', system_time={system_time_sec:.3f} sec'

        result += ']'

        return result

    def __str__(self):
        return repr(self)

    @classmethod
    def pack_values(cls, format: Union[str, struct.Struct], buffer: bytes, offset: int = 0, *args):
        """!
        @brief Serialize data into a byte stream.

        This is a convenience packing function for consistency with @ref unpack_values(). It behaves similarly to a
        direct call to `struct.pack_into()`, however the list of values (`args`) may include NumPy `ndarray` elements,
        which will be flattened automatically.

        @param format A `struct` format string or a `struct.Struct` object describing the data packing.
        @param buffer A byte buffer in which the serialized data will be stored.
        @param offset The start offset (in bytes) within `buffer`.
        @param args The values to be packed.

        @return The size of the serialized data.
        """
        # If the user passed in a numpy array, expand it into its elements:
        #   (1, 2, array([3, 4, 5])) -->
        #   (1, 2, 3, 4, 5)
        if any([isinstance(e, np.ndarray) for e in args]):
            flattened_args = []
            for e in args:
                if isinstance(e, np.ndarray):
                    flattened_args.extend(e.flat)
                else:
                    flattened_args.append(e)
        else:
            flattened_args = args

        if isinstance(format, struct.Struct):
            format.pack_into(buffer, offset, *flattened_args)
            return format.size
        else:
            struct.pack_into(format, buffer, offset, *flattened_args)
            return struct.calcsize(format)

    @classmethod
    def unpack_values(cls, format: Union[str, struct.Struct], buffer: bytes, offset: int = 0, *args):
        """!
        @brief Unpack serialized data.

        This is a helper function, similar to `struct.unpack_from()`, which can be used to unpack class members where
        _all_ members are NumPy `ndarray` elements.

        @warning
        Primitives cannot be passed by reference in Python. If you pass in anything other than a NumPy array in `args`,
        it will _not_ be populated on return.

        For example, the following:
        ```py
        my_array = np.ndarray((3,))
        (my_array[0], my_array[1], my_array[2]) = my_struct.unpack_from(buffer, offset)
        ```

        can be rewritten as:
        ```py
        my_array = np.ndarray((3,))
        self.unpack_values(my_struct, buffer, offset, my_array)
        ```

        This function also has the benefit of being consistent with `struct.pack_into()`, making derived classes'
        `pack()` and `unpack()` functions more symmetrical. For example, the above data can be serialized as follows:
        ```py
        self.pack_values(my_struct, buffer, offset, my_double, my_array)

        # or

        my_struct.pack_into(buffer, offset, my_double, *my_array)
        ```

        @param format A `struct` format string or a `struct.Struct` object describing the data packing.
        @param buffer A byte buffer containing the data to be unpacked.
        @param offset The start offset (in bytes) within `buffer`.
        @param args References to variables to be populated.

        @return The number of bytes consumed.
        """
        if isinstance(format, struct.Struct):
            values = format.unpack_from(buffer, offset)
            size = format.size
        else:
            values = struct.unpack_from(format, buffer, offset)
            size = struct.calcsize(format)

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

        return size


def PackedDataToBuffer(packed_data: bytes, buffer: Optional[bytes] = None, offset: int = 0,
                       return_buffer: bool = True) -> (bytes, int):
    if buffer is None:
        buffer = packed_data
    else:
        buffer[offset:(offset + len(packed_data))] = packed_data

    if return_buffer:
        return buffer
    else:
        return len(packed_data)
