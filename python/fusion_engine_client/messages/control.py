import struct
from typing import Sequence

from construct import (Struct, Int64ul, Int16ul, Int8ul, Padding, this, Bytes, PaddedString)

from .defs import *


class CommandResponseMessage(MessagePayload):
    """!
    @brief Response to indicate if command was processed successfully.
    """
    MESSAGE_TYPE = MessageType.COMMAND_RESPONSE
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<IB3x')

    def __init__(self):
        self.source_sequence_num = 0
        self.response = Response.OK

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        initial_offset = offset

        self._STRUCT.pack_into(buffer, offset, self.source_sequence_num, self.response)
        offset = self._STRUCT.size

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        (self.source_sequence_num, self.response) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset = self._STRUCT.size

        try:
            self.response = Response(self.response)
        except ValueError:
            pass

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', response={self.response}, seq_num={self.source_sequence_num}]'
        return result

    def __str__(self):
        string = f'Command Response\n'
        string += f'  Sequence #: {self.source_sequence_num}\n'
        if isinstance(self.response, Response):
            string += f'  Response: {str(self.response)} ({int(self.response)})'
        else:
            string += f'  Response: UNKNOWN ({int(self.response)})'
        return string


class MessageRequest(MessagePayload):
    """!
    @brief Request transmission of a specified message type.
    """
    MESSAGE_TYPE = MessageType.MESSAGE_REQUEST
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<H2x')

    def __init__(self, message_type: MessageType = MessageType.INVALID):
        self.message_type: MessageType = message_type

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        initial_offset = offset

        self._STRUCT.pack_into(buffer, offset, self.message_type.value)
        offset += self._STRUCT.size

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        (message_type,) = self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.message_type = MessageType(message_type)

        return offset - initial_offset

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', message_type={self.message_type}]'
        return result

    def __str__(self):
        return 'Transmission request for message %s.' % MessageType.get_type_string(self.message_type)

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size


class ResetRequest(MessagePayload):
    """!
    @brief Perform a software or hardware reset.
    """
    MESSAGE_TYPE = MessageType.RESET_REQUEST
    MESSAGE_VERSION = 0

    ##
    # @name Runtime State Reset
    # @{
    ## Restart the navigation engine, but do not clear its position estimate.
    RESTART_NAVIGATION_ENGINE = 0x00000001
    ## Delete all GNSS corrections information.
    RESET_GNSS_CORRECTIONS = 0x00000002
    ## Delete all GNSS time information. */
    RESET_GNSS_TIME = 0x00000004
    ## @}

    ##
    # @name Clear Short Lived Data
    # @{
    ## Reset the navigation engine's estimate of position, velocity, and orientation.
    RESET_POSITION_DATA = 0x00000100
    ## Delete all saved satellite ephemeris.
    RESET_EPHEMERIS = 0x00000200
    ## Reset bias estimates, and other IMU corrections that are typically estimated quickly.
    RESET_FAST_IMU_CORRECTIONS = 0x00000400
    ## @}

    ##
    # @name Clear Long Lived Data
    # @{
    ##
    # Reset all stored navigation engine data, including position, velocity, and orientation state (same as @ref
    # RESET_POSITION_DATA), plus all IMU corrections and other training data.
    RESET_NAVIGATION_ENGINE_DATA = 0x00001000

    ##
    # Reset the device calibration data.
    #
    # @note
    # This does _not_ reset any existing navigation engine state. It is recommended that you set @ref
    # RESET_NAVIGATION_ENGINE_DATA as well under normal circumstances.
    RESET_CALIBRATION_DATA = 0x00002000
    ## @}

    ##
    # @name Clear Configuration Data
    # @{
    ## Clear all configuration data.
    RESET_CONFIG = 0x00100000
    ## @}

    ##
    # @name Software Reboot And Special Reset Modes
    # @{
    ##
    # Reboot the GNSS measurement engine (GNSS receiver), in addition to
    # performing any other requested resets (e.g., @ref RESET_EPHEMERIS). If no
    # other resets are specified, the GNSS receiver will reboot and should
    # perform a hot start.
    REBOOT_GNSS_MEASUREMENT_ENGINE = 0x01000000
    ## Reboot the navigation processor.
    REBOOT_NAVIGATION_PROCESSOR = 0x02000000
    ##
    # Perform a diagnostic log reset to guarantee deterministic performance for
    # data post-processing and diagnostic support.
    #
    # Diagnostic log resets are useful when capturing data to be sent to Point
    # One for analysis and support. Performing a diagnostic reset guarantees that
    # the performance of the device seen in real time can be reproduced during
    # post-processing.
    #
    # This reset performs the following:
    # - Restart the navigation engine (@ref RESTART_NAVIGATION_ENGINE)
    # - Clear any stored data in RAM that was received since startup such as
    #   ephemeris or GNSS corrections
    #   - This is _not_ the same as @ref RESET_EPHEMERIS; this action does not
    #     reset ephemeris data stored in persistent storage
    # - Flush internal data buffers on the device
    #
    # Note that this does _not_ reset the navigation engine's position data,
    # training parameters, or calibration. If the navigation engine has existing
    # position information, it will be used.
    #
    # This reset may be combined with other resets as needed to clear additional
    # information.
    DIAGNOSTIC_LOG_RESET = 0x04000000
    ## @}

    ##
    # @name Device Reset Bitmasks
    # @{

    ##
    # Perform a device hot start.
    #
    # This will reset the navigation engine into a known state, using previously
    # stored position and time information. The device will begin navigating
    # immediately if possible.
    #
    # To be reset:
    # - The navigation engine (@ref RESTART_NAVIGATION_ENGINE)
    #
    # Not reset/performed:
    # - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
    # - GNSS times (@ref RESET_GNSS_TIME)
    # - Position, velocity, orientation (@ref RESET_POSITION_DATA)
    # - GNSS ephemeris data (@ref RESET_EPHEMERIS)
    # - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
    # - Training parameters (slowly estimated IMU corrections, temperature
    #   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
    # - Calibration data (@ref RESET_CALIBRATION_DATA)
    # - User configuration settings (@ref RESET_CONFIG)
    # - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
    # - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
    HOT_START = 0x00000001

    ##
    # Perform a device warm start.
    #
    # During a warm start, the device retains its knowledge of approximate
    # position and time, plus almanac data if available, but resets all ephemeris
    # data. As a result, the device will need to download ephemeris data before
    # continuing to navigate with GNSS.
    #
    # To be reset:
    # - The navigation engine (i.e., perform a hot start, @ref
    #   RESTART_NAVIGATION_ENGINE)
    # - GNSS ephemeris data (@ref RESET_EPHEMERIS)
    #
    # Not reset/performed:
    # - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
    # - GNSS times (@ref RESET_GNSS_TIME)
    # - Position, velocity, orientation (@ref RESET_POSITION_DATA)
    # - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
    # - Training parameters (slowly estimated IMU corrections, temperature
    #   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
    # - Calibration data (@ref RESET_CALIBRATION_DATA)
    # - User configuration settings (@ref RESET_CONFIG)
    # - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
    # - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
    WARM_START = 0x00000201

    ##
    # Perform a pose reset: reset all position, velocity, and orientation
    # information (i.e., the navigation engine's kinematic state).
    #
    # A pose reset is typically used to reset the kinematic portion of the
    # navigation engine's state if you are experiencing errors on startup or
    # after a @ref HOT_START.
    #
    # To be reset:
    # - The navigation engine (@ref RESTART_NAVIGATION_ENGINE)
    # - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
    # - Position, velocity, orientation (@ref RESET_POSITION_DATA)
    #
    # Not reset/performed:
    # - GNSS times (@ref RESET_GNSS_TIME)
    # - GNSS ephemeris data (@ref RESET_EPHEMERIS)
    # - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
    # - Training parameters (slowly estimated IMU corrections, temperature
    #   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
    # - Calibration data (@ref RESET_CALIBRATION_DATA)
    # - User configuration settings (@ref RESET_CONFIG)
    # - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
    # - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
    POSE_RESET = 0x000001FB

    ##
    # Perform a device cold start.
    #
    # A cold start is typically used to reset the device's state estimate in the
    # case of error that cannot be resolved by a @ref WARM_START.
    #
    # To be reset:
    # - The navigation engine (@ref RESTART_NAVIGATION_ENGINE)
    # - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
    # - GNSS times (@ref RESET_GNSS_TIME)
    # - Position, velocity, orientation (@ref RESET_POSITION_DATA)
    # - GNSS ephemeris data (@ref RESET_EPHEMERIS)
    # - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
    #
    # Not reset/performed:
    # - Training parameters (slowly estimated IMU corrections, temperature
    #   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
    # - Calibration data (@ref RESET_CALIBRATION_DATA)
    # - User configuration settings (@ref RESET_CONFIG)
    # - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
    # - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
    #
    # @note
    # To reset training or calibration data as well, set the @ref
    # RESET_NAVIGATION_ENGINE_DATA and @ref RESET_CALIBRATION_DATA bits.
    COLD_START = 0x00000FFF

    ##
    # Restart mask to set all persistent data, including calibration and user configuration, back to factory defaults.
    FACTORY_RESET = 0xFFFFFFFF

    ## @}

    _STRUCT = struct.Struct('<I')

    def __init__(self, reset_mask: int = 0):
        self.reset_mask = reset_mask

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        self._STRUCT.pack_into(buffer, offset, self.reset_mask)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        (self.reset_mask,) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size

    def __repr__(self):
        result = super().__repr__()[:-1]
        mask_text = f'0x{self.reset_mask:08X}'
        name = self._get_known_mask_name(self.reset_mask)
        if name is not None:
            mask_text += f' ({name})'
        result += f', mask={mask_text}]'
        return result

    def __str__(self):
        mask_text = f'0x{self.reset_mask:08X}'
        name = self._get_known_mask_name(self.reset_mask)
        if name is not None:
            mask_text += f' ({name})'
        return f'Reset Request [mask={mask_text}]'

    @classmethod
    def _get_known_mask_name(cls, mask) -> str:
        if mask == cls.HOT_START:
            return 'HOT_START'
        elif mask == cls.WARM_START:
            return 'WARM_START'
        elif mask == cls.POSE_RESET:
            return 'POSE_RESET'
        elif mask == cls.COLD_START:
            return 'COLD_START'
        elif mask == cls.FACTORY_RESET:
            return 'FACTORY_RESET'
        elif mask & cls.DIAGNOSTIC_LOG_RESET:
            return 'DIAGNOSTIC_LOG_RESET'
        else:
            return None


class ShutdownRequest(MessagePayload):
    """!
    @brief Perform a device shutdown.
    """
    MESSAGE_TYPE = MessageType.SHUTDOWN_REQUEST
    MESSAGE_VERSION = 0

    ## Stop navigation engine and flush state to non-volatile storage.
    STOP_ENGINE = 0x0000000000000001
    ## If a log is being generated, end that log.
    STOP_CURRENT_LOG = 0x0000000000000002

    ShutdownRequestConstruct = Struct(
        "shutdown_flags" / Int64ul,
        Padding(8),
    )

    def __init__(self, shutdown_flags = 0):
        self.shutdown_flags = shutdown_flags

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = vars(self)
        packed_data = self.ShutdownRequestConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.ShutdownRequestConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', flags=0x{self.shutdown_flags:016X}]'
        return result

    def __str__(self):
        return 'Shutdown Request [flags=0x%016x]' % self.shutdown_flags

    def calcsize(self) -> int:
        return self.ShutdownRequestConstruct.sizeof()


class StartupRequest(MessagePayload):
    """!
    @brief Perform a device startup.
    """
    MESSAGE_TYPE = MessageType.STARTUP_REQUEST
    MESSAGE_VERSION = 0

    ## Start navigation engine if not running.
    START_ENGINE = 0x0000000000000001
    ## If a log is not being generated, start a new log. If a log is active, end it, and immediately start a new log.
    START_NEW_LOG = 0x0000000000000002

    StartupRequestConstruct = Struct(
        "startup_flags" / Int64ul,
        Padding(8),
    )

    def __init__(self, startup_flags = 0):
        self.startup_flags = startup_flags

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = vars(self)
        packed_data = self.StartupRequestConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.StartupRequestConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', flags=0x{self.startup_flags:016X}]'
        return result

    def __str__(self):
        return 'Startup Request [flags=0x%016x]' % self.startup_flags

    def calcsize(self) -> int:
        return self.StartupRequestConstruct.sizeof()
