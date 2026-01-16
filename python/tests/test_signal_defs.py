import pytest

from fusion_engine_client.messages.signal_def_gen import update_python_code, update_cpp_code
from fusion_engine_client.messages.signal_defs import *


def test_generated_code_up_to_date():
    # Check that the generated source code in src/point_one/fusion_engine/messages/signal_defs.h is up to date.
    assert not update_python_code(True)
    # Check that the generated source code in python/fusion_engine_client/messages/signal_defs.py is up to date.
    assert not update_cpp_code(True)


def test_pretty_print():
    assert pretty_print_gnss_enum(SatelliteType.GPS) == 'GPS'
    assert pretty_print_gnss_enum(SatelliteType.GALILEO) == 'Galileo'
    assert pretty_print_gnss_enum(SatelliteType.BEIDOU) == 'BeiDou'
    assert pretty_print_gnss_enum(SatelliteType.GLONASS) == 'GLONASS'

    assert pretty_print_gnss_enum(GNSSSignalType.GPS_L1CA) == 'GPS C/A'
    assert pretty_print_gnss_enum(GNSSSignalType.GPS_L1C) == 'GPS L1C'
    assert pretty_print_gnss_enum(GNSSSignalType.GPS_L1P) == 'GPS L1 P(Y)'
    assert pretty_print_gnss_enum(GNSSSignalType.GPS_L5) == 'GPS L5'
    assert pretty_print_gnss_enum(GNSSSignalType.GPS_L5_I) == 'GPS L5-I (Data)'

    assert pretty_print_gnss_enum(GNSSSignalType.GLONASS_L1CA) == 'GLONASS L1 C/A'
    assert pretty_print_gnss_enum(GNSSSignalType.GLONASS_L2CA) == 'GLONASS L2 C/A'

    assert pretty_print_gnss_enum(GNSSSignalType.GALILEO_E1BC) == 'Galileo E1-B/C'
    assert pretty_print_gnss_enum(GNSSSignalType.GALILEO_E1C) == 'Galileo E1-C (Pilot)'
    assert pretty_print_gnss_enum(GNSSSignalType.GALILEO_E5A) == 'Galileo E5a'
    assert pretty_print_gnss_enum(GNSSSignalType.GALILEO_E5A_I) == 'Galileo E5a-I (Data)'


def test_satellite_id():
    # Default invalid construction.
    sv = SatelliteID()
    assert sv.encode_hash() == INVALID_SV_HASH

    # Explicit conversion from invalid hash.
    sv = SatelliteID(sv_hash=INVALID_SV_HASH)
    assert sv.encode_hash() == INVALID_SV_HASH

    # Normal construction.
    hash = encode_signal_hash(SatelliteType.GALILEO, 5)
    sv = SatelliteID(system=SatelliteType.GALILEO, prn=5)
    assert sv.system == SatelliteType.GALILEO
    assert sv.prn == 5
    assert sv.encode_hash() == hash

    # Decode valid hash for G04.
    hash = encode_signal_hash(SatelliteType.GPS, 4)
    sv = SatelliteID(sv_hash=hash)
    assert sv.system == SatelliteType.GPS
    assert sv.prn == 4
    assert sv.encode_hash() == hash

    # Switch to another satellite.
    hash = encode_signal_hash(SatelliteType.BEIDOU, 7)
    sv.decode_hash(hash)
    assert sv.system == SatelliteType.BEIDOU
    assert sv.prn == 7
    assert sv.encode_hash() == hash

    # Specify both components and hash.
    with pytest.raises(Exception):
        sv = SatelliteID(system=SatelliteType.GPS, prn=5, sv_hash=12345)

    # Omit system.
    with pytest.raises(Exception):
        sv = SatelliteID(prn=5)

    # Omit PRN.
    with pytest.raises(Exception):
        sv = SatelliteID(system=SatelliteType.GPS)

    # Assuming SatelliteType value 15 does not exist for the tests below.
    unknown_satellite_type_value = 15
    with pytest.raises(Exception):
        SatelliteType(unknown_satellite_type_value, raise_on_unrecognized=True)

    # Check backwards compatibility support: decode a valid hash for an enum that is not yet supported by this library.
    # SatelliteType should create an enum for this.
    hash = encode_signal_hash(unknown_satellite_type_value, 3)
    sv = SatelliteID(sv_hash=hash)
    assert int(sv.system) == unknown_satellite_type_value
    assert sv.prn == 3
    assert sv.encode_hash() == hash


def test_satellite_id_operators():
    # == and !=
    assert SatelliteID() == SatelliteID()
    assert SatelliteID(SatelliteType.GPS, 3) != SatelliteID()
    assert SatelliteID() != SatelliteID(SatelliteType.GPS, 3)
    assert SatelliteID(SatelliteType.GPS, 3) == SatelliteID(SatelliteType.GPS, 3)
    assert SatelliteID(SatelliteType.GPS, 3) != SatelliteID(SatelliteType.GPS, 4)
    assert SatelliteID(SatelliteType.GPS, 3) != SatelliteID(SatelliteType.QZSS, 3)

    # <
    assert not (SatelliteID() < SatelliteID())
    assert (SatelliteID() < SatelliteID(SatelliteType.GPS, 3))
    assert not (SatelliteID(SatelliteType.GPS, 3) < SatelliteID())
    assert not (SatelliteID(SatelliteType.GPS, 3) < SatelliteID(SatelliteType.GPS, 3))
    assert (SatelliteID(SatelliteType.GPS, 3) < SatelliteID(SatelliteType.GPS, 4))
    assert not (SatelliteID(SatelliteType.GPS, 4) < SatelliteID(SatelliteType.GPS, 3))
    assert (SatelliteID(SatelliteType.GPS, 3) < SatelliteID(SatelliteType.QZSS, 3))
    assert not (SatelliteID(SatelliteType.QZSS, 3) < SatelliteID(SatelliteType.GPS, 3))

    # >
    assert not (SatelliteID() > SatelliteID())
    assert not (SatelliteID() > SatelliteID(SatelliteType.GPS, 3))
    assert (SatelliteID(SatelliteType.GPS, 3) > SatelliteID())
    assert not (SatelliteID(SatelliteType.GPS, 3) > SatelliteID(SatelliteType.GPS, 3))
    assert not (SatelliteID(SatelliteType.GPS, 3) > SatelliteID(SatelliteType.GPS, 4))
    assert (SatelliteID(SatelliteType.GPS, 4) > SatelliteID(SatelliteType.GPS, 3))
    assert not (SatelliteID(SatelliteType.GPS, 3) > SatelliteID(SatelliteType.QZSS, 3))
    assert (SatelliteID(SatelliteType.QZSS, 3) > SatelliteID(SatelliteType.GPS, 3))

    # <=
    assert (SatelliteID() <= SatelliteID())
    assert (SatelliteID() <= SatelliteID(SatelliteType.GPS, 3))
    assert not (SatelliteID(SatelliteType.GPS, 3) <= SatelliteID())
    assert (SatelliteID(SatelliteType.GPS, 3) <= SatelliteID(SatelliteType.GPS, 3))
    assert (SatelliteID(SatelliteType.GPS, 3) <= SatelliteID(SatelliteType.GPS, 4))
    assert not (SatelliteID(SatelliteType.GPS, 4) <= SatelliteID(SatelliteType.GPS, 3))
    assert (SatelliteID(SatelliteType.GPS, 3) <= SatelliteID(SatelliteType.QZSS, 3))
    assert not (SatelliteID(SatelliteType.QZSS, 3) <= SatelliteID(SatelliteType.GPS, 3))

    # >=
    assert (SatelliteID() >= SatelliteID())
    assert not (SatelliteID() >= SatelliteID(SatelliteType.GPS, 3))
    assert (SatelliteID(SatelliteType.GPS, 3) >= SatelliteID())
    assert (SatelliteID(SatelliteType.GPS, 3) >= SatelliteID(SatelliteType.GPS, 3))
    assert not (SatelliteID(SatelliteType.GPS, 3) >= SatelliteID(SatelliteType.GPS, 4))
    assert (SatelliteID(SatelliteType.GPS, 4) >= SatelliteID(SatelliteType.GPS, 3))
    assert not (SatelliteID(SatelliteType.GPS, 3) >= SatelliteID(SatelliteType.QZSS, 3))
    assert (SatelliteID(SatelliteType.QZSS, 3) >= SatelliteID(SatelliteType.GPS, 3))


def test_satellite_id_str():
    assert SatelliteID(SatelliteType.GPS, 3).to_string(short=False) == 'GPS PRN 3'
    assert SatelliteID(SatelliteType.GPS, 3).to_string(short=True) == 'G03'
    assert SatelliteID(SatelliteType.GPS, 0).to_string(short=False) == 'GPS PRN ?'
    assert SatelliteID(SatelliteType.GPS, 0).to_string(short=True) == 'G??'

    assert SatelliteID(SatelliteType.UNKNOWN, 3).to_string(short=False) == 'UNKNOWN PRN 3'
    assert SatelliteID(SatelliteType.UNKNOWN, 3).to_string(short=True) == 'U03'
    assert SatelliteID().to_string(short=False) == 'Invalid Satellite'
    assert SatelliteID().to_string(short=True) == 'U??'


def test_signal_id():
    # Default invalid construction.
    sv = SignalID()
    assert sv.encode_hash() == INVALID_SIGNAL_HASH

    # Explicit conversion from invalid hash.
    signal = SignalID(signal_hash=INVALID_SIGNAL_HASH)
    assert signal.encode_hash() == INVALID_SIGNAL_HASH

    # Normal construction.
    hash = encode_signal_hash(GNSSSignalType.GALILEO_E5B_I, 5)
    signal = SignalID(signal_type=GNSSSignalType.GALILEO_E5B_I, prn=5)
    assert signal.system == SatelliteType.GALILEO
    assert signal.signal_type == GNSSSignalType.GALILEO_E5B_I
    assert signal.get_signal_name() == GalileoSignalName.E5B
    assert signal.prn == 5
    assert signal.encode_hash() == hash

    # Decode valid hash for G04 C/A.
    hash = encode_signal_hash(GNSSSignalType.GPS_L1CA, 4)
    signal = SignalID(signal_hash=hash)
    assert signal.system == SatelliteType.GPS
    assert signal.signal_type == GNSSSignalType.GPS_L1CA
    assert signal.get_signal_name() == GPSSignalName.L1CA
    assert signal.prn == 4
    assert signal.encode_hash() == hash

    # Switch to another signal.
    hash = encode_signal_hash(GNSSSignalType.BEIDOU_B1I, 7)
    signal.decode_hash(hash)
    assert signal.system == SatelliteType.BEIDOU
    assert signal.signal_type == GNSSSignalType.BEIDOU_B1I
    assert signal.get_signal_name() == BeiDouSignalName.B1I
    assert signal.prn == 7
    assert signal.encode_hash() == hash

    # Specify both components and hash.
    with pytest.raises(Exception):
        signal = SignalID(signal_type=GNSSSignalType.GPS_L1CA, prn=5, signal_hash=12345)

    # Omit signal type.
    with pytest.raises(Exception):
        signal = SignalID(prn=5)

    # Omit PRN.
    with pytest.raises(Exception):
        signal = SignalID(signal_type=GNSSSignalType.GPS_L1CA)

    # Assuming SatelliteType value 15 does not exist for the tests below.
    unknown_satellite_type_value = 15
    with pytest.raises(Exception):
        SatelliteType(unknown_satellite_type_value, raise_on_unrecognized=True)

    unknown_signal_name_value = 1
    unknown_signal_type_value = ((unknown_satellite_type_value << 12) |
                                 (int(FrequencyBand.L1) << 5) |
                                 (unknown_signal_name_value << 2) |
                                 (int(GNSSComponent.COMBINED) << 0))
    with pytest.raises(Exception):
        GNSSSignalType(unknown_signal_type_value, raise_on_unrecognized=True)

    # Check backwards compatibility support: decode a valid hash for an enum that is not yet supported by this library.
    # SatelliteType should create an enum for this.
    hash = (unknown_signal_type_value << 16) | 3
    signal = SignalID(signal_hash=hash)
    assert int(signal.system) == unknown_satellite_type_value
    assert int(signal.signal_type) == unknown_signal_type_value
    assert signal.prn == 3
    assert signal.encode_hash() == hash


def test_signal_id_operators():
    # == and !=
    assert SignalID() == SignalID()
    assert SignalID(GNSSSignalType.GPS_L1CA, 3) != SignalID()
    assert SignalID() != SignalID(GNSSSignalType.GPS_L1CA, 3)
    assert SignalID(GNSSSignalType.GPS_L1CA, 3) == SignalID(GNSSSignalType.GPS_L1CA, 3)
    assert SignalID(GNSSSignalType.GPS_L1CA, 3) != SignalID(GNSSSignalType.GPS_L5, 3)
    assert SignalID(GNSSSignalType.GPS_L1CA, 3) != SignalID(GNSSSignalType.GPS_L1CA, 4)
    assert SignalID(GNSSSignalType.GPS_L1CA, 3) != SignalID(GNSSSignalType.QZSS_L1CA, 3)

    # <
    assert not (SignalID() < SignalID())
    assert (SignalID() < SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 3) < SignalID())
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 3) < SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert (SignalID(GNSSSignalType.GPS_L1CA, 3) < SignalID(GNSSSignalType.GPS_L5, 3))
    assert not (SignalID(GNSSSignalType.GPS_L5, 3) < SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert (SignalID(GNSSSignalType.GPS_L1CA, 3) < SignalID(GNSSSignalType.GPS_L1CA, 4))
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 4) < SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert (SignalID(GNSSSignalType.GPS_L1CA, 3) < SignalID(GNSSSignalType.QZSS_L1CA, 3))
    assert not (SignalID(GNSSSignalType.QZSS_L1CA, 3) < SignalID(GNSSSignalType.GPS_L1CA, 3))

    # >
    assert not (SignalID() > SignalID())
    assert not (SignalID() > SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert (SignalID(GNSSSignalType.GPS_L1CA, 3) > SignalID())
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 3) > SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 3) > SignalID(GNSSSignalType.GPS_L5, 3))
    assert (SignalID(GNSSSignalType.GPS_L5, 3) > SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 3) > SignalID(GNSSSignalType.GPS_L1CA, 4))
    assert (SignalID(GNSSSignalType.GPS_L1CA, 4) > SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 3) > SignalID(GNSSSignalType.QZSS_L1CA, 3))
    assert (SignalID(GNSSSignalType.QZSS_L1CA, 3) > SignalID(GNSSSignalType.GPS_L1CA, 3))

    # <=
    assert (SignalID() <= SignalID())
    assert (SignalID() <= SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 3) <= SignalID())
    assert (SignalID(GNSSSignalType.GPS_L1CA, 3) <= SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert (SignalID(GNSSSignalType.GPS_L1CA, 3) <= SignalID(GNSSSignalType.GPS_L5, 3))
    assert not (SignalID(GNSSSignalType.GPS_L5, 3) <= SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert (SignalID(GNSSSignalType.GPS_L1CA, 3) <= SignalID(GNSSSignalType.GPS_L1CA, 4))
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 4) <= SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert (SignalID(GNSSSignalType.GPS_L1CA, 3) <= SignalID(GNSSSignalType.QZSS_L1CA, 3))
    assert not (SignalID(GNSSSignalType.QZSS_L1CA, 3) <= SignalID(GNSSSignalType.GPS_L1CA, 3))

    # >=
    assert (SignalID() >= SignalID())
    assert not (SignalID() >= SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert (SignalID(GNSSSignalType.GPS_L1CA, 3) >= SignalID())
    assert (SignalID(GNSSSignalType.GPS_L1CA, 3) >= SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 3) >= SignalID(GNSSSignalType.GPS_L5, 3))
    assert (SignalID(GNSSSignalType.GPS_L5, 3) >= SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 3) >= SignalID(GNSSSignalType.GPS_L1CA, 4))
    assert (SignalID(GNSSSignalType.GPS_L1CA, 4) >= SignalID(GNSSSignalType.GPS_L1CA, 3))
    assert not (SignalID(GNSSSignalType.GPS_L1CA, 3) >= SignalID(GNSSSignalType.QZSS_L1CA, 3))
    assert (SignalID(GNSSSignalType.QZSS_L1CA, 3) >= SignalID(GNSSSignalType.GPS_L1CA, 3))


def test_signal_id_str():
    assert SignalID(GNSSSignalType.GPS_L1CA, 3).to_string(short=False) == 'GPS C/A PRN 3'
    assert SignalID(GNSSSignalType.GPS_L1CA, 3).to_string(short=True) == 'G03 C/A'
    assert SignalID(GNSSSignalType.GPS_L1CA, 0).to_string(short=False) == 'GPS C/A PRN ?'
    assert SignalID(GNSSSignalType.GPS_L1CA, 0).to_string(short=True) == 'G?? C/A'

    assert SignalID(GNSSSignalType.UNKNOWN, 3).to_string(short=False) == 'Unknown Signal PRN 3'
    assert SignalID(GNSSSignalType.UNKNOWN, 3).to_string(short=True) == 'U03 UNKNOWN'
    assert SignalID().to_string(short=False) == 'Invalid Signal'
    assert SignalID().to_string(short=True) == 'U?? UNKNOWN'
