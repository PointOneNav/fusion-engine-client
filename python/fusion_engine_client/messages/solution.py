import struct
from typing import List

import numpy as np

from .defs import *


class PoseMessage:
    """!
    @brief Platform pose solution (position, velocity, attitude).
    """
    MESSAGE_TYPE = MessageType.POSE

    _FORMAT = '<B3x ddd ddd ddd ddd ddd ddd ddd'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.p1_time = Timestamp()
        self.gps_time = Timestamp()

        self.solution_type = SolutionType.Invalid

        self.lla_deg = np.full((3,), np.nan)
        self.ypr_deg = np.full((3,), np.nan)
        self.velocity_enu_mps = np.full((3,), np.nan)

        self.position_std_dev_ecef_m = np.full((3,), np.nan)
        self.ypr_std_dev_deg = np.full((3,), np.nan)
        self.velocity_std_dev_enu_mps = np.full((3,), np.nan)

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
                         self.ypr_deg[0], self.ypr_deg[1], self.ypr_deg[2],
                         self.velocity_enu_mps[0], self.velocity_enu_mps[1], self.velocity_enu_mps[2],
                         self.position_std_dev_ecef_m[0], self.position_std_dev_ecef_m[1],
                         self.position_std_dev_ecef_m[2],
                         self.ypr_std_dev_deg[0], self.ypr_std_dev_deg[1], self.ypr_std_dev_deg[2],
                         self.velocity_std_dev_enu_mps[0], self.velocity_std_dev_enu_mps[1],
                         self.velocity_std_dev_enu_mps[2],
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
         self.ypr_deg[0], self.ypr_deg[1], self.ypr_deg[2],
         self.velocity_enu_mps[0], self.velocity_enu_mps[1], self.velocity_enu_mps[2],
         self.position_std_dev_ecef_m[0], self.position_std_dev_ecef_m[1], self.position_std_dev_ecef_m[2],
         self.ypr_std_dev_deg[0], self.ypr_std_dev_deg[1], self.ypr_std_dev_deg[2],
         self.velocity_std_dev_enu_mps[0], self.velocity_std_dev_enu_mps[1], self.velocity_std_dev_enu_mps[2],
         self.aggregate_protection_level_m,
         self.horizontal_protection_level_m,
         self.vertical_protection_level_m) = \
            struct.unpack_from(PoseMessage._FORMAT, buffer=buffer, offset=offset)

        self.solution_type = SolutionType(solution_type_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return 2 * Timestamp.calcsize() + PoseMessage._SIZE


class SatelliteInfo:
    """!
    @brief Information about an individual satellite.
    """
    _FORMAT = '<BB?xdd'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.system = SatelliteType.UNKNOWN
        self.prn = 0
        self.used_in_solution = False
        self.azimuth_deg = np.nan
        self.elevation_deg = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        args = (int(self.system), self.prn, self.used_in_solution, self.azimuth_deg, self.elevation_deg)
        if buffer is None:
            buffer = struct.pack(SatelliteInfo._FORMAT, *args)
        else:
            struct.pack_into(SatelliteInfo._FORMAT, buffer=buffer, offset=offset, *args)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        (system_int, self.prn, self.used_in_solution, self.azimuth_deg, self.elevation_deg) = \
            struct.unpack_from(SatelliteInfo._FORMAT, buffer=buffer, offset=offset)
        self.system = SatelliteType(system_int)
        return self.calcsize()

    @classmethod
    def calcsize(cls) -> int:
        return SatelliteInfo._SIZE


class GNSSInfoMessage:
    """!
    @brief Information about the GNSS data used in the @ref PoseMessage with the corresponding timestamp.
    """
    MESSAGE_TYPE = MessageType.GNSS_INFO

    INVALID_REFERENCE_STATION = 0xFFFFFFFF

    _FORMAT = '<IddddH2x'
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

        self.svs: List[SatelliteInfo] = []

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
                         len(self.svs))
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
         num_svs) = \
            struct.unpack_from(GNSSInfoMessage._FORMAT, buffer=buffer, offset=offset)
        offset += GNSSInfoMessage._SIZE

        self.svs = []
        for i in range(num_svs):
            sv = SatelliteInfo()
            offset += sv.unpack(buffer, offset)
            self.svs.append(sv)

        return offset - initial_offset

    def calcsize(self) -> int:
        return 3 * Timestamp.calcsize() + GNSSInfoMessage._SIZE + len(self.svs) * SatelliteInfo.calcsize()
