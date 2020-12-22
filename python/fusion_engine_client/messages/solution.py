import struct
from typing import List

import numpy as np

from .defs import *


class PoseMessage:
    """!
    @brief Platform pose solution (position, velocity, attitude).
    """
    MESSAGE_TYPE = MessageType.POSE

    _FORMAT = '<B3x ddd fff ddd fff ddd fff fff'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.p1_time = Timestamp()
        self.gps_time = Timestamp()

        self.solution_type = SolutionType.Invalid

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
            buffer = bytes(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)
        offset += self.gps_time.pack(buffer, offset, return_buffer=False)

        struct.pack_into(PoseMessage._FORMAT, buffer, offset,
                         int(self.solution_type),
                         self.lla_deg[0], self.lla_deg[1], self.lla_deg[2],
                         self.position_std_enu_m[0], self.position_std_enu_m[1], self.position_std_enu_m[2],
                         self.ypr_deg[0], self.ypr_deg[1], self.ypr_deg[2],
                         self.ypr_std_deg[0], self.ypr_std_deg[1], self.ypr_std_deg[2],
                         self.velocity_body_mps[0], self.velocity_body_mps[1], self.velocity_body_mps[2],
                         self.velocity_std_body_mps[0], self.velocity_std_body_mps[1], self.velocity_std_body_mps[2],
                         self.aggregate_protection_level_m,
                         self.horizontal_protection_level_m,
                         self.vertical_protection_level_m)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)
        offset += self.gps_time.unpack(buffer, offset)

        (solution_type_int,
         self.lla_deg[0], self.lla_deg[1], self.lla_deg[2],
         self.position_std_enu_m[0], self.position_std_enu_m[1], self.position_std_enu_m[2],
         self.ypr_deg[0], self.ypr_deg[1], self.ypr_deg[2],
         self.ypr_std_deg[0], self.ypr_std_deg[1], self.ypr_std_deg[2],
         self.velocity_body_mps[0], self.velocity_body_mps[1], self.velocity_body_mps[2],
         self.velocity_std_body_mps[0], self.velocity_std_body_mps[1], self.velocity_std_body_mps[2],
         self.aggregate_protection_level_m,
         self.horizontal_protection_level_m,
         self.vertical_protection_level_m) = \
            struct.unpack_from(PoseMessage._FORMAT, buffer=buffer, offset=offset)
        offset += PoseMessage._SIZE

        self.solution_type = SolutionType(solution_type_int)

        return offset - initial_offset

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.p1_time)

    def __str__(self):
        string = 'Pose message @ P1 time %s\n' % str(self.p1_time)
        string += '  Solution type: %s\n' % self.solution_type.name
        string += '  GPS time: %s\n' % str(self.gps_time.as_gps())
        string += '  Position (LLA): %.6f, %.6f, %.3f (deg, deg, m)\n' % tuple(self.lla_deg)
        string += '  Attitude (YPR): %.2f, %.2f, %.2f (deg, deg, deg)\n' % tuple(self.ypr_deg)
        string += '  Velocity (Body): %.2f, %.2f, %.2f (m/s, m/s, m/s)\n' % tuple(self.velocity_body_mps)
        string += '  Position std (ENU): %.2f, %.2f, %.2f (m, m, m)\n' % tuple(self.position_std_enu_m)
        string += '  Attitude std (YPR): %.2f, %.2f, %.2f (deg, deg, deg)\n' % tuple(self.ypr_std_deg)
        string += '  Velocity std (Body): %.2f, %.2f, %.2f (m/s, m/s, m/s)\n' % tuple(self.velocity_std_body_mps)
        string += '  Protection levels:\n'
        string += '    Aggregate: %.2f m\n' % self.aggregate_protection_level_m
        string += '    Horizontal: %.2f m\n' % self.horizontal_protection_level_m
        string += '    Vertical: %.2f m' % self.vertical_protection_level_m
        return string

    @classmethod
    def calcsize(cls) -> int:
        return 2 * Timestamp.calcsize() + PoseMessage._SIZE

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'gps_time': np.array([float(m.gps_time) for m in messages]),
            'solution_type': np.array([int(m.solution_type) for m in messages], dtype=int),
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


class PoseAuxMessage:
    """!
    @brief Auxiliary platform pose information.
    """
    MESSAGE_TYPE = MessageType.POSE_AUX

    _FORMAT = '<3f 9d 4d 3d 3f'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.p1_time = Timestamp()

        self.position_std_body_m = np.full((3,), np.nan)
        self.position_cov_enu_m2 = np.full((3, 3), np.nan)

        self.attitude_quaternion = np.full((4,), np.nan)

        self.velocity_enu_mps = np.full((3,), np.nan)
        self.velocity_std_enu_mps = np.full((3,), np.nan)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytes(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        struct.pack_into(PoseAuxMessage._FORMAT, buffer, offset,
                         *self.position_std_body_m,
                         *self.position_cov_enu_m2.flat,
                         *self.attitude_quaternion,
                         *self.velocity_enu_mps,
                         *self.velocity_std_enu_mps)
        offset += PoseAuxMessage._SIZE

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)

        MessageHeader.unpack_values(PoseAuxMessage._FORMAT, buffer, offset,
                                    self.position_std_body_m,
                                    self.position_cov_enu_m2,
                                    self.attitude_quaternion,
                                    self.velocity_enu_mps,
                                    self.velocity_std_enu_mps)
        offset += PoseAuxMessage._SIZE

        return offset - initial_offset

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.p1_time)

    def __str__(self):
        return 'Pose aux message @ P1 time %s' % str(self.p1_time)

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp.calcsize() + PoseAuxMessage._SIZE

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


class GNSSInfoMessage:
    """!
    @brief Information about the GNSS data used in the @ref PoseMessage with the corresponding timestamp.
    """
    MESSAGE_TYPE = MessageType.GNSS_INFO

    INVALID_REFERENCE_STATION = 0xFFFFFFFF

    _FORMAT = '<Ifffff'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.p1_time = Timestamp()
        self.gps_time = Timestamp()

        self.last_differential_time = Timestamp()

        self.reference_station_id = GNSSInfoMessage.INVALID_REFERENCE_STATION

        self.gdop = np.nan
        self.pdop = np.nan
        self.hdop = np.nan
        self.vdop = np.nan

        self.gps_time_std_sec = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytes(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)
        offset += self.gps_time.pack(buffer, offset, return_buffer=False)

        offset += self.last_differential_time.pack(buffer, offset, return_buffer=False)

        struct.pack_into(GNSSInfoMessage._FORMAT, buffer, offset,
                         self.reference_station_id,
                         self.gdop, self.pdop, self.hdop, self.vdop,
                         self.gps_time_std_sec)
        offset += GNSSInfoMessage._SIZE

        for sv in self.svs:
            offset += sv.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)
        offset += self.gps_time.unpack(buffer, offset)

        offset += self.last_differential_time.unpack(buffer, offset)

        (self.reference_station_id,
         self.gdop, self.pdop, self.hdop, self.vdop,
         self.gps_time_std_sec) = \
            struct.unpack_from(GNSSInfoMessage._FORMAT, buffer=buffer, offset=offset)
        offset += GNSSInfoMessage._SIZE

        return offset - initial_offset

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.p1_time)

    def __str__(self):
        string = 'GNSS info message @ P1 time %s\n' % str(self.p1_time)
        string += '  GPS time: %s\n' % str(self.gps_time.as_gps())
        string += ('  Reference station: %s\n' %
                   (str(self.reference_station_id)
                    if self.reference_station_id != GNSSInfoMessage.INVALID_REFERENCE_STATION
                    else 'none'))
        string += '  Last differential time: %s\n' % str(self.last_differential_time)
        string += '  GDOP: %.1f  PDOP: %.1f\n' % (self.gdop, self.pdop)
        string += '  HDOP: %.1f  VDOP: %.1f' % (self.hdop, self.vdop)
        return string

    def calcsize(self) -> int:
        return 3 * Timestamp.calcsize() + GNSSInfoMessage._SIZE


class SatelliteInfo:
    """!
    @brief Information about an individual satellite.
    """
    SATELLITE_USED = 0x01

    _FORMAT = '<BBBxff'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.system = SatelliteType.UNKNOWN
        self.prn = 0
        self.usage = 0
        self.azimuth_deg = np.nan
        self.elevation_deg = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        args = (int(self.system), self.prn, self.usage, self.azimuth_deg, self.elevation_deg)
        if buffer is None:
            buffer = struct.pack(SatelliteInfo._FORMAT, *args)
        else:
            struct.pack_into(SatelliteInfo._FORMAT, buffer=buffer, offset=offset, *args)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        (system_int, self.prn, self.usage, self.azimuth_deg, self.elevation_deg) = \
            struct.unpack_from(SatelliteInfo._FORMAT, buffer=buffer, offset=offset)
        self.system = SatelliteType(system_int)
        return self.calcsize()

    def used_in_solution(self):
        return self.usage & SatelliteInfo.SATELLITE_USED
        return string

    @classmethod
    def calcsize(cls) -> int:
        return SatelliteInfo._SIZE


class GNSSSatelliteMessage:
    """!
    @brief Information about the GNSS data used in the @ref PoseMessage with the corresponding timestamp.
    """
    MESSAGE_TYPE = MessageType.GNSS_SATELLITE

    _FORMAT = '<H2x'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.p1_time = Timestamp()
        self.gps_time = Timestamp()

        self.svs: List[SatelliteInfo] = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytes(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)
        offset += self.gps_time.pack(buffer, offset, return_buffer=False)

        struct.pack_into(GNSSSatelliteMessage._FORMAT, buffer, offset, len(self.svs))
        offset += GNSSSatelliteMessage._SIZE

        for sv in self.svs:
            offset += sv.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)
        offset += self.gps_time.unpack(buffer, offset)

        (num_svs,) = struct.unpack_from(GNSSSatelliteMessage._FORMAT, buffer=buffer, offset=offset)
        offset += GNSSSatelliteMessage._SIZE

        self.svs = []
        for i in range(num_svs):
            sv = SatelliteInfo()
            offset += sv.unpack(buffer, offset)
            self.svs.append(sv)

        return offset - initial_offset

    def __repr__(self):
        return '%s @ %s [%d SVs]' % (self.MESSAGE_TYPE.name, self.p1_time, len(self.svs))

    def __str__(self):
        string = 'GNSS satellite message @ P1 time %s\n' % str(self.p1_time)
        string += '  %d SVs:' % len(self.svs)
        for sv in self.svs:
            string += '\n'
            string += '    %s PRN %d:\n' % (sv.system.name, sv.prn)
            string += '      Used in solution: %s\n' % ('yes' if sv.used_in_solution() else 'no')
            string += '      Az/el: %.1f, %.1f deg' % (sv.azimuth_deg, sv.elevation_deg)
        return string

    def calcsize(self) -> int:
        return 2 * Timestamp.calcsize() + GNSSSatelliteMessage._SIZE + len(self.svs) * SatelliteInfo.calcsize()
