from typing import NamedTuple, Optional

from construct import Struct, Bytes, Flag, Int8ul, Padding, this

from ..utils.construct_utils import NamedTupleAdapter, AutoEnum, construct_message_to_string
from ..utils.enum_utils import IntEnum
from .defs import *


class FaultType(IntEnum):
    CLEAR_ALL = 0
    CRASH = 1
    FATAL_ERROR = 2
    COCOM = 3
    ENABLE_GNSS = 4
    REGION_BLACKOUT = 5
    QUECTEL_TEST = 6


class CoComType(IntEnum):
    NONE = 0
    ACCELERATION = 1
    SPEED = 2
    ALTITUDE = 3


class _FaultPayloadGenerator:
    """!
    @brief Internal class for generating `FaultPayload` children.

    See @ref _ConfigClassGenerator for details.
    """
    class FaultPayload:
        """!
        @brief Abstract base class for accessing configuration types.
        """
        @classmethod
        def GetType(cls) -> FaultType:
            raise ValueError('Accessing `GetType()` of base class')

    def __init__(self):
        # Gets populated with the mappings from ConfigType to constructs.
        self.TYPE_MAP = {}

    def create_payload_class(self, fault_type, construct_class):
        """!
        @brief Decorator for generating ConfigClass children.

        @copydoc _ConfigClassGenerator
        """
        def inner(payload_class):
            # Make the decorated class a child of FaultPayload. Add the GetType method.
            class InnerClass(payload_class, self.FaultPayload):
                @classmethod
                def GetType(cls) -> FaultType:
                    return fault_type
            InnerClass.__name__ = payload_class.__name__

            # Register the construct with the MessageType.
            self.TYPE_MAP[fault_type] = NamedTupleAdapter(InnerClass, construct_class)

            return InnerClass
        return inner

    class Empty(NamedTuple):
        """!
        @brief Dummy specifier for empty config.
        """
        pass

    EmptyConstruct = Struct()

    class Bool(NamedTuple):
        """!
        @brief Bool value specifier.
        """
        value: bool

    BoolConstruct = Struct(
        "value" / Flag,
    )

    class CoComLimit(NamedTuple):
        """!
        @brief COCOM limit specifier.
        """
        value: CoComType

    CoComConstruct = Struct(
        "value" / AutoEnum(Int8ul, CoComType),
    )


_class_gen = _FaultPayloadGenerator()


class FaultControlMessage(MessagePayload):
    """!
    @brief Enable/disable a specified system fault.

    The @ref payload should be set to a `FaultPayload` instance.

    Usage examples:
    ```{.py}
    # Disable GNSS.
    FaultControlMessage(payload=FaultControlMessage.EnableGNSS(false))

    # Simulate a COCOM acceleration limit.
    FaultControlMessage(payload=FaultControlMessage.CoComLimit(CoComLimit.ACCELERATION))

    # Simulate a fatal error.
    FaultControlMessage(payload=FaultControlMessage.FatalError())
    ```
    """
    MESSAGE_TYPE = MessageType.FAULT_CONTROL
    MESSAGE_VERSION = 0

    @_class_gen.create_payload_class(FaultType.CLEAR_ALL, _class_gen.EmptyConstruct)
    class ClearAll(_class_gen.Empty):
        """!
        @brief Clear existing faults.
        """
        pass

    @_class_gen.create_payload_class(FaultType.CRASH, _class_gen.EmptyConstruct)
    class Crash(_class_gen.Empty):
        """!
        @brief Force the device to crash (intended for factory test purposes only).
        """
        pass

    @_class_gen.create_payload_class(FaultType.FATAL_ERROR, _class_gen.EmptyConstruct)
    class FatalError(_class_gen.Empty):
        """!
        @brief Force the device to exhibit a fatal error (intended for factory test purposes only).
        """
        pass

    @_class_gen.create_payload_class(FaultType.COCOM, _class_gen.CoComConstruct)
    class CoComLimit(_class_gen.CoComLimit):
        """!
        @brief Simulate a COCOM limit.
        """
        pass

    @_class_gen.create_payload_class(FaultType.ENABLE_GNSS, _class_gen.BoolConstruct)
    class EnableGNSS(_class_gen.Bool):
        """!
        @brief Enable/disable use of GNSS measurements (intended for dead reckoning performance testing).
        """
        pass

    @_class_gen.create_payload_class(FaultType.REGION_BLACKOUT, _class_gen.BoolConstruct)
    class RegionBlackout(_class_gen.Bool):
        """!
        @brief Simulate a region blackout (intended for factory test purposes only).
        """
        pass

    @_class_gen.create_payload_class(FaultType.QUECTEL_TEST, _class_gen.BoolConstruct)
    class QuectelTest(_class_gen.Bool):
        """!
        @brief Enable/disable Quectel test features (intended for factory test purposes only).
        """
        pass

    FaultControlMessageConstruct = Struct(
        "fault_type" / AutoEnum(Int8ul, FaultType),
        Padding(15),
        "payload_length_bytes" / Int32ul,
        "payload" / Bytes(this.payload_length_bytes),
    )

    def __init__(self, payload: Optional[_class_gen.FaultPayload] = None):
        self.payload = payload

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if not isinstance(self.payload, _class_gen.FaultPayload):
            raise TypeError(f'The payload member ({str(self.payload)}) must be set to a class decorated '
                            'with create_payload_class().')
        fault_type = self.payload.GetType()
        construct_obj = _class_gen.TYPE_MAP[fault_type]
        data = construct_obj.build(self.payload)
        values = {
            'fault_type': fault_type,
            'payload': data,
            'payload_length_bytes': len(data)
        }
        packed_data = self.FaultControlMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.FaultControlMessageConstruct.parse(buffer[offset:])
        self.payload = _class_gen.TYPE_MAP[parsed.fault_type].parse(parsed.payload)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', fault_type={self.payload.GetType() if self.payload is not None else "None"}]'
        return result

    def __str__(self):
        return construct_message_to_string(message=self, title='Fault Control Command')

    def calcsize(self) -> int:
        return len(self.pack())
