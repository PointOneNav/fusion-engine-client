import struct

import numpy as np

from .defs import *


class CovarianceType(IntEnum):
    COVARIANCE_TYPE_UNKNOWN = 0
    COVARIANCE_TYPE_APPROXIMATED = 1
    COVARIANCE_TYPE_DIAGONAL_KNOWN = 2
    COVARIANCE_TYPE_KNOWN = 3


class PoseMessage(MessagePayload):
    """!
    @brief ROS `Pose` message (@ref MessageType::ROS_POSE)

    The relative change in ENU position since the time of the first @ref PoseMessage, resolved in the local ENU frame at
    the time of the first @ref PoseMessage.
    """
    MESSAGE_TYPE = MessageType.ROS_POSE
    MESSAGE_VERSION = 0

    _FORMAT = '< 3d 4d'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        # The time of the message, in P1 time (beginning at power-on)
        self.p1_time = Timestamp()
        # relative ENU position (see ros.h messages)
        self.position_rel_m = np.full((3,), np.nan)
        # The platform orientation, represented as a quaternion with the scalar
        # component last (x, y, z, w)
        self.orientation = np.full((4,), np.nan)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        struct.pack_into(PoseMessage._FORMAT, buffer, offset,
                         self.position_rel_m[0], self.position_rel_m[1], self.position_rel_m[2],
                         self.orientation[0], self.orientation[1], self.orientation[2], self.orientation[3])

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)
        (self.position_rel_m[0], self.position_rel_m[1], self.position_rel_m[2],
         self.orientation[0], self.orientation[1], self.orientation[2], self.orientation[3]) = \
            struct.unpack_from(PoseMessage._FORMAT,
                               buffer=buffer, offset=offset)
        offset += PoseMessage._SIZE
        return offset - initial_offset

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.p1_time)

    def __str__(self):
        string = 'ROS Pose message @ P1 time %s\n' % str(self.p1_time)
        string += '  Position : %.6f, %.6f, %.6f \n' % tuple(self.position_rel_m)
        string += '  Orientation: %.12f, %.12f, %.12f, %.12f \n' % tuple(self.orientation)
        return string

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp.calcsize() + PoseMessage._SIZE

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'position_rel_m': np.array([m.position_rel_m for m in messages]).T,
            'orientation': np.array([m.orientation for m in messages]).T,
        }
        return result


class GPSFixMessage(MessagePayload):
    """!
    @brief ROS `GPSFix` message (MessageType::ROS_GPS_FIX).
    """
    MESSAGE_TYPE = MessageType.ROS_GPS_FIX
    MESSAGE_VERSION = 0

    _FORMAT = '< ddd ddd ddd d ddddd dddddddddd 9d B 3B'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.p1_time = Timestamp()
        # Geodetic Position (expressed using the WGS-84 ellipsoid)
        # Geodetic latitude (in degrees)
        self.latitude_deg = np.nan
        # Geodetic longitude (in degrees)
        self.longitude_deg = np.nan
        # Altitude above the ellipsoid (in meters)
        self.altitude_m = np.nan

        # Velocity
        # The vehicle direction from north (in degrees)
        self.track_deg = np.nan
        # The vehicle ground speed (in meters/second)
        self.speed_mps = np.nan
        # The vehicle vertical speed (in meters/second)
        self.climb_mps = np.nan

        # Vehicle Orientation (not supported)
        self.pitch_deg = np.nan
        self.roll_deg = np.nan
        self.dip_deg = np.nan

        # The GPS time of the message (in seconds), referenced to 1980/1/6
        self.gps_time = np.nan

        # Dilution Of Precision
        self.gdop = np.nan  # Geometric (position + time) DOP
        self.pdop = np.nan  # Positional (3D) DOP
        self.hdop = np.nan  # Horizontal DOP
        self.vdop = np.nan  # Vertical DOP
        self.tdop = np.nan  # Time DOP

        # Measurement Uncertainty (95% Confidence)
        # Spherical position uncertainty (in meters) [epe]
        self.err_3d_m = np.nan
        # Horizontal position uncertainty (in meters) [eph]
        self.err_horiz_m = np.nan
        # Vertical position uncertainty (in meters) [epv]
        self.err_vert_m = np.nan
        self.err_track_deg = np.nan  # Track uncertainty (in degrees) [epd]
        # Ground speed uncertainty (in meters/second) [eps]
        self.err_speed_mps = np.nan
        # Vertical speed uncertainty (in meters/second) [epc]
        self.err_climb_mps = np.nan
        self.err_time_sec = np.nan  # Time uncertainty (in seconds) [ept]
        self.err_pitch_deg = np.nan  # Pitch uncertainty (in degrees)
        self.err_roll_deg = np.nan  # Roll uncertainty (in degrees)
        self.err_dip_deg = np.nan   # Dip uncertainty (in degrees)

        # Position Covariance
        """
            The 3x3 position covariance matrix (in m^2), resolved in the local ENU
            frame. Values are stored in row-major order.
        """
        self.position_covariance_m2 = np.full((9,), np.nan)
        # The method in which @ref position_covariance_m2 was populated
        self.position_covariance_type = CovarianceType.COVARIANCE_TYPE_UNKNOWN

        self.reserved = np.full((3,), 0, np.uint8)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        struct.pack_into(GPSFixMessage._FORMAT, buffer, offset,
                         self.latitude_deg,
                         self.longitude_deg,
                         self.altitude_m,
                         self.track_deg,
                         self.speed_mps,
                         self.climb_mps,
                         self.pitch_deg,
                         self.roll_deg,
                         self.dip_deg,
                         self.gps_time,
                         self.gdop,
                         self.pdop,
                         self.hdop,
                         self.vdop,
                         self.tdop,
                         self.err_3d_m,
                         self.err_horiz_m,
                         self.err_vert_m,
                         self.err_track_deg,
                         self.err_speed_mps,
                         self.err_climb_mps,
                         self.err_time_sec,
                         self.err_pitch_deg,
                         self.err_roll_deg,
                         self.err_dip_deg,
                         self.position_covariance_m2[0], self.position_covariance_m2[1], self.position_covariance_m2[2],
                         self.position_covariance_m2[3], self.position_covariance_m2[4], self.position_covariance_m2[5],
                         self.position_covariance_m2[6], self.position_covariance_m2[7], self.position_covariance_m2[8],
                         self.position_covariance_type,
                         self.reserved[0], self.reserved[1], self.reserved[2])

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)
        (self.latitude_deg,
         self.longitude_deg,
         self.altitude_m,
         self.track_deg,
         self.speed_mps,
         self.climb_mps,
         self.pitch_deg,
         self.roll_deg,
         self.dip_deg,
         self.gps_time,
         self.gdop,
         self.pdop,
         self.hdop,
         self.vdop,
         self.tdop,
         self.err_3d_m,
         self.err_horiz_m,
         self.err_vert_m,
         self.err_track_deg,
         self.err_speed_mps,
         self.err_climb_mps,
         self.err_time_sec,
         self.err_pitch_deg,
         self.err_roll_deg,
         self.err_dip_deg,
         self.position_covariance_m2[0], self.position_covariance_m2[1], self.position_covariance_m2[2],
         self.position_covariance_m2[3], self.position_covariance_m2[4], self.position_covariance_m2[5],
         self.position_covariance_m2[6], self.position_covariance_m2[7], self.position_covariance_m2[8],
         self.position_covariance_type,
         self.reserved[0], self.reserved[1], self.reserved[2]) = \
            struct.unpack_from(GPSFixMessage._FORMAT,
                               buffer=buffer, offset=offset)
        offset += GPSFixMessage._SIZE
        return offset - initial_offset

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.p1_time)

    def __str__(self):
        string = 'ROS GPSFix message @ P1 time %s\n' % str(self.p1_time)
        string += '  Position : %.8f, %.8f, %.2f \n' % (
            self.latitude_deg, self.longitude_deg, self.altitude_m)
        string += '  Velocity: %.6f, %.6f, %.6f\n' % (
            self.track_deg, self.speed_mps, self.climb_mps)
        return string

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp.calcsize() + GPSFixMessage._SIZE


class IMUMessage(MessagePayload):
    """!
    @brief ROS `Imu` message (@ref MessageType::ROS_IMU)
    """
    MESSAGE_TYPE = MessageType.ROS_IMU
    MESSAGE_VERSION = 0

    _FORMAT = '< 4d 9d 3d 9d 3d 9d'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.p1_time = Timestamp()
        # The platform orientation, represented as a quaternion with the scalar
        # component last (x, y, z, w)
        self.orientation = np.full((4,), 0.0)
        # Orientation covariance matrix. Set to -1 if not available
        self.orientation_covariance = np.full((9,), -1)
        # Vehicle x/y/z rate of rotation (in radians/second), resolved in the body
        # frame
        self.angular_velocity_rps = np.full((3,), 0.0)
        # Vehicle rate of rotation covariance matrix. Set to -1 if not available
        self.angular_velocity_covariance = np.full((9,), -1)
        # Vehicle x/y/z linear acceleration (in meters/second^2), resolved in the
        # body frame
        self.acceleration_mps2 = np.full((3,), 0.0)
        # Vehicle x/y/z acceleration covariance matrix. Set to -1 if not available
        self.acceleration_covariance = np.full((9,), -1)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        struct.pack_into(
            IMUMessage._FORMAT, buffer, offset,
            self.orientation[0], self.orientation[1], self.orientation[2], self.orientation[3],
            self.orientation_covariance[0], self.orientation_covariance[1], self.orientation_covariance[2],
            self.orientation_covariance[3], self.orientation_covariance[4], self.orientation_covariance[5],
            self.orientation_covariance[6], self.orientation_covariance[7], self.orientation_covariance[8],
            self.angular_velocity_rps[0], self.angular_velocity_rps[1], self.angular_velocity_rps[2],
            self.angular_velocity_covariance[0], self.angular_velocity_covariance[1], self.angular_velocity_covariance[2],  # noqa
            self.angular_velocity_covariance[3], self.angular_velocity_covariance[4], self.angular_velocity_covariance[5],  # noqa
            self.angular_velocity_covariance[6], self.angular_velocity_covariance[7], self.angular_velocity_covariance[8],  # noqa
            self.acceleration_mps2[0], self.acceleration_mps2[1], self.acceleration_mps2[2],
            self.acceleration_covariance[0], self.acceleration_covariance[1], self.acceleration_covariance[2],
            self.acceleration_covariance[3], self.acceleration_covariance[4], self.acceleration_covariance[5],
            self.acceleration_covariance[6], self.acceleration_covariance[7], self.acceleration_covariance[8],
            )

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)
        (self.orientation[0], self.orientation[1], self.orientation[2], self.orientation[3],
         self.orientation_covariance[0], self.orientation_covariance[1], self.orientation_covariance[2],
         self.orientation_covariance[3], self.orientation_covariance[4], self.orientation_covariance[5],
         self.orientation_covariance[6], self.orientation_covariance[7], self.orientation_covariance[8],
         self.angular_velocity_rps[0], self.angular_velocity_rps[1], self.angular_velocity_rps[2],
         self.angular_velocity_covariance[0], self.angular_velocity_covariance[1], self.angular_velocity_covariance[2],
         self.angular_velocity_covariance[3], self.angular_velocity_covariance[4], self.angular_velocity_covariance[5],
         self.angular_velocity_covariance[6], self.angular_velocity_covariance[7], self.angular_velocity_covariance[8],
         self.acceleration_mps2[0], self.acceleration_mps2[1], self.acceleration_mps2[2],
         self.acceleration_covariance[0], self.acceleration_covariance[1], self.acceleration_covariance[2],
         self.acceleration_covariance[3], self.acceleration_covariance[4], self.acceleration_covariance[5],
         self.acceleration_covariance[6], self.acceleration_covariance[7], self.acceleration_covariance[8],
         ) = \
            struct.unpack_from(IMUMessage._FORMAT,
                               buffer=buffer, offset=offset)
        offset += IMUMessage._SIZE
        return offset - initial_offset

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.p1_time)

    def __str__(self):
        string = 'ROS IMU message @ P1 time %s\n' % str(self.p1_time)
        string += '  Orientation: %.6f, %.6f, %.6f, %.6f \n' % tuple(
            self.orientation)
        string += '  Angular Velocity: %.6f, %.6f, %.6f \n' % tuple(
            self.angular_velocity_rps)
        string += '  Acceleration: %.6f, %.6f, %.6f \n' % tuple(
            self.acceleration_mps2)
        return string

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp.calcsize() + IMUMessage._SIZE
