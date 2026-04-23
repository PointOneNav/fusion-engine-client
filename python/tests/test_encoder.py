import numpy as np
import pytest

from fusion_engine_client.messages import (GNSSSignalType, GNSSSatelliteInfo, GNSSSignalInfo,
                                           GNSSSignalsMessage, PoseAuxMessage,
                                           PoseMessage, SatelliteType, Timestamp)
from fusion_engine_client.parsers import FusionEngineEncoder
from fusion_engine_client.utils import trace as logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('point_one').setLevel(logging.DEBUG)


P1_POSE_MESSAGE1 = b".1\x00\x00\xb1&\xc8\xfe\x02\x02\x10'\x00\x00\x00\x00\x8c\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\x00\x00\x00\x00\xf0?\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x08@\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f"
P1_POSE_MESSAGE2 = b".1\x00\x00\x00\xf3\xeen\x02\x02\x10'\x01\x00\x00\x00\x8c\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\x00\x00\x00\x00\xf0?\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x08@\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f"
P1_POSE_AUX_MESSAGE3 = b".1\x00\x00\xac\xa4\x08\x94\x02\x00\x13'\x02\x00\x00\x00\xa0\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f"


def test_pose_encode():
    encoder = FusionEngineEncoder()
    pose = PoseMessage()
    pose.velocity_body_mps = np.array([1.0, 2.0, 3.0])
    pose_aux = PoseAuxMessage()

    data = encoder.encode_message(pose)
    assert data == P1_POSE_MESSAGE1
    data = encoder.encode_message(pose)
    assert data == P1_POSE_MESSAGE2
    data = encoder.encode_message(pose_aux)
    assert data == P1_POSE_AUX_MESSAGE3


def test_gnss_signals_message_encode():
    message = GNSSSignalsMessage()
    message.gps_time = Timestamp(1432573739.134)
    message.gps_week = 2368
    message.gps_tow_ms = 407339134

    data = message.pack()
    assert len(data) == 32

    sats = [
        GNSSSatelliteInfo(),
        GNSSSatelliteInfo(system=SatelliteType.GPS, prn=3, elevation_deg=45.0, azimuth_deg=27.0,
                          status_flags=GNSSSatelliteInfo.STATUS_FLAG_IS_USED),
    ]

    message.sat_info = {e.get_satellite_id(): e for e in sats}
    data = message.pack()
    assert len(data) == 32 + 8 * 2

    signals = [
        GNSSSignalInfo(),
        GNSSSignalInfo(signal_type=GNSSSignalType.GPS_L1CA, prn=3, cn0_dbhz=46.75,
                       status_flags=GNSSSignalInfo.STATUS_FLAG_VALID_PR | GNSSSignalInfo.STATUS_FLAG_USED_PR),
        GNSSSignalInfo(signal_type=GNSSSignalType.GALILEO_E1BC, prn=4, cn0_dbhz=13.25,
                       status_flags=GNSSSignalInfo.STATUS_FLAG_VALID_PR),
    ]

    message.signal_info = {e.get_signal_id(): e for e in signals}
    data = message.pack()
    assert len(data) == 32 + 8 * len(sats) + 8 * len(signals)

    decoded_message = GNSSSignalsMessage()
    decoded_message.unpack(data)
    assert float(decoded_message.gps_time) == pytest.approx(1432573739.134, 1e-3)
    assert decoded_message.gps_week == 2368
    assert decoded_message.gps_tow_ms == 407339134

    # Test invalid time decoding.
    message = GNSSSignalsMessage()
    data = message.pack()

    decoded_message = GNSSSignalsMessage()
    decoded_message.unpack(data)
    assert not decoded_message.gps_time
    assert decoded_message.gps_tow_ms is None
    assert decoded_message.gps_week is None

    # It would be nice to do the following:
    #   assert list(decoded_message.sat_info.values()) == sats
    # but that is not possible because the invalid satellite/signal entries contain NANs, and NAN == NAN is always
    # false.
    #
    # IMPORTANT: However, that check actually PASSES in Python <=3.12 and FAILS in Python 3.13.
    #
    # Before Python 3.13, the @dataclass __eq__ operator was implemented as follows:
    #   (a.var1, a.var2, ...) == (b.var1, b.var2, ...)
    #
    # Tuple == comparison first checks if the elements are the same physical object in memory. If so, it assumes they
    # are equal. But in Python, math.nan (and numpy.nan) is an object, _not_ a primitive, so if any variable was set to
    # NAN, checking tuple == would return true incorrectly. In Python 3.13, they @dataclass operator was changed to the
    # following:
    #   a.var1 == b.var1 and a.var2 == b.var2 and ...
    def _is_equal(a, b):
        for k, v_a in a.__dict__.items():
            v_b = b.__dict__[k]
            if np.isnan(v_a):
                if not np.isnan(v_b):
                    return False
            elif np.isnan(v_b):
                return False
            elif v_a != v_b:
                return False
        return True
    assert all([_is_equal(a, b) for a, b in zip(decoded_message.sat_info.values(), sats)])
    assert all([_is_equal(a, b) for a, b in zip(decoded_message.signal_info.values(), signals)])
