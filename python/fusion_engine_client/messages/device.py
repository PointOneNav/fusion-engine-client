import math

from construct import (Padding, Struct, Float64l, Int64ul, Int32ul, Int16ul, Int16sl, Int8ul)
import numpy as np

from ..utils.construct_utils import AutoEnum, FixedPointAdapter, NumpyAdapter
from .defs import *


class RTKOutputSource(IntEnum):
    NONE = 0
    OSR = 1
    SSR = 2


class SystemStatusMessage(MessagePayload):
    """!
    @brief System status message.
    """
    MESSAGE_TYPE = MessageType.SYSTEM_STATUS
    MESSAGE_VERSION = 0

    Construct = Struct(
        "p1_time" / TimestampConstruct,
        "gnss_temperature_degc" / FixedPointAdapter(2 ** -7, Int16sl, invalid=0x7FFF),
        Padding(118),
    )

    def __init__(self):
        self.p1_time = Timestamp()
        self.gnss_temperature_degc = math.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = vars(self)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']
        return parsed._io.tell()

    @classmethod
    def calcsize(cls) -> int:
        return cls.Construct.sizeof()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', gnss_temperature={self.gnss_temperature_degc:.1f} deg C]'
        return result

    def __str__(self):
        return f"""\
System Status Message @ {self.p1_time}
  GNSS Temperature: {self.gnss_temperature_degc:.1f} deg C"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'gnss_temperature_degc': np.array([m.gnss_temperature_degc for m in messages]),
        }
        return result


class SSRStatusMessage(MessagePayload):
    """!
    @brief State-space representation (SSR) GNSS corrections status.
    """
    MESSAGE_TYPE = MessageType.SSR_STATUS
    MESSAGE_VERSION = 0

    Construct = Struct(
        "p1_time" / TimestampConstruct,
        "system_time_ns" / Int64ul,

        "output_gps_time" / TimestampConstruct,
        "output_source" / AutoEnum(Int8ul, RTKOutputSource),
        Padding(1),
        "output_station_id" / Int16ul,
        "base_lla_deg" / NumpyAdapter(shape=(3,)),

        "num_satellites" / Int8ul,
        "num_signals" / Int8ul,
        "gnss_systems_mask" / Int16ul,
        "gps_signal_types_mask" / Int16ul,
        "glo_signal_types_mask" / Int16ul,
        "gal_signal_types_mask" / Int16ul,
        "bds_signal_types_mask" / Int16ul,
        Padding(8),

        "num_gps_ephemeris" / Int8ul,
        "num_glo_ephemeris" / Int8ul,
        "num_gal_ephemeris" / Int8ul,
        "num_bds_ephemeris" / Int8ul,
        Padding(4),

        "osr_status_mask" / Int16ul,
        Padding(2),

        "ssr_status_mask" / Int16ul,
        Padding(1),
        "ssr_grid_id" / Int8ul,
        "ssr_enabled_component_mask" / Int16ul,
        "ssr_model_status_mask" / Int16ul,
        "ssr_decode_status_mask" / Int16ul,
        Padding(2),

        "ssr_primary_message_count" / Int32ul,
        "ssr_primary_crc_fail_count" / Int32ul,
    )

    def __init__(self):
        self.p1_time = Timestamp()
        self.system_time_ns = 0

        self.output_gps_time = Timestamp()
        self.output_source = RTKOutputSource.NONE
        self.output_station_id = 0
        self.base_lla_deg = np.full((3,), np.nan)

        self.num_satellites = 0
        self.num_signals = 0
        self.gnss_systems_mask = 0x0
        self.gps_signal_types_mask = 0x0
        self.glo_signal_types_mask = 0x0
        self.gal_signal_types_mask = 0x0
        self.bds_signal_types_mask = 0x0

        self.num_gps_ephemeris = 0
        self.num_glo_ephemeris = 0
        self.num_gal_ephemeris = 0
        self.num_bds_ephemeris = 0

        self.osr_status_mask = 0x0

        self.ssr_status_mask = 0x0
        self.ssr_grid_id = 0
        self.ssr_enabled_component_mask = 0x0
        self.ssr_model_status_mask = 0x0
        self.ssr_decode_status_mask = 0x0

        self.ssr_primary_message_count = 0
        self.ssr_primary_crc_fail_count = 0

    def calcsize(self) -> int:
        return self.Construct.sizeof()

    def _construct_str_impl(self, **kwargs):
        to_hex = lambda v: '0x%04X' % v
        kwargs['value_to_string'] = {
            'output_gps_time': lambda t: t.to_gps_str(),
            'gnss_systems_mask': lambda v: f'{to_hex(v)} = {SatelliteTypeMask.to_string(v)}',
            'gps_signal_types_mask': lambda v: f'{to_hex(v)} = {GPSSignalTypeMask.to_string(v)}',
            'glo_signal_types_mask': lambda v: f'{to_hex(v)} = {GLOSignalTypeMask.to_string(v)}',
            'gal_signal_types_mask': lambda v: f'{to_hex(v)} = {GALSignalTypeMask.to_string(v)}',
            'bds_signal_types_mask': lambda v: f'{to_hex(v)} = {BDSSignalTypeMask.to_string(v)}',
            'osr_status_mask': to_hex,
            'ssr_status_mask': to_hex,
            'ssr_enabled_component_mask': to_hex,
            'ssr_model_status_mask': to_hex,
            'ssr_decode_status_mask': to_hex,
        }
        return super()._construct_str_impl(**kwargs)

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', output_gps_time={self.output_gps_time}, source={self.output_source}, ' \
                  f'num_signals={self.num_signals}]'
        return result
