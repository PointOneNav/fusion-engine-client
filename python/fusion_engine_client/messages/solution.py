import struct
from typing import List, Sequence

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
    MESSAGE_VERSION = 1

    INVALID_UNDULATION = -32768

    _STRUCT = struct.Struct('<Bx h ddd fff ddd fff ddd fff fff')

    def __init__(self):
        self.p1_time = Timestamp()
        self.gps_time = Timestamp()

        self.solution_type = SolutionType.Invalid

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
        string += '  Position (LLA): %.6f, %.6f, %.3f (deg, deg, m)\n' % tuple(self.lla_deg)
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

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

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
        all_sv_ids = np.array([encode_signal_id(entry) for entry in flattened_data['data']], dtype=int)
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
        all_sv_ids = np.array([encode_signal_id(entry) for entry in flattened_data['data']], dtype=int)
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
