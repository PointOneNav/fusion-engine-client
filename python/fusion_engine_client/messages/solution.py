from dataclasses import dataclass
import struct
from typing import Dict, List, Sequence

from construct import (Struct, Float64l, Float32l, Int32ul, Int8ul, Padding, Array)
import numpy as np

from ..utils.construct_utils import AutoEnum, construct_message_to_string
from ..utils.enum_utils import IntEnum
from .defs import *


class PoseMessage(MessagePayload):
    """!
    @brief Platform pose solution (position, velocity, attitude).
    """
    MESSAGE_TYPE = MessageType.POSE
    MESSAGE_VERSION = 2

    INVALID_UNDULATION = -32768

    FLAG_STATIONARY = 0x1

    _STRUCT = struct.Struct('<BB h ddd fff ddd fff ddd fff fff')

    def __init__(self):
        self.p1_time = Timestamp()
        self.gps_time = Timestamp()

        self.solution_type = SolutionType.Invalid

        # Added in version 1.2
        self.flags = 0x0

        # Added in version 1.1.
        self.undulation_m = np.nan

        self.lla_deg = np.full((3,), np.nan)
        self.position_std_enu_m = np.full((3,), np.nan)

        self.ypr_deg = np.full((3,), np.nan)
        self.ypr_std_deg = np.full((3,), np.nan)

        self.velocity_body_mps = np.full((3,), np.nan)
        self.velocity_std_body_mps = np.full((3,), np.nan)

        self.aggregate_protection_level_m = np.nan
        self.horizontal_protection_level_m = np.nan
        self.vertical_protection_level_m = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)
        offset += self.gps_time.pack(buffer, offset, return_buffer=False)

        if np.isnan(self.undulation_m):
            undulation_cm = PoseMessage.INVALID_UNDULATION
        else:
            undulation_cm = int(np.round(self.undulation_m * 1e2))

        self._STRUCT.pack_into(
            buffer, offset,
            int(self.solution_type),
            self.flags,
            undulation_cm,
            self.lla_deg[0], self.lla_deg[1], self.lla_deg[2],
            self.position_std_enu_m[0], self.position_std_enu_m[1], self.position_std_enu_m[2],
            self.ypr_deg[0], self.ypr_deg[1], self.ypr_deg[2],
            self.ypr_std_deg[0], self.ypr_std_deg[1], self.ypr_std_deg[2],
            self.velocity_body_mps[0], self.velocity_body_mps[1], self.velocity_body_mps[2],
            self.velocity_std_body_mps[0], self.velocity_std_body_mps[1], self.velocity_std_body_mps[2],
            self.aggregate_protection_level_m,
            self.horizontal_protection_level_m,
            self.vertical_protection_level_m)
        offset += self._STRUCT.size

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)
        offset += self.gps_time.unpack(buffer, offset)

        (solution_type_int,
         flags,
         undulation_cm,
         self.lla_deg[0], self.lla_deg[1], self.lla_deg[2],
         self.position_std_enu_m[0], self.position_std_enu_m[1], self.position_std_enu_m[2],
         self.ypr_deg[0], self.ypr_deg[1], self.ypr_deg[2],
         self.ypr_std_deg[0], self.ypr_std_deg[1], self.ypr_std_deg[2],
         self.velocity_body_mps[0], self.velocity_body_mps[1], self.velocity_body_mps[2],
         self.velocity_std_body_mps[0], self.velocity_std_body_mps[1], self.velocity_std_body_mps[2],
         self.aggregate_protection_level_m,
         self.horizontal_protection_level_m,
         self.vertical_protection_level_m) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        if undulation_cm == PoseMessage.INVALID_UNDULATION:
            self.undulation_m = np.nan
        else:
            self.undulation_m = undulation_cm * 1e-2

        self.solution_type = SolutionType(solution_type_int)

        self.flags = flags

        return offset - initial_offset

    def __repr__(self):
        lla_str = '(%.6f, %.6f, %.3f)' % tuple(self.lla_deg)
        if self.gps_time:
            gps_str = f'{str(self.gps_time).replace("GPS: ", "")} ' \
                      f'({datetime_to_string(self.gps_time.as_utc())} UTC)'
        else:
            gps_str = 'None'

        result = super().__repr__()[:-1]
        result += f', gps_time={gps_str}, solution_type={self.solution_type}, position={lla_str}]'
        return result

    def __str__(self):
        string = 'Pose Message @ %s\n' % str(self.p1_time)
        string += '  Solution type: %s\n' % self.solution_type.name
        if self.gps_time:
            gps_str = f'{str(self.gps_time).replace("GPS: ", "")}'
            utc_str = f'{datetime_to_string(self.gps_time.as_utc())}'
        else:
            gps_str = 'None'
            utc_str = 'None'
        string += '  GPS time: %s\n' % gps_str
        string += '  UTC time: %s\n' % utc_str
        string += '  Position (LLA): %.8f, %.8f, %.3f (deg, deg, m)\n' % tuple(self.lla_deg)
        string += '  Attitude (YPR): %.2f, %.2f, %.2f (deg, deg, deg)\n' % tuple(self.ypr_deg)
        string += '  Velocity (Body): %.2f, %.2f, %.2f (m/s, m/s, m/s)\n' % tuple(self.velocity_body_mps)
        string += '  Position std (ENU): %.2f, %.2f, %.2f (m, m, m)\n' % tuple(self.position_std_enu_m)
        string += '  Attitude std (YPR): %.2f, %.2f, %.2f (deg, deg, deg)\n' % tuple(self.ypr_std_deg)
        string += '  Velocity std (Body): %.2f, %.2f, %.2f (m/s, m/s, m/s)\n' % tuple(self.velocity_std_body_mps)
        string += '  Geoid undulation: %.2f m\n' % self.undulation_m
        string += '  Protection levels:\n'
        string += '    Aggregate: %.2f m\n' % self.aggregate_protection_level_m
        string += '    Horizontal: %.2f m\n' % self.horizontal_protection_level_m
        string += '    Vertical: %.2f m' % self.vertical_protection_level_m
        return string

    @classmethod
    def calcsize(cls) -> int:
        return 2 * Timestamp.calcsize() + cls._STRUCT.size

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'gps_time': np.array([float(m.gps_time) for m in messages]),
            'solution_type': np.array([int(m.solution_type) for m in messages], dtype=int),
            'flags': np.array([m.flags for m in messages], dtype=int),
            'undulation': np.array([m.undulation_m for m in messages]),
            'lla_deg': np.array([m.lla_deg for m in messages]).T,
            'ypr_deg': np.array([m.ypr_deg for m in messages]).T,
            'velocity_body_mps': np.array([m.velocity_body_mps for m in messages]).T,
            'position_std_enu_m': np.array([m.position_std_enu_m for m in messages]).T,
            'ypr_std_deg': np.array([m.ypr_std_deg for m in messages]).T,
            'velocity_std_body_mps': np.array([m.velocity_std_body_mps for m in messages]).T,
            'aggregate_protection_level_m': np.array([m.aggregate_protection_level_m for m in messages]),
            'horizontal_protection_level_m': np.array([m.horizontal_protection_level_m for m in messages]),
            'vertical_protection_level_m': np.array([m.vertical_protection_level_m for m in messages]),
        }
        return result


class PoseAuxMessage(MessagePayload):
    """!
    @brief Auxiliary platform pose information.
    """
    MESSAGE_TYPE = MessageType.POSE_AUX
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<3f 9d 4d 3d 3f')

    def __init__(self):
        self.p1_time = Timestamp()

        self.position_std_body_m = np.full((3,), np.nan)
        self.position_cov_enu_m2 = np.full((3, 3), np.nan)

        self.attitude_quaternion = np.full((4,), np.nan)

        self.velocity_enu_mps = np.full((3,), np.nan)
        self.velocity_std_enu_mps = np.full((3,), np.nan)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        offset += self.pack_values(
            self._STRUCT, buffer, offset,
            self.position_std_body_m,
            self.position_cov_enu_m2,
            self.attitude_quaternion,
            self.velocity_enu_mps,
            self.velocity_std_enu_mps)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)

        offset += self.unpack_values(
            self._STRUCT, buffer, offset,
            self.position_std_body_m,
            self.position_cov_enu_m2,
            self.attitude_quaternion,
            self.velocity_enu_mps,
            self.velocity_std_enu_mps)

        return offset - initial_offset

    def __str__(self):
        return 'Pose Aux Message @ %s' % str(self.p1_time)

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp.calcsize() + cls._STRUCT.size

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'position_std_body_m': np.array([m.position_std_body_m for m in messages]).T,
            # Note: This is Nx3x3, not 3x3xN
            'position_cov_enu_m2': np.array([m.position_cov_enu_m2 for m in messages]),
            'attitude_quaternion': np.array([m.attitude_quaternion for m in messages]).T,
            'velocity_enu_mps': np.array([m.velocity_enu_mps for m in messages]).T,
            'velocity_std_enu_mps': np.array([m.velocity_std_enu_mps for m in messages]).T,
        }
        return result


class GNSSInfoMessage(MessagePayload):
    """!
    @brief Information about the GNSS data used in the @ref PoseMessage with the corresponding timestamp.
    """
    MESSAGE_TYPE = MessageType.GNSS_INFO
    MESSAGE_VERSION = 1

    INVALID_LEAP_SECOND = 0xFF
    INVALID_AGE = 0xFFFF
    INVALID_DISTANCE = 0xFFFF
    INVALID_REFERENCE_STATION = 0xFFFFFFFF

    _STRUCT = struct.Struct('<BBxxHHIfffff')

    def __init__(self):
        self.p1_time = Timestamp()
        self.gps_time = Timestamp()

        self.leap_second = GNSSInfoMessage.INVALID_LEAP_SECOND
        self.num_svs = 0

        self.corrections_age_sec = np.nan
        self.baseline_distance_m = np.nan
        self.reference_station_id = GNSSInfoMessage.INVALID_REFERENCE_STATION

        self.gdop = np.nan
        self.pdop = np.nan
        self.hdop = np.nan
        self.vdop = np.nan

        self.gps_time_std_sec = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)
        offset += self.gps_time.pack(buffer, offset, return_buffer=False)

        if np.isnan(self.corrections_age_sec):
            corrections_age = GNSSInfoMessage.INVALID_AGE
        else:
            corrections_age = round(self.corrections_age_sec * 10.0)

        if np.isnan(self.baseline_distance_m):
            baseline_distance = GNSSInfoMessage.INVALID_DISTANCE
        else:
            baseline_distance = round(self.baseline_distance_m / 10.0)

        self._STRUCT.pack_into(
            buffer, offset,
            self.leap_second, self.num_svs,
            corrections_age, baseline_distance, self.reference_station_id,
            self.gdop, self.pdop, self.hdop, self.vdop,
            self.gps_time_std_sec)
        offset += self._STRUCT.size

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)
        offset += self.gps_time.unpack(buffer, offset)

        (leap_second, num_svs,
         corrections_age, baseline_distance, self.reference_station_id,
         self.gdop, self.pdop, self.hdop, self.vdop,
         self.gps_time_std_sec) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        # The following fields were added in message version 1.
        if message_version >= 1:
            self.leap_second = leap_second
            self.num_svs = num_svs
            self.corrections_age_sec = (np.nan if corrections_age == GNSSInfoMessage.INVALID_AGE else
                                        (corrections_age * 0.1))
            self.baseline_distance_m = (np.nan if baseline_distance == GNSSInfoMessage.INVALID_DISTANCE else
                                        (baseline_distance * 10.0))
        else:
            self.leap_second = GNSSInfoMessage.INVALID_LEAP_SECOND
            self.num_svs = 0
            self.corrections_age_sec = np.nan
            self.baseline_distance_m = np.nan

        return offset - initial_offset

    def __repr__(self):
        if self.gps_time:
            gps_str = f'{str(self.gps_time).replace("GPS: ", "")} ' \
                      f'({datetime_to_string(self.gps_time.as_utc())} UTC)'
        else:
            gps_str = 'None'
        if self.reference_station_id != GNSSInfoMessage.INVALID_REFERENCE_STATION:
            station_str = str(self.reference_station_id)
        else:
            station_str = 'None'

        result = super().__repr__()[:-1]
        result += f', gps_time={gps_str}, num_svs={self.num_svs}, station={station_str}, ' \
                  f'age={self.corrections_age_sec:.1f} sec, baseline={self.baseline_distance_m * 1e-3:.1f} km]'
        return result

    def __str__(self):
        string = 'GNSS Info Message @ %s\n' % str(self.p1_time)
        if self.gps_time:
            gps_str = f'{str(self.gps_time).replace("GPS: ", "")}'
            utc_str = f'{datetime_to_string(self.gps_time.as_utc())}'
        else:
            gps_str = 'None'
            utc_str = 'None'
        string += '  GPS time: %s\n' % gps_str
        string += '  UTC time: %s\n' % utc_str
        string += '  UTC leap second: %s\n' % \
                  (self.leap_second if self.leap_second != GNSSInfoMessage.INVALID_LEAP_SECOND else 'unknown')
        string += '  # SVs used: %d\n' % self.num_svs
        string += ('  Reference station: %s\n' %
                   (str(self.reference_station_id)
                    if self.reference_station_id != GNSSInfoMessage.INVALID_REFERENCE_STATION
                    else 'none'))
        string += '  Corrections age: %.1f sec\n' % self.corrections_age_sec
        string += '  Baseline distance: %.2f km\n' % (self.baseline_distance_m * 1e-3)
        string += '  GDOP: %.1f  PDOP: %.1f\n' % (self.gdop, self.pdop)
        string += '  HDOP: %.1f  VDOP: %.1f' % (self.hdop, self.vdop)
        return string

    def calcsize(self) -> int:
        return 2 * Timestamp.calcsize() + self._STRUCT.size

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'gps_time': np.array([float(m.gps_time) for m in messages]),
            'gps_time_std_sec': np.array([m.baseline_distance_m for m in messages]),
            'leap_second': np.array([int(m.leap_second) for m in messages], dtype=int),
            'num_svs': np.array([int(m.num_svs) for m in messages], dtype=int),
            'corrections_age_sec': np.array([m.corrections_age_sec for m in messages]),
            'baseline_distance_m': np.array([m.baseline_distance_m for m in messages]),
            'reference_station_id': np.array([int(m.reference_station_id) for m in messages], dtype=np.uint32),
            'gdop': np.array([m.gdop for m in messages]),
            'pdop': np.array([m.pdop for m in messages]),
            'hdop': np.array([m.hdop for m in messages]),
            'vdop': np.array([m.vdop for m in messages]),
        }
        return result


class SatelliteInfo:
    """!
    @brief Information about an individual satellite.
    """
    SATELLITE_USED = 0x01

    INVALID_CN0 = 0

    _STRUCT = struct.Struct('<BBBBff')

    def __init__(self):
        self.system = SatelliteType.UNKNOWN
        self.prn = 0
        self.usage = 0
        self.azimuth_deg = np.nan
        self.elevation_deg = np.nan
        ## The C/N0 of the L1 signal present on this satellite (in dB-Hz).
        self.cn0_dbhz = np.nan

    def get_satellite_id(self) -> SatelliteID:
        return SatelliteID(system=self.system, prn=self.prn)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        if np.isnan(self.cn0_dbhz):
            cn0_int = SatelliteInfo.INVALID_CN0
        else:
            cn0_int = round(self.cn0_dbhz / 0.25)
            if cn0_int > 255:
                cn0_int = 255
            elif cn0_int < 1:
                cn0_int = 1

        self._STRUCT.pack_into(
            buffer, offset,
            int(self.system), self.prn, self.usage, cn0_int, self.azimuth_deg, self.elevation_deg)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        (system_int, self.prn, self.usage, cn0_int, self.azimuth_deg, self.elevation_deg) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)

        self.system = SatelliteType(system_int)

        if cn0_int == SatelliteInfo.INVALID_CN0:
            self.cn0_dbhz = np.nan
        else:
            self.cn0_dbhz = cn0_int * 0.25

        return self.calcsize()

    def used_in_solution(self):
        return self.usage & SatelliteInfo.SATELLITE_USED

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size


class GNSSSatelliteMessage(MessagePayload):
    """!
    @brief Information about the GNSS data used in the @ref PoseMessage with the corresponding timestamp.
    """
    MESSAGE_TYPE = MessageType.GNSS_SATELLITE
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<H2x')

    def __init__(self):
        self.p1_time = Timestamp()
        self.gps_time = Timestamp()

        self.svs: List[SatelliteInfo] = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)
        offset += self.gps_time.pack(buffer, offset, return_buffer=False)

        self._STRUCT.pack_into(buffer, offset, len(self.svs))
        offset += self._STRUCT.size

        for sv in self.svs:
            offset += sv.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)
        offset += self.gps_time.unpack(buffer, offset)

        (num_svs,) = self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.svs = []
        for i in range(num_svs):
            sv = SatelliteInfo()
            offset += sv.unpack(buffer, offset)
            self.svs.append(sv)

        return offset - initial_offset

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', num_svs={len(self.svs)}]'
        return result

    def __str__(self):
        string = 'GNSS Satellite Message @ %s\n' % str(self.p1_time)
        string += '  %d SVs:' % len(self.svs)
        for sv in self.svs:
            string += '\n'
            string += '    %s PRN %d:\n' % (sv.system.name, sv.prn)
            string += '      Used in solution: %s\n' % ('yes' if sv.used_in_solution() else 'no')
            string += '      Az/el: %.1f, %.1f deg\n' % (sv.azimuth_deg, sv.elevation_deg)
            if np.isnan(sv.cn0_dbhz):
                string += '      C/N0: invalid'
            else:
                string += '      C/N0: %.1f dB-Hz' % sv.cn0_dbhz
        return string

    def calcsize(self) -> int:
        return 2 * Timestamp.calcsize() + GNSSSatelliteMessage._SIZE + len(self.svs) * SatelliteInfo.calcsize()

    def to_gnss_signals_message(self) -> 'GNSSSignalsMessage':
        """!
        @brief Convert this message to the newer @ref GNSSSignalsMessage format.

        @note
        The deprecated @ref GNSSSatelliteMessage does not store information about individual GNSS signals. This function
        assumes that each satellite present in the message is being tracked on the L1 civilian signal on that
        constellation.

        @return A @ref GNSSSignalsMessage.
        """
        l1_signal_types_per_system = {
            SatelliteType.GPS: GNSSSignalType.GPS_L1CA,
            SatelliteType.GLONASS: GNSSSignalType.GLONASS_L1CA,
            SatelliteType.GALILEO: GNSSSignalType.GALILEO_E1BC,
            SatelliteType.BEIDOU: GNSSSignalType.BEIDOU_B1I,
            SatelliteType.QZSS: GNSSSignalType.QZSS_L1CA,
            SatelliteType.SBAS: GNSSSignalType.SBAS_L1CA,
        }

        result = GNSSSignalsMessage()
        result.p1_time = self.p1_time
        result.gps_time = self.gps_time
        if self.gps_time:
            gps_time_sec = float(self.gps_time)
            result.gps_week = int(gps_time_sec / SECONDS_PER_WEEK)
            result.gps_tow_ms = int(round((gps_time_sec - result.gps_week * SECONDS_PER_WEEK) * 1e3))

        for sv_entry in self.svs:
            sv = sv_entry.get_satellite_id()
            signal_type = l1_signal_types_per_system.get(sv.get_satellite_type(), None)
            if signal_type is None:
                continue
            signal = SignalID(signal_type=signal_type, prn=sv.get_prn())

            is_used = (sv_entry.usage & SatelliteInfo.SATELLITE_USED) != 0
            flags = 0
            if is_used:
                flags |= (GNSSSatelliteInfo.STATUS_FLAG_HAS_EPHEM | GNSSSatelliteInfo.STATUS_FLAG_IS_USED)
            sv_info = GNSSSatelliteInfo(
                system=sv.get_satellite_type(), prn=sv.get_prn(),
                azimuth_deg=sv_entry.azimuth_deg, elevation_deg=sv_entry.elevation_deg,
                status_flags=flags)
            result.sat_info[sv] = sv_info

            # This message doesn't indicate which measurements were used for a given satellite. We'll assume all of
            # them, which may not be accurate.
            #
            # To avoid confusion, since we actually don't have tracking status, we'll assume that a signal has valid
            # measurements if it is _present at all_. Otherwise, its tracking status could appear to change rapidly when
            # plotted if the navigation engine simply decides not to use it for any reason. Since we do not know if we
            # are fixed, we cannot accurately indicate "carrier ambiguity resolved", so we'll leave that out.
            flags = (GNSSSignalInfo.STATUS_FLAG_VALID_PR | GNSSSignalInfo.STATUS_FLAG_VALID_DOPPLER |
                     GNSSSignalInfo.STATUS_FLAG_CARRIER_LOCKED)
            if is_used:
                flags |= (GNSSSignalInfo.STATUS_FLAG_USED_PR | GNSSSignalInfo.STATUS_FLAG_USED_DOPPLER |
                          GNSSSignalInfo.STATUS_FLAG_USED_CARRIER)
            signal_info = GNSSSignalInfo(
                signal_type=signal_type, prn=sv.get_prn(),
                cn0_dbhz=sv_entry.cn0_dbhz,
                status_flags=flags)
            result.signal_info[signal] = signal_info

        return result

    @classmethod
    def to_numpy(cls, messages):
        return {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'gps_time': np.array([float(m.gps_time) for m in messages]),
            'num_svs': np.array([len(m.svs) for m in messages], dtype=int),
            'num_used_svs': np.array([len([sv for sv in m.svs if sv.used_in_solution()]) for m in messages], dtype=int),
            'flattened_data': cls.flatten(messages),
        }

    @classmethod
    def group_by_sv(cls, input):
        flattened_data = cls.flatten(input)

        all_p1_time = flattened_data['p1_time']
        all_gps_time = flattened_data['gps_time']
        all_sv_ids = np.array([encode_signal_hash(entry.system, entry.prn)
                              for entry in flattened_data['data']], dtype=int)
        all_azim_deg = np.array([entry.azimuth_deg for entry in flattened_data['data']])
        all_elev_deg = np.array([entry.elevation_deg for entry in flattened_data['data']])
        all_cn0_dbhz = np.array([entry.cn0_dbhz for entry in flattened_data['data']])
        all_flags = np.array([entry.usage for entry in flattened_data['data']], dtype=int)

        svs = np.unique(all_sv_ids)
        results = {}
        for sv in svs:
            idx = all_sv_ids == sv
            results[sv] = {
                'p1_time': all_p1_time[idx],
                'gps_time': all_gps_time[idx],
                'azimuth_deg': all_azim_deg[idx],
                'elevation_deg': all_elev_deg[idx],
                'cn0_dbhz': all_cn0_dbhz[idx],
                'flags': all_flags[idx],
            }
        return results

    @classmethod
    def group_by_time(cls, input):
        flattened_data = cls.flatten(input)

        all_p1_time = flattened_data['p1_time']
        all_gps_time = flattened_data['gps_time']
        all_sv_ids = np.array([encode_signal_hash(entry.system, entry.prn)
                              for entry in flattened_data['data']], dtype=int)
        all_azim_deg = np.array([entry.azimuth_deg for entry in flattened_data['data']])
        all_elev_deg = np.array([entry.elevation_deg for entry in flattened_data['data']])
        all_cn0_dbhz = np.array([entry.cn0_dbhz for entry in flattened_data['data']])
        all_flags = np.array([entry.usage for entry in flattened_data['data']], dtype=int)

        p1_times = np.unique(flattened_data['p1_time'])
        results = {}
        for p1_time in p1_times:
            idx = all_p1_time == p1_time
            results[p1_time] = {
                'gps_time': all_gps_time[idx][0] if np.any(idx) else np.nan,
                'sv_id': all_sv_ids[idx],
                'azimuth_deg': all_azim_deg[idx],
                'elevation_deg': all_elev_deg[idx],
                'cn0_dbhz': all_cn0_dbhz[idx],
                'flags': all_flags[idx],
            }
        return results

    @classmethod
    def flatten(cls, input):
        # Check if this object contains already-flattened data.
        if isinstance(input, object) and hasattr(input, 'flattened_data'):
            return input.flattened_data
        elif isinstance(input, dict) and 'p1_time' in input and 'data' in input:
            flattened_data = input['data']
        else:
            return {
                'p1_time': np.array([float(m.p1_time) for m in input for _ in m.svs]),
                'gps_time': np.array([float(m.gps_time) for m in input for _ in m.svs]),
                'data': [entry for m in input for entry in m.svs]
            }


# Breaking the declaration up allows specifying the class properties without affecting constructor or property
# iteration.
@dataclass
class _GNSSSatelliteInfo:
    system: SatelliteType = SatelliteType.UNKNOWN
    elevation_deg: float = np.nan
    azimuth_deg: float = np.nan
    prn: int = 0
    status_flags: int = 0


class GNSSSatelliteInfo(_GNSSSatelliteInfo):
    STATUS_FLAG_IS_USED = 0x01
    STATUS_FLAG_IS_UNHEALTHY = 0x02
    STATUS_FLAG_IS_NON_LINE_OF_SIGHT = 0x04
    STATUS_FLAG_HAS_EPHEM = 0x10
    STATUS_FLAG_HAS_SBAS = 0x20

    _INVALID_AZIMUTH = 0xFFFF
    _INVALID_ELEVATION = 0x7FFF

    _STRUCT = struct.Struct('<BBBxhH')

    def get_satellite_id(self) -> SatelliteID:
        return SatelliteID(system=self.system, prn=self.prn)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        initial_offset = offset

        self._STRUCT.pack_into(
            buffer, offset,
            int(self.system),
            self.prn,
            self.status_flags,
            self._INVALID_ELEVATION if np.isnan(self.elevation_deg) else int(np.round(self.elevation_deg * 100.0)),
            self._INVALID_AZIMUTH if np.isnan(self.azimuth_deg) else int(np.round(self.azimuth_deg * 100.0)))
        offset += self._STRUCT.size

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        (system,
         self.prn,
         self.status_flags,
         elev_int,
         azim_int) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.system = SatelliteType(system, raise_on_unrecognized=False)
        self.elevation_deg = np.nan if elev_int == self._INVALID_ELEVATION else (elev_int * 0.01)
        self.azimuth_deg = np.nan if azim_int == self._INVALID_AZIMUTH else (azim_int * 0.01)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size


# Breaking the declaration up allows specifying the class properties without affecting constructor or property
# iteration.
@dataclass
class _GNSSSignalInfo:
    signal_type: GNSSSignalType = GNSSSignalType.UNKNOWN
    prn: int = 0
    cn0_dbhz: float = np.nan
    status_flags: int = 0


class GNSSSignalInfo(_GNSSSignalInfo):
    STATUS_FLAG_USED_PR = 0x01
    STATUS_FLAG_USED_DOPPLER = 0x02
    STATUS_FLAG_USED_CARRIER = 0x04
    STATUS_FLAG_CARRIER_AMBIGUITY_RESOLVED = 0x08

    STATUS_FLAG_VALID_PR = 0x10
    STATUS_FLAG_VALID_DOPPLER = 0x20
    STATUS_FLAG_CARRIER_LOCKED = 0x40

    STATUS_FLAG_HAS_RTK = 0x100
    STATUS_FLAG_HAS_SBAS = 0x200
    STATUS_FLAG_HAS_EPHEM = 0x400

    _INVALID_CN0 = 0

    _STRUCT = struct.Struct('<HBBH2x')

    def get_signal_id(self) -> SignalID:
        return SignalID(signal_type=self.signal_type, prn=self.prn)

    def get_satellite_id(self) -> SatelliteID:
        return SatelliteID(system=self.signal_type.get_satellite_type(), prn=self.prn)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        initial_offset = offset

        self._STRUCT.pack_into(
            buffer, offset,
            int(self.signal_type),
            self.prn,
            self._INVALID_CN0 if np.isnan(self.cn0_dbhz) else int(np.round(self.cn0_dbhz / 0.25)),
            self.status_flags)
        offset += self._STRUCT.size

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        (signal_type,
         self.prn,
         cn0_int,
         self.status_flags) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.signal_type = GNSSSignalType(signal_type, raise_on_unrecognized=False)
        self.cn0_dbhz = np.nan if cn0_int == self._INVALID_CN0 else cn0_int * 0.25

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size


class GNSSSignalsMessage(MessagePayload):
    """!
    @brief Information about the individual GNSS satellites and signals used in the pose solution.
    """
    MESSAGE_TYPE = MessageType.GNSS_SIGNALS
    MESSAGE_VERSION = 1

    _INVALID_GPS_WEEK = 0xFFFF
    _INVALID_GPS_TOW = 0xFFFFFFFF

    _STRUCT = struct.Struct('<IH HB 7x')

    def __init__(self):
        self.p1_time = Timestamp()
        self.gps_time = Timestamp()
        self.gps_tow_ms: Optional[int] = None
        self.gps_week: Optional[int] = None
        self.sat_info: Dict[SatelliteID, GNSSSatelliteInfo] = {}
        self.signal_info: Dict[SignalID, GNSSSignalInfo] = {}

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)
        offset += self.gps_time.pack(buffer, offset, return_buffer=False)

        self._STRUCT.pack_into(
            buffer, offset,
            self._INVALID_GPS_TOW if self.gps_tow_ms is None else self.gps_tow_ms,
            self._INVALID_GPS_WEEK if self.gps_week is None else self.gps_week,
            len(self.signal_info),
            len(self.sat_info))
        offset += self._STRUCT.size

        for info in self.sat_info.values():
            offset += info.pack(buffer, offset, return_buffer=False)

        for info in self.signal_info.values():
            offset += info.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        # Legacy version 0 not supported.
        if message_version == 0:
            raise NotImplementedError('GNSSSignalsMessage version 0 not supported.')

        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)
        offset += self.gps_time.unpack(buffer, offset)

        (gps_tow_ms_int,
         gps_week_int,
         num_signals,
         num_satellites) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.gps_tow_ms = None if gps_tow_ms_int == self._INVALID_GPS_TOW else gps_tow_ms_int
        self.gps_week = None if gps_week_int == self._INVALID_GPS_WEEK else gps_week_int

        sat_info_list = [GNSSSatelliteInfo() for _ in range(num_satellites)]
        for info in sat_info_list:
            offset += info.unpack(buffer, offset, version=message_version)

        signal_info_list = [GNSSSignalInfo() for _ in range(num_signals)]
        for info in signal_info_list:
            offset += info.unpack(buffer, offset, version=message_version)

        self.sat_info = {e.get_satellite_id(): e for e in sat_info_list}
        self.signal_info = {e.get_signal_id(): e for e in signal_info_list}

        return offset - initial_offset

    def calcsize(self) -> int:
        return ((2 * Timestamp.calcsize()) + GNSSSignalsMessage._STRUCT.size +
                (len(self.sat_info) * GNSSSatelliteInfo.calcsize()) +
                (len(self.signal_info) * GNSSSignalInfo.calcsize()))

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', num_svs={len(self.sat_info)}, num_signals={len(self.signal_info)}]'
        return result

    def __str__(self):
        string = 'GNSS Signals Message @ %s\n' % str(self.p1_time)
        string += '  %d SVs:' % len(self.sat_info)

        def _signal_usage_str(status_flags: int) -> str:
            if status_flags & GNSSSignalInfo.STATUS_FLAG_CARRIER_AMBIGUITY_RESOLVED:
                return 'Fixed'
            elif status_flags & GNSSSignalInfo.STATUS_FLAG_USED_CARRIER:
                return 'Float'
            elif status_flags & GNSSSignalInfo.STATUS_FLAG_USED_PR:
                return 'PR'
            else:
                return "No"

        def _signal_tracking_str(status_flags: int) -> str:
            if status_flags & GNSSSignalInfo.STATUS_FLAG_CARRIER_LOCKED:
                return 'PR,CP'
            elif status_flags & GNSSSignalInfo.STATUS_FLAG_VALID_PR:
                return 'PR'
            else:
                return 'No'

        for sv, info in self.sat_info.items():
            string += '\n'
            string += '    %s:\n' % str(sv)
            string += '      Used in solution: %s\n' % \
                      ('yes' if (info.status_flags | info.STATUS_FLAG_IS_USED) else 'no')
            string += '      Az/el: %.1f, %.1f deg' % (info.azimuth_deg, info.elevation_deg)
        string += '\n  %d signals:' % len(self.signal_info)
        for signal, info in self.signal_info.items():
            string += '\n'
            string += '    %s:\n' % str(signal)
            string += '      C/N0: %.1f dB-Hz\n' % (info.cn0_dbhz,)
            string += '      Available: %s\n' % (_signal_tracking_str(info.status_flags),)
            string += '      Used: %s' % (_signal_usage_str(info.status_flags),)
        return string

    @classmethod
    def to_numpy(cls, messages: List['GNSSSignalsMessage']):
        flat_sv_info = [(m, sv, info) for m in messages for sv, info in m.sat_info.items()]
        sv_ids = np.array([e[1] for e in flat_sv_info], dtype=SatelliteID)
        sv_data = {
            'p1_time': np.array([float(e[0].p1_time) for e in flat_sv_info]),
            'gps_time': np.array([float(e[0].gps_time) for e in flat_sv_info]),
            'gps_week': np.array([(e[0].gps_week if e[0].gps_week is not None else -1) for e in flat_sv_info],
                                 dtype=int),
            'gps_tow_sec': np.array([(e[0].gps_tow_ms * 1e-3 if e[0].gps_tow_ms is not None else np.nan)
                                     for e in flat_sv_info]),
            'sv': sv_ids,
            'sv_hash': sv_ids.astype(int),
            'azimuth_deg': np.array([e[2].azimuth_deg for e in flat_sv_info]),
            'elevation_deg': np.array([e[2].elevation_deg for e in flat_sv_info]),
            'status_flags': np.array([e[2].status_flags for e in flat_sv_info], dtype=int),
        }

        flat_sig_info = [(m, signal, info) for m in messages for signal, info in m.signal_info.items()]
        signal_ids = np.array([e[1] for e in flat_sig_info], dtype=SignalID)
        signal_data = {
            'p1_time': np.array([float(e[0].p1_time) for e in flat_sig_info]),
            'gps_time': np.array([float(e[0].gps_time) for e in flat_sig_info]),
            'gps_week': np.array([(e[0].gps_week if e[0].gps_week is not None else -1) for e in flat_sig_info],
                                 dtype=int),
            'gps_tow_sec': np.array([(e[0].gps_tow_ms * 1e-3 if e[0].gps_tow_ms is not None else np.nan)
                                     for e in flat_sig_info]),
            'signal': signal_ids,
            'signal_hash': signal_ids.astype(int),
            'cn0_dbhz': np.array([e[2].cn0_dbhz for e in flat_sig_info]),
            'status_flags': np.array([e[2].status_flags for e in flat_sig_info], dtype=int),
        }

        return {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'gps_time': np.array([float(m.gps_time) for m in messages]),
            'gps_week': np.array([(m.gps_week if m.gps_week is not None else -1) for m in messages],
                                 dtype=int),
            'gps_tow_sec': np.array([(m.gps_tow_ms * 1e-3 if m.gps_tow_ms is not None else np.nan)
                                     for m in messages]),
            'num_svs': np.array([len(m.sat_info) for m in messages], dtype=int),
            'num_signals': np.array([len(m.signal_info) for m in messages], dtype=int),
            'sv_data': sv_data,
            'signal_data': signal_data,
        }


class CalibrationStage(IntEnum):
    """!
    @brief The stages of the device calibration process.
    """
    UNKNOWN = 0, ##< Calibration stage not known.
    MOUNTING_ANGLE = 1, ##< Estimating IMU mounting angles.
    DONE = 255, ##< Calibration complete.


class CalibrationStatus(MessagePayload):
    """!
    @brief Device calibration status update.
    """
    MESSAGE_TYPE = MessageType.CALIBRATION_STATUS
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<B3x 3f3f f 24x ?3x BBB 5x f3f')

    def __init__(self):
        ## The most recent P1 time, if available.
        self.p1_time = Timestamp()

        ## @name Calibration State Data
        ## @{

        ## The current calibration stage.
        self.calibration_stage = CalibrationStage.UNKNOWN

        ## The IMU yaw, pitch, and roll mounting angle offsets (in degrees).
        self.ypr_deg = np.full((3,), np.nan)

        ## The IMU yaw, pitch, and roll mounting angle standard deviations (in degrees).
        self.ypr_std_dev_deg = np.full((3,), np.nan)

        ## The accumulated calibration travel distance (in meters).
        self.travel_distance_m = np.nan

        ## @}

        ## @name Calibration Process Status
        ## @{

        ## Set to `True` once the navigation engine state is validated after initialization.
        self.state_verified = False

        ## The completion percentage for gyro bias estimation.
        self.gyro_bias_percent_complete = 0.0

        ## The completion percentage for accelerometer bias estimation.
        self.accel_bias_percent_complete = 0.0

        ## The completion percentage for IMU mounting angle estimation.
        self.mounting_angle_percent_complete = 0.0

        ## @}

        ## @name Calibration Thresholds
        ## @{

        ## The minimum accumulated calibration travel distance needed to complete mounting angle calibration.
        self.min_travel_distance_m = np.nan

        ## The max threshold for each of the YPR mounting angle states (in degrees), above which calibration is
        ##  incomplete.
        self.mounting_angle_max_std_dev_deg = np.full((3,), np.nan)

        ## @}

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())
            offset = 0

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        self._STRUCT.pack_into(
            buffer, offset,
            self.calibration_stage,
            self.ypr_deg[0], self.ypr_deg[2], self.ypr_deg[3],
            self.ypr_std_dev_deg[0], self.ypr_std_dev_deg[2], self.ypr_std_dev_deg[3],
            self.travel_distance_m,
            self.state_verified,
            self.gyro_bias_percent_complete * 2.0,
            self.accel_bias_percent_complete * 2.0,
            self.mounting_angle_percent_complete * 2.0,
            self.min_travel_distance_m,
            self.mounting_angle_max_std_dev_deg[0], self.mounting_angle_max_std_dev_deg[1],
            self.mounting_angle_max_std_dev_deg[2])
        offset += self._STRUCT.size

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)

        (self.calibration_stage,
         self.ypr_deg[0], self.ypr_deg[1], self.ypr_deg[2],
         self.ypr_std_dev_deg[0], self.ypr_std_dev_deg[1], self.ypr_std_dev_deg[2],
         self.travel_distance_m,
         self.state_verified,
         self.gyro_bias_percent_complete,
         self.accel_bias_percent_complete,
         self.mounting_angle_percent_complete,
         self.min_travel_distance_m,
         self.mounting_angle_max_std_dev_deg[0], self.mounting_angle_max_std_dev_deg[1],
         self.mounting_angle_max_std_dev_deg[2]) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.calibration_stage = CalibrationStage(self.calibration_stage)

        self.gyro_bias_percent_complete /= 2.0
        self.accel_bias_percent_complete /= 2.0
        self.mounting_angle_percent_complete /= 2.0

        return offset - initial_offset

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', stage={self.calibration_stage}, mounting_angle={self.mounting_angle_percent_complete:.1f}%]'
        return result

    def __str__(self):
        string = 'Calibration Status Message @ %s\n' % str(self.p1_time)
        string += '  Stage: %s\n' % CalibrationStage(self.calibration_stage).to_string()
        string += '  Completion: gyro=%.1f%%, accel=%.1f%%, mounting angles=%.1f%%\n' % \
                  (self.gyro_bias_percent_complete, self.accel_bias_percent_complete,
                   self.mounting_angle_percent_complete)
        string += '  Distance traveled: %.3f km (min: %.1f km)%s\n' % \
                  (self.travel_distance_m, self.min_travel_distance_m,
                   ' [OK]' if self.travel_distance_m >= self.min_travel_distance_m else '')
        string += '  Yaw: %.1f deg (std dev: %.1f deg, max: %.1f deg)%s\n' % \
                  (self.ypr_deg[0], self.ypr_std_dev_deg[0], self.mounting_angle_max_std_dev_deg[0],
                   ' [OK]' if self.ypr_std_dev_deg[0] < self.mounting_angle_max_std_dev_deg[0] else '')
        string += '  Pitch: %.1f deg (std dev: %.1f deg, max: %.1f deg)%s\n' % \
                  (self.ypr_deg[1], self.ypr_std_dev_deg[1], self.mounting_angle_max_std_dev_deg[1],
                   ' [OK]' if self.ypr_std_dev_deg[1] < self.mounting_angle_max_std_dev_deg[1] else '')
        string += '  Roll: %.1f deg (std dev: %.1f deg, max: %.1f deg)%s' % \
                  (self.ypr_deg[2], self.ypr_std_dev_deg[2], self.mounting_angle_max_std_dev_deg[2],
                   ' [OK]' if self.ypr_std_dev_deg[2] < self.mounting_angle_max_std_dev_deg[2] else '')
        return string

    def calcsize(self) -> int:
        return Timestamp.calcsize() + self._STRUCT.size

    @classmethod
    def to_numpy(cls, messages: Sequence['CalibrationStatus']):
        # In some cases, the early calibration status messages may not be complete, and may include entries with an
        # unknown stage and nan values if the system is not fully initialized. Find the first non-nan entry.
        if len(messages) > 0:
            calibration_stage = np.array([int(m.calibration_stage) for m in messages], dtype=int)
            idx = np.argmax(calibration_stage != CalibrationStage.UNKNOWN)
            if idx > 0 or not calibration_stage[0] != CalibrationStage.UNKNOWN:
                messages = messages[idx:]

        result = {
            '__metadata__': {
              'not_time_dependent': [
                  'min_travel_distance_m',
                  'mounting_angle_max_std_dev_deg',
              ],
            },
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'calibration_stage': np.array([int(m.calibration_stage) for m in messages], dtype=int),
            'ypr_deg': np.array([m.ypr_deg for m in messages]).T,
            'ypr_std_dev_deg': np.array([m.ypr_std_dev_deg for m in messages]).T,
            'travel_distance_m': np.array([m.travel_distance_m for m in messages]),
            'state_verified': np.array([m.state_verified for m in messages], dtype=bool),
            'gyro_bias_percent_complete': np.array([m.gyro_bias_percent_complete for m in messages]),
            'accel_bias_percent_complete': np.array([m.accel_bias_percent_complete for m in messages]),
            'mounting_angle_percent_complete': np.array([m.mounting_angle_percent_complete for m in messages]),
            'min_travel_distance_m': messages[0].min_travel_distance_m if len(messages) > 0 else np.nan,
            'mounting_angle_max_std_dev_deg': (messages[0].mounting_angle_max_std_dev_deg
                                               if len(messages) > 0 else np.full((3,), np.nan)),
        }

        return result


class RelativeENUPositionMessage(MessagePayload):
    """!
    @brief Relative ENU position to base station.

    @note
    This message represents the relationship between the navigation engine's
    position solution and a nearby RTK base station. It is not used to convey
    unfiltered vehicle body orientation measurements generated using multiple
    GNSS antennas. See @ref GNSSAttitudeOutput instead.
    """
    MESSAGE_TYPE = MessageType.RELATIVE_ENU_POSITION
    MESSAGE_VERSION = 0

    INVALID_REFERENCE_STATION = 0xFFFFFFFF

    Construct = Struct(
        "p1_time" / TimestampConstruct,
        "gps_time" / TimestampConstruct,
        "solution_type" / AutoEnum(Int8ul, SolutionType),
        Padding(3),
        "reference_station_id" / Int32ul,
        "relative_position_enu_m" / Array(3, Float64l),
        "position_std_enu_m" / Array(3, Float32l),
    )

    def __init__(self):
        # The time of the message, in P1 time (beginning at power-on).
        self.p1_time = Timestamp()
        # The GPS time of the message, if available, referenced to 1980/1/6.
        self.gps_time = Timestamp()
        # The type of this position solution.
        self.solution_type = SolutionType.Invalid
        # The ID of the differential base station, if used.
        self.reference_station_id = RelativeENUPositionMessage.INVALID_REFERENCE_STATION
        ##
        # The relative position (in meters), resolved in the local ENU frame.
        #
        # @note
        # If a differential solution to the base station is not available, these
        # values will be `NAN`.
        ##
        self.relative_position_enu_m = np.full((3,), np.nan)
        ##
        # The position standard deviation (in meters), resolved with respect to the
        # local ENU tangent plane: east, north, up.
        #
        # @note
        # If a differential solution to the base station is not available, these
        # values will be `NAN`.
        ##
        self.position_std_enu_m = np.full((3,), np.nan)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', solution_type={self.solution_type}]'
        return result

    def __str__(self):
        return construct_message_to_string(
            message=self,
            title=f'RelativeENUPosition @ {self.p1_time}',
            fields=['gps_time', 'solution_type', 'reference_station_id', 'relative_position_enu_m',
                    'position_std_enu_m'])

    @classmethod
    def calcsize(cls) -> int:
        return cls.Construct.sizeof()

    @classmethod
    def to_numpy(cls, messages: Sequence['RelativeENUPositionMessage']):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'gps_time': np.array([float(m.gps_time) for m in messages]),
            'solution_type': np.array([int(m.solution_type) for m in messages], dtype=int),
            'reference_station_id': np.array([m.reference_station_id for m in messages]),
            'relative_position_enu_m': np.array([m.relative_position_enu_m for m in messages]).T,
            'position_std_enu_m': np.array([m.position_std_enu_m for m in messages]).T,
        }

        return result
