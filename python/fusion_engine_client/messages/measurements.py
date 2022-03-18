import numpy as np

from .defs import *


class IMUMeasurement(MessagePayload):
    """!
    @brief IMU sensor measurement data.
    """
    MESSAGE_TYPE = MessageType.IMU_MEASUREMENT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<3d 3d 3d 3d')

    def __init__(self):
        self.p1_time = Timestamp()

        self.accel_mps2 = np.full((3,), np.nan)
        self.accel_std_mps2 = np.full((3,), np.nan)

        self.gyro_rps = np.full((3,), np.nan)
        self.gyro_std_rps = np.full((3,), np.nan)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        offset += self.pack_values(
            self._STRUCT, buffer, offset,
            self.accel_mps2,
            self.accel_std_mps2,
            self.gyro_rps,
            self.gyro_std_rps)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)

        offset += self.unpack_values(
            self._STRUCT, buffer, offset,
            self.accel_mps2,
            self.accel_std_mps2,
            self.gyro_rps,
            self.gyro_std_rps)

        return offset - initial_offset

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.p1_time)

    def __str__(self):
        return 'IMU Measurement @ %s' % str(self.p1_time)

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'accel_mps2': np.array([m.accel_mps2 for m in messages]).T,
            'accel_std_mps2': np.array([m.accel_std_mps2 for m in messages]).T,
            'gyro_rps': np.array([m.gyro_rps for m in messages]).T,
            'gyro_std_rps': np.array([m.gyro_std_rps for m in messages]).T,
        }
        return result

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp.calcsize() + cls._STRUCT.size
