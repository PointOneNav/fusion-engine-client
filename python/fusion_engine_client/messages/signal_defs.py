import functools
import re
from typing import NamedTuple, Optional, TypeAlias, TypeVar, Union

import numpy as np

from ..utils.enum_utils import IntEnum, enum_bitmask


############################################################################
## Signal Type Component Enums
############################################################################

##
# @brief System/constellation type definitions.
#
# For some purposes, this enum may be used as part of a bitmask. See
# @ref gnss_enums_to_bitmasks.
#
# This needs to be packed into 4 bits so no values above 15 are allowed.
class SatelliteType(IntEnum):
    UNKNOWN = 0
    GPS = 1
    GLONASS = 2
    LEO = 3
    GALILEO = 4
    BEIDOU = 5
    QZSS = 6
    MIXED = 7
    SBAS = 8
    IRNSS = 9


SatelliteTypeChar = {
    SatelliteType.UNKNOWN: 'U',
    SatelliteType.GPS: 'G',
    SatelliteType.GLONASS: 'R',
    SatelliteType.LEO: 'L',
    SatelliteType.GALILEO: 'E',
    SatelliteType.BEIDOU: 'C',
    SatelliteType.QZSS: 'J',
    SatelliteType.MIXED: 'M',
    SatelliteType.SBAS: 'S',
    SatelliteType.IRNSS: 'I'
}

SatelliteTypeCharReverse = {v: k for k, v in SatelliteTypeChar.items()}


@enum_bitmask(SatelliteType)
class SatelliteTypeMask:
    ALL = 0xFFFF


class SignalType(IntEnum):
    UNKNOWN = 0


## @brief GNSS frequency band definitions.
#
# A frequency band generally includes multiple GNSS carrier frequencies and
# signal types, which can usually be captured by a single antenna element.
# For example, an L1 antenna typically has sufficient bandwidth to capture
# signals on the BeiDou B1I (1561.098 MHz), GPS L1 (1575.42 MHz), and GLONASS G1
# (1602.0 MHz) frequencies.
#
# For some purposes, this enum may be used as part of a bitmask. See
# @ref gnss_enums_to_bitmasks.
#
# This needs to be packed into 4 bits so no values about 15 are allowed.
class FrequencyBand(IntEnum):
    ## ~L1 = 1561.098 MHz (B1) -> 1602.0 (G1)
    # Includes: GPS L1, Galileo E1, BeiDou B1I (and B1C == L1), GLONASS G1
    L1 = 0
    ## ~L2 = 1202.025 MHz (G3) -> 1248.06 (G2)
    ## Includes: GPS L2, Galileo E5b, BeiDou B2I, GLONASS G2 & G3
    L2 = 1
    ##
    # ~L5 = 1176.45 MHz (L5)
    # Includes: GPS L5, Galileo E5a, BeiDou B2a, IRNSS L5
    L5 = 2
    ## ~L6 = 1268.52 MHz (B3) -> 1278.75 MHz (L6)
    # Includes: Galileo E6, BeiDou B3, QZSS L6
    L6 = 3
    ## ~(L1 - L2) = 296.67 MHz (QZSS L6) -> 373.395 MHz (G3)
    L1_L2_WIDE_LANE = 4
    ## ~(L1 - L5) = 398.97 MHz (L5)
    L1_L5_WIDE_LANE = 5
    ## S band 2.0 -> 4.0 GHz
    # IRNSS S band is 2492.028 MHz
    S = 6


@enum_bitmask(FrequencyBand)
class FrequencyBandMask:
    ALL = 0xFFFF


_SHORT_FORMAT = re.compile(r'([%s])(\d+)(?:\s+(\w+))?' % ''.join(SatelliteTypeCharReverse.keys()))
_LONG_FORMAT = re.compile(r'(\w+)(?:\s+(\w+))(?:\s+PRN\s+(\d+))?')

##
# @brief Groupings encapsulating the form of the signal broadcast by a
#        particular constellation.
#
# This needs to be packed into 3 bits so no values above 7 are allowed.
class SignalName(IntEnum):
    pass


##
# @brief The name of a signal from a GPS satellite.
#
# For some purposes, this enum may be used as part of a bitmask. See
# @ref gnss_enums_to_bitmasks.
#
# This needs to be packed into 3 bits so no values above 7 are allowed.
class GPSSignalName(SignalName):
    L1CA = 0
    L1P = 1
    L1C = 2
    L2C = 3
    L2P = 4
    L5 = 5


@enum_bitmask(GPSSignalName)
class GPSSignalNameMask:
    ALL = 0xFF

##
# @brief The name of a signal from a GLONASS satellite.
#
# For some purposes, this enum may be used as part of a bitmask. See
# @ref gnss_enums_to_bitmasks.
#
# This needs to be packed into 3 bits so no values above 7 are allowed.
class GLONASSSignalName(SignalName):
    L1CA = 0
    L1P = 1
    L2CA = 2
    L2P = 3


@enum_bitmask(GPSSignalName)
class GLONASSSignalNameMask:
    ALL = 0xFF


##
# @brief The name of a signal from a Galileo satellite.
#
# For some purposes, this enum may be used as part of a bitmask. See
# @ref gnss_enums_to_bitmasks.
#
# This needs to be packed into 3 bits so no values above 7 are allowed.
class GalileoSignalName(SignalName):
    E1A = 0
    E1BC = 1
    E5A = 2
    E5B = 3
    E6A = 4
    E6BC = 5


@enum_bitmask(GPSSignalName)
class GalileoSignalNameMask:
    ALL = 0xFF


##
# @brief The name of a signal from a BeiDou satellite.
#
# For some purposes, this enum may be used as part of a bitmask. See
# @ref gnss_enums_to_bitmasks.
#
# This needs to be packed into 3 bits so no values above 7 are allowed.
class BeiDouSignalName(SignalName):
    B1I = 0
    B1C = 1
    B2I = 2
    B2B = 3
    B2A = 4
    B3I = 5


@enum_bitmask(GPSSignalName)
class BeiDouSignalNameMask:
    ALL = 0xFF


##
# @brief The name of a signal from a SBAS satellite.
#
# For some purposes, this enum may be used as part of a bitmask. See
# @ref gnss_enums_to_bitmasks.
#
# This needs to be packed into 3 bits so no values above 7 are allowed.
class SBASSignalName(SignalName):
    L1CA = 0
    L5 = 1


@enum_bitmask(GPSSignalName)
class BeiDouSignalNameMask:
    ALL = 0xFF


##
# @brief The name of a signal from a QZSS satellite.
#
# For some purposes, this enum may be used as part of a bitmask. See
# @ref gnss_enums_to_bitmasks.
#
# This needs to be packed into 3 bits so no values above 7 are allowed.
class QZSSSignalName(SignalName):
    L1CA = 0
    L1C = 1
    L2C = 2
    L5 = 3
    L6 = 4


@enum_bitmask(GPSSignalName)
class QZSSSignalNameMask:
    ALL = 0xFF


##
# @brief The component being tracked for signals that have separate data and
#        pilot components.
#
# This needs to be packed into 2 bits so no values above 3 are allowed.
class GNSSComponent(IntEnum):
    COMBINED = 0
    DATA = 1
    PILOT = 2

############################################################################
## INTERNAL HELPER FUNCTIONS
############################################################################


class _BitPacking(NamedTuple):
    bit_offset: int
    bit_len: int


## This defines the bit packing for the component values in @ref GNSSSignalType
_GNSS_SIGNAL_TYPE_PARTS = {
    SatelliteType: _BitPacking(12, 4),
    # Reserved:    _BitPacking(10, 2),
    FrequencyBand: _BitPacking(6, 4),
    # Reserved:    _BitPacking(5, 1),
    SignalName: _BitPacking(2, 3),
    GNSSComponent: _BitPacking(0, 2),
}

_SIGNAL_NAME_ENUM_MAP = {
    SatelliteType.GPS: GPSSignalName,
    SatelliteType.GLONASS: GLONASSSignalName,
    SatelliteType.GALILEO: GalileoSignalName,
    SatelliteType.BEIDOU: BeiDouSignalName,
    SatelliteType.SBAS: SBASSignalName,
    SatelliteType.QZSS: QZSSSignalName,
}

_GNSSSignalPartType: TypeAlias = SatelliteType | FrequencyBand | SignalName | GNSSComponent


def _get_gnss_enum_bit_packing(cls: type[_GNSSSignalPartType]) -> _BitPacking:
    '''!
    Get the bit packing for an enum component of @ref GNSSSignalType
    '''
    cls = SignalName if issubclass(cls, SignalName) else cls
    return _GNSS_SIGNAL_TYPE_PARTS[cls]


_T = TypeVar('_T', SatelliteType, FrequencyBand, SignalName, GNSSComponent)


def _get_signal_part(signal: 'GNSSSignalType', cls: type[_T], raise_on_unrecognized: bool = True) -> _T:
    '''!
    Return the value for an enum component of @ref GNSSSignalType

    @param signal The full signal type to get a component from.
    @param cls The enum class to get the value for (e.g., @ref SatelliteType, @ref GalileoSignalName).
    @param raise_on_unrecognized If `False`, insert a new enum element on unrecognized values. Otherwise, raise an
           exception.

    @return The component enum value.
    '''
    bit_packing = _get_gnss_enum_bit_packing(cls)
    value = (int(signal) >> bit_packing.bit_offset) & ((1 << bit_packing.bit_len) - 1)
    return cls(value, raise_on_unrecognized=raise_on_unrecognized)


def _shift_enum_value(value: _GNSSSignalPartType) -> int:
    '''!
    Get the integer value for a component of @ref GNSSSignalType shifted into the bits it will occupy in the @ref
    GNSSSignalType value.
s
    @param value The value of the enum component.

    @return The shifted value.
    '''
    return int(value) << _get_gnss_enum_bit_packing(type(value)).bit_offset


def _get_pretty_gnss_signal_type(name: str, sv_type: SatelliteType, signal_name: SignalName,
                                 component: GNSSComponent, omit_component_hint: bool = False) -> str:
    '''!
    Get a human readable string to describe the components of a GNSSSignalType value.
    '''
    if sv_type is None:
        sat_str = ''
    else:
        sat_str = pretty_print_gnss_enum(sv_type) + ' '
    signal_str = pretty_print_gnss_enum(signal_name)
    component_str = ''
    if component != GNSSComponent.COMBINED:
        if signal_str.endswith('B/C'):
            end_char = 'B' if component == GNSSComponent.DATA else 'C'
            signal_str = signal_str[:-3] + end_char
        if name[-2] == '_' and name[-1] in ('D', 'P', 'I', 'Q', 'M', 'L'):
            signal_str += '-' + name[-1]
        if not omit_component_hint:
            component_str = f' ({pretty_print_gnss_enum(component)})'
    return sat_str + signal_str + component_str


def to_signal_val(sv_type: SatelliteType, freq_band: FrequencyBand, signal_name: SignalName,
                  component=GNSSComponent.COMBINED) -> int:
    '''!
    Combine the component enums into the integer value used in @ref GNSSSignalType.

    @note This is used in the definition of @ref GNSSSignalType. This means that this function and any functions it
          references must be defined earlier in the file then @ref GNSSSignalType.
    '''
    return (_shift_enum_value(sv_type) | _shift_enum_value(freq_band) |
            _shift_enum_value(signal_name) | _shift_enum_value(component))


def to_signal_type(sv_type: SatelliteType, freq_band: FrequencyBand, signal_name: SignalName,
                   component=GNSSComponent.COMBINED) -> 'GNSSSignalType':
    '''!
    Combine the component enums into the @ref GNSSSignalType.

    @warning This will throw an exception if this combination of values isn't defined in @ref GNSSSignalType.
    '''
    return GNSSSignalType(to_signal_val(sv_type, freq_band, signal_name, component))

##
# @brief Representation of the combination of GNSS constellation, signal type,
#        and component being tracked (pilot/data).
#
# This `enum` is organized as a bitmask, defined as follows:
# ```
# { SatelliteType (4b), Reserved (2b), FrequencyBand (4b), Reserved (1b),
#   *SignalName (3b), GNSSComponent (2b) }
# ```
#
# The `*SignalName` mappings are specific to each @ref SatelliteType. For
# example, use @ref GPSSignalName for GPS signal definitions.
#
# Each enumeration entry uniquely identifies an individual GNSS signal being
# tracked by the GNSS receiver. For signals that have separate data and pilot
# components, the entry indicates which component is being tracked.
class GNSSSignalType(IntEnum):
    ## > Start Autogenerated Types (See python/fusion_engine_client/messages/signal_def_gen.py)

    UNKNOWN = 0

    ############################################################################
    ## GPS
    ############################################################################

    ## L1 Band

    ### GPS C/A: 4096 (0x1000)
    GPS_L1CA = to_signal_val(SatelliteType.GPS, FrequencyBand.L1,
                             GPSSignalName.L1CA, GNSSComponent.COMBINED)
    ### GPS L1 P(Y): 4100 (0x1004)
    GPS_L1P = to_signal_val(SatelliteType.GPS, FrequencyBand.L1,
                            GPSSignalName.L1P, GNSSComponent.COMBINED)
    ### GPS L1C: 4104 (0x1008)
    GPS_L1C = to_signal_val(SatelliteType.GPS, FrequencyBand.L1,
                            GPSSignalName.L1C, GNSSComponent.COMBINED)
    ### GPS L1C-D (Data): 4105 (0x1009)
    GPS_L1C_D = to_signal_val(SatelliteType.GPS, FrequencyBand.L1,
                              GPSSignalName.L1C, GNSSComponent.DATA)
    ### GPS L1C-P (Pilot): 4106 (0x100A)
    GPS_L1C_P = to_signal_val(SatelliteType.GPS, FrequencyBand.L1,
                              GPSSignalName.L1C, GNSSComponent.PILOT)

    ## L2 Band

    ### GPS L2C: 4172 (0x104C)
    GPS_L2C = to_signal_val(SatelliteType.GPS, FrequencyBand.L2,
                            GPSSignalName.L2C, GNSSComponent.COMBINED)
    ### GPS L2C-M (Data): 4173 (0x104D)
    GPS_L2C_M = to_signal_val(SatelliteType.GPS, FrequencyBand.L2,
                              GPSSignalName.L2C, GNSSComponent.DATA)
    ### GPS L2C-L (Pilot): 4174 (0x104E)
    GPS_L2C_L = to_signal_val(SatelliteType.GPS, FrequencyBand.L2,
                              GPSSignalName.L2C, GNSSComponent.PILOT)
    ### GPS L2 P(Y): 4176 (0x1050)
    GPS_L2P = to_signal_val(SatelliteType.GPS, FrequencyBand.L2,
                            GPSSignalName.L2P, GNSSComponent.COMBINED)

    ## L5 Band

    ### GPS L5: 4244 (0x1094)
    GPS_L5 = to_signal_val(SatelliteType.GPS, FrequencyBand.L5,
                           GPSSignalName.L5, GNSSComponent.COMBINED)
    ### GPS L5-I (Data): 4245 (0x1095)
    GPS_L5_I = to_signal_val(SatelliteType.GPS, FrequencyBand.L5,
                             GPSSignalName.L5, GNSSComponent.DATA)
    ### GPS L5-Q (Pilot): 4246 (0x1096)
    GPS_L5_Q = to_signal_val(SatelliteType.GPS, FrequencyBand.L5,
                             GPSSignalName.L5, GNSSComponent.PILOT)

    ############################################################################
    ## GLONASS
    ############################################################################

    ## L1 Band

    ### GLONASS L1 C/A: 8192 (0x2000)
    GLONASS_L1CA = to_signal_val(SatelliteType.GLONASS, FrequencyBand.L1,
                                 GLONASSSignalName.L1CA, GNSSComponent.COMBINED)
    ### GLONASS L1P: 8196 (0x2004)
    GLONASS_L1P = to_signal_val(SatelliteType.GLONASS, FrequencyBand.L1,
                                GLONASSSignalName.L1P, GNSSComponent.COMBINED)

    ## L2 Band

    ### GLONASS L2 C/A: 8264 (0x2048)
    GLONASS_L2CA = to_signal_val(SatelliteType.GLONASS, FrequencyBand.L2,
                                 GLONASSSignalName.L2CA, GNSSComponent.COMBINED)
    ### GLONASS L2P: 8268 (0x204C)
    GLONASS_L2P = to_signal_val(SatelliteType.GLONASS, FrequencyBand.L2,
                                GLONASSSignalName.L2P, GNSSComponent.COMBINED)

    ############################################################################
    ## Galileo
    ############################################################################

    ## L1 Band

    ### Galileo E1-A: 16384 (0x4000)
    GALILEO_E1A = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L1,
                                GalileoSignalName.E1A, GNSSComponent.COMBINED)
    ### Galileo E1-B/C: 16388 (0x4004)
    GALILEO_E1BC = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L1,
                                 GalileoSignalName.E1BC, GNSSComponent.COMBINED)
    ### Galileo E1-B (Data): 16389 (0x4005)
    GALILEO_E1B = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L1,
                                GalileoSignalName.E1BC, GNSSComponent.DATA)
    ### Galileo E1-C (Pilot): 16390 (0x4006)
    GALILEO_E1C = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L1,
                                GalileoSignalName.E1BC, GNSSComponent.PILOT)

    ## L2 Band

    ### Galileo E5b: 16460 (0x404C)
    GALILEO_E5B = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L2,
                                GalileoSignalName.E5B, GNSSComponent.COMBINED)
    ### Galileo E5b-I (Data): 16461 (0x404D)
    GALILEO_E5B_I = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L2,
                                  GalileoSignalName.E5B, GNSSComponent.DATA)
    ### Galileo E5b-Q (Pilot): 16462 (0x404E)
    GALILEO_E5B_Q = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L2,
                                  GalileoSignalName.E5B, GNSSComponent.PILOT)

    ## L5 Band

    ### Galileo E5a: 16520 (0x4088)
    GALILEO_E5A = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L5,
                                GalileoSignalName.E5A, GNSSComponent.COMBINED)
    ### Galileo E5a-I (Data): 16521 (0x4089)
    GALILEO_E5A_I = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L5,
                                  GalileoSignalName.E5A, GNSSComponent.DATA)
    ### Galileo E5a-Q (Pilot): 16522 (0x408A)
    GALILEO_E5A_Q = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L5,
                                  GalileoSignalName.E5A, GNSSComponent.PILOT)

    ## L6 Band

    ### Galileo E6-A: 16592 (0x40D0)
    GALILEO_E6A = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L6,
                                GalileoSignalName.E6A, GNSSComponent.COMBINED)
    ### Galileo E6-B/C: 16596 (0x40D4)
    GALILEO_E6BC = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L6,
                                 GalileoSignalName.E6BC, GNSSComponent.COMBINED)
    ### Galileo E6-B (Data): 16597 (0x40D5)
    GALILEO_E6B = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L6,
                                GalileoSignalName.E6BC, GNSSComponent.DATA)
    ### Galileo E6-C (Pilot): 16598 (0x40D6)
    GALILEO_E6C = to_signal_val(SatelliteType.GALILEO, FrequencyBand.L6,
                                GalileoSignalName.E6BC, GNSSComponent.PILOT)

    ############################################################################
    ## BeiDou
    ############################################################################

    ## L1 Band

    ### BeiDou B1I: 20480 (0x5000)
    BEIDOU_B1I = to_signal_val(SatelliteType.BEIDOU, FrequencyBand.L1,
                               BeiDouSignalName.B1I, GNSSComponent.COMBINED)
    ### BeiDou B1C: 20484 (0x5004)
    BEIDOU_B1C = to_signal_val(SatelliteType.BEIDOU, FrequencyBand.L1,
                               BeiDouSignalName.B1C, GNSSComponent.COMBINED)
    ### BeiDou B1C-D (Data): 20485 (0x5005)
    BEIDOU_B1C_D = to_signal_val(SatelliteType.BEIDOU, FrequencyBand.L1,
                                 BeiDouSignalName.B1C, GNSSComponent.DATA)
    ### BeiDou B1C-P (Pilot): 20486 (0x5006)
    BEIDOU_B1C_P = to_signal_val(SatelliteType.BEIDOU, FrequencyBand.L1,
                                 BeiDouSignalName.B1C, GNSSComponent.PILOT)

    ## L2 Band

    ### BeiDou B2I: 20552 (0x5048)
    BEIDOU_B2I = to_signal_val(SatelliteType.BEIDOU, FrequencyBand.L2,
                               BeiDouSignalName.B2I, GNSSComponent.COMBINED)
    ### BeiDou B2b: 20556 (0x504C)
    BEIDOU_B2B = to_signal_val(SatelliteType.BEIDOU, FrequencyBand.L2,
                               BeiDouSignalName.B2B, GNSSComponent.COMBINED)

    ## L5 Band

    ### BeiDou B2a: 20624 (0x5090)
    BEIDOU_B2A = to_signal_val(SatelliteType.BEIDOU, FrequencyBand.L5,
                               BeiDouSignalName.B2A, GNSSComponent.COMBINED)
    ### BeiDou B2a-D (Data): 20625 (0x5091)
    BEIDOU_B2A_D = to_signal_val(SatelliteType.BEIDOU, FrequencyBand.L5,
                                 BeiDouSignalName.B2A, GNSSComponent.DATA)
    ### BeiDou B2a-P (Pilot): 20626 (0x5092)
    BEIDOU_B2A_P = to_signal_val(SatelliteType.BEIDOU, FrequencyBand.L5,
                                 BeiDouSignalName.B2A, GNSSComponent.PILOT)

    ## L6 Band

    ### BeiDou B3I: 20692 (0x50D4)
    BEIDOU_B3I = to_signal_val(SatelliteType.BEIDOU, FrequencyBand.L6,
                               BeiDouSignalName.B3I, GNSSComponent.COMBINED)

    ############################################################################
    ## QZSS
    ############################################################################

    ## L1 Band

    ### QZSS C/A: 24576 (0x6000)
    QZSS_L1CA = to_signal_val(SatelliteType.QZSS, FrequencyBand.L1,
                              QZSSSignalName.L1CA, GNSSComponent.COMBINED)
    ### QZSS L1C: 24580 (0x6004)
    QZSS_L1C = to_signal_val(SatelliteType.QZSS, FrequencyBand.L1,
                             QZSSSignalName.L1C, GNSSComponent.COMBINED)
    ### QZSS L1C-D (Data): 24581 (0x6005)
    QZSS_L1C_D = to_signal_val(SatelliteType.QZSS, FrequencyBand.L1,
                               QZSSSignalName.L1C, GNSSComponent.DATA)
    ### QZSS L1C-P (Pilot): 24582 (0x6006)
    QZSS_L1C_P = to_signal_val(SatelliteType.QZSS, FrequencyBand.L1,
                               QZSSSignalName.L1C, GNSSComponent.PILOT)

    ## L2 Band

    ### QZSS L2C: 24648 (0x6048)
    QZSS_L2C = to_signal_val(SatelliteType.QZSS, FrequencyBand.L2,
                             QZSSSignalName.L2C, GNSSComponent.COMBINED)
    ### QZSS L2C-M (Data): 24649 (0x6049)
    QZSS_L2C_M = to_signal_val(SatelliteType.QZSS, FrequencyBand.L2,
                               QZSSSignalName.L2C, GNSSComponent.DATA)
    ### QZSS L2C-L (Pilot): 24650 (0x604A)
    QZSS_L2C_L = to_signal_val(SatelliteType.QZSS, FrequencyBand.L2,
                               QZSSSignalName.L2C, GNSSComponent.PILOT)
    ### QZSS L6: 24656 (0x6050)
    QZSS_L6 = to_signal_val(SatelliteType.QZSS, FrequencyBand.L2,
                            QZSSSignalName.L6, GNSSComponent.COMBINED)
    ### QZSS L6-M (Data): 24657 (0x6051)
    QZSS_L6_M = to_signal_val(SatelliteType.QZSS, FrequencyBand.L2,
                              QZSSSignalName.L6, GNSSComponent.DATA)
    ### QZSS L6-L (Pilot): 24658 (0x6052)
    QZSS_L6_L = to_signal_val(SatelliteType.QZSS, FrequencyBand.L2,
                              QZSSSignalName.L6, GNSSComponent.PILOT)

    ## L5 Band

    ### QZSS L5: 24716 (0x608C)
    QZSS_L5 = to_signal_val(SatelliteType.QZSS, FrequencyBand.L5,
                            QZSSSignalName.L5, GNSSComponent.COMBINED)
    ### QZSS L5-I (Data): 24717 (0x608D)
    QZSS_L5_I = to_signal_val(SatelliteType.QZSS, FrequencyBand.L5,
                              QZSSSignalName.L5, GNSSComponent.DATA)
    ### QZSS L5-Q (Pilot): 24718 (0x608E)
    QZSS_L5_Q = to_signal_val(SatelliteType.QZSS, FrequencyBand.L5,
                              QZSSSignalName.L5, GNSSComponent.PILOT)

    ############################################################################
    ## SBAS
    ############################################################################

    ## L1 Band

    ### SBAS C/A: 32768 (0x8000)
    SBAS_L1CA = to_signal_val(SatelliteType.SBAS, FrequencyBand.L1,
                              SBASSignalName.L1CA, GNSSComponent.COMBINED)

    ## L5 Band

    ### SBAS L5: 32900 (0x8084)
    SBAS_L5 = to_signal_val(SatelliteType.SBAS, FrequencyBand.L5,
                            SBASSignalName.L5, GNSSComponent.COMBINED)
    ### SBAS L5-I (Data): 32901 (0x8085)
    SBAS_L5_I = to_signal_val(SatelliteType.SBAS, FrequencyBand.L5,
                              SBASSignalName.L5, GNSSComponent.DATA)
    ### SBAS L5-Q (Pilot): 32902 (0x8086)
    SBAS_L5_Q = to_signal_val(SatelliteType.SBAS, FrequencyBand.L5,
                              SBASSignalName.L5, GNSSComponent.PILOT)

    ## < Stop Autogenerated Types (See python/fusion_engine_client/messages/signal_def_gen.py)

    def get_satellite_type(self) -> SatelliteType:
        return _get_signal_part(self, SatelliteType, raise_on_unrecognized=False)

    def get_frequency_band(self) -> FrequencyBand:
        return _get_signal_part(self, FrequencyBand, raise_on_unrecognized=False)

    def get_signal_name(self) -> SignalName:
        system = self.get_satellite_type()
        return _get_signal_part(self, _SIGNAL_NAME_ENUM_MAP[system], raise_on_unrecognized=False)

    def get_gnss_component(self) -> GNSSComponent:
        return _get_signal_part(self, GNSSComponent, raise_on_unrecognized=False)


def pretty_print_gnss_enum(value: IntEnum, omit_satellite_type: bool = False, omit_component_hint: bool = False) -> str:
    if isinstance(value, GNSSSignalType):
        if value == GNSSSignalType.UNKNOWN:
            return "Unknown Signal"
        else:
            return _get_pretty_gnss_signal_type(
                value.name,
                None if omit_satellite_type else value.get_satellite_type(),
                value.get_signal_name(),
                value.get_gnss_component(),
                omit_component_hint)
    elif isinstance(value, SatelliteType):
        if SatelliteType.GALILEO == value:
            return 'Galileo'
        elif SatelliteType.BEIDOU == value:
            return 'BeiDou'
    elif isinstance(value, FrequencyBand):
        if FrequencyBand.L1_L2_WIDE_LANE == value:
            return 'L1-L2 Wide-Lane'
        elif FrequencyBand.L1_L5_WIDE_LANE == value:
            return 'L1-L5 Wide-Lane'
    elif isinstance(value, GPSSignalName):
        if GPSSignalName.L1P == value:
            return 'L1 P(Y)'
        elif GPSSignalName.L2P == value:
            return 'L2 P(Y)'
    elif isinstance(value, GalileoSignalName):
        if GalileoSignalName.E5A == value:
            return 'E5a'
        elif GalileoSignalName.E5B == value:
            return 'E5b'
        elif value == GalileoSignalName.E1BC:
            return 'E1-B/C'
        elif value == GalileoSignalName.E6BC:
            return 'E6-B/C'
        elif value == GalileoSignalName.E1A:
            return 'E1-A'
        elif value == GalileoSignalName.E6A:
            return 'E6-A'
    elif isinstance(value, BeiDouSignalName):
        if BeiDouSignalName.B2A == value:
            return 'B2a'
        elif BeiDouSignalName.B2B == value:
            return 'B2b'
    elif isinstance(value, GNSSComponent):
        return value.name.title()

    if value.name == 'L1CA' and value is not GLONASSSignalName.L1CA:
        return 'C/A'
    elif value.name.endswith('CA'):
        return value.name[:-2] + ' C/A'
    else:
        return value.name


INVALID_SV_HASH = 0x0FFF0000
INVALID_SIGNAL_HASH = 0x00000000


def get_satellite_type(hash: int) -> SatelliteType:
    satellite_type = SatelliteType(hash >> 28, raise_on_unrecognized=False)
    return satellite_type


def get_prn(hash: int) -> int:
    prn = hash & 0xFFFF
    return prn


def get_signal_type(hash: int) -> GNSSSignalType:
    signal_type_val = (hash >> 16) & 0xFFFF
    if (signal_type_val & 0xFFF) == 0xFFF:
        signal_type = GNSSSignalType.UNKNOWN
    else:
        signal_type = GNSSSignalType(signal_type_val, raise_on_unrecognized=False)
    return signal_type


def get_satellite_hash(signal_hash: int) -> int:
    """!
    @brief Get the satellite hash for a given signal hash.
    """
    sv_hash = signal_hash | 0x0FFF0000
    return sv_hash

def decode_signal_hash(signal_hash: int) -> tuple[SatelliteType, int, Optional[GNSSSignalType]]:
    """!
    @brief Decode an integer satellite/signal hash into its component parts: system, signal type, and PRN.

    Satellite/signal IDs are encoded as 32-bit integers as follows
    ```
    { SatelliteType (4b), 0xFFF, prn (16b) }  # Satellite ID
    { GNSSSignalType (16b), prn (16b) }       # Signal ID
    ```

    @param signal_hash An integer satellite/signal hash value.

    @return A tuple containing the @ref SatelliteType, PRN (`int`), and a @ref GNSSSignalType if available. The
            @ref GNSSSignalType will be `None` for satellite hashes.
    """
    prn = get_prn(signal_hash)

    signal_type_val = (signal_hash >> 16) & 0xFFFF
    if (signal_type_val & 0xFFF) == 0xFFF:
        signal_type = None
        satellite_type = get_satellite_type(signal_hash)
    else:
        signal_type = GNSSSignalType(signal_type_val, raise_on_unrecognized=False)
        satellite_type = signal_type.get_satellite_type()
    return satellite_type, prn, signal_type


def encode_signal_hash(signal_info: GNSSSignalType | SatelliteType, prn) -> int:
    """!
    @brief Encode satellite/signal ID component parts into an integer hash.

    See @ref decode_signal_hash() for details.

    @param signal_info The @ref GNSSSignalType for a signal ID or the @ref SatelliteType for a satellite ID.
    @param prn The satellite/signal's PRN.

    @return The encoded integer value.
    """
    if isinstance(signal_info, GNSSSignalType):
        signal_type_val = int(signal_info)
    else:
        signal_type_val = (int(signal_info) << 12) | 0xFFF

    signal_hash = (signal_type_val << 16) | int(prn)
    return signal_hash


@functools.total_ordering
class SatelliteID:
    """!
    @brief Representation of a GNSS satellite (@ref SatelliteType + PRN).
    """

    def __init__(self, system: SatelliteType = None, prn: int = None, sv_hash: int = None):
        """!
        @brief Create a signal ID instance.

        @param system The GNSS constellation to which this satellite belongs.
        @param prn The satellite's PRN.
        @param sv_hash A known integer satellite hash.
        """
        if sv_hash is not None:
            if system is not None or prn is not None:
                raise ValueError('You cannot specify both a signal hash and signal type/PRN.')

            self.system = SatelliteType.UNKNOWN
            self.prn = 0
            self.decode_hash(sv_hash)
        else:
            if system is None:
                if prn is None:
                    self.system = SatelliteType.UNKNOWN
                    self.prn = 0
                else:
                    raise ValueError(f'GNSS system not specified.')
            elif prn is None:
                raise ValueError(f'PRN not specified.')
            else:
                self.system = system
                self.prn = prn

        self._hash = encode_signal_hash(signal_info=self.system, prn=self.prn)

    def get_satellite_type(self) -> SatelliteType:
        return self.system

    def get_prn(self) -> int:
        return self.prn

    def decode_hash(self, sv_hash: int):
        self.system, self.prn, _ = decode_signal_hash(sv_hash)
        self._hash = int(sv_hash)

    def encode_hash(self) -> int:
        return self._hash

    def to_string(self, short: bool = False) -> str:
        """!
        @brief Generate a human-readable string for this satellite.

        @param short If `True`, output a compact format string.

        @return A string formatted as shown:
                - `short == False`: `Galileo PRN 5`
                - `short == True`: `E05`
        """
        if short:
            if self.prn > 0:
                return '%s%02d' % (SatelliteTypeChar[self.system], self.prn)
            else:
                return '%s??' % SatelliteTypeChar[self.system]
        else:
            if self.prn > 0:
                return '%s PRN %d' % (str(self.system), self.prn)
            elif self.system != SatelliteType.UNKNOWN:
                return '%s PRN ?' % (str(self.system),)
            else:
                return 'Invalid Satellite'

    def __lt__(self, other: Union['SatelliteID', int]):
        self_hash = self.encode_hash()
        other_hash = self.to_hash(other)
        # Note: Invalid SV < valid SV.
        if self_hash == INVALID_SV_HASH:
            return other_hash != INVALID_SV_HASH
        elif other_hash == INVALID_SV_HASH:
            return False
        else:
            return self_hash < other_hash

    def __eq__(self, other: Union['SatelliteID', int]):
        self_hash = self.encode_hash()
        other_hash = self.to_hash(other)
        return self_hash == other_hash

    def __int__(self):
        return self._hash

    def __hash__(self):
        return self._hash

    def __str__(self):
        return self.to_string(short=False)

    def __repr__(self):
        return f"[{self.to_string(short=True)} (0x{self.encode_hash():08x})]"

    @classmethod
    def to_id(cls, id: Union['SatelliteID', int]) -> 'SatelliteID':
        if isinstance(id, SatelliteID):
            return id
        else:
            signal_id = SatelliteID()
            signal_id.decode_hash(id)
            return signal_id

    @classmethod
    def to_hash(cls, id: Union['SatelliteID', int]) -> int:
        if isinstance(id, SatelliteID):
            return id.encode_hash()
        else:
            return id


@functools.total_ordering
class SignalID:
    """!
    @brief Representation of a GNSS signal (@ref SatelliteType, @ref GNSSSignalType, and PRN).
    """

    def __init__(self, signal_type: GNSSSignalType = None, prn: int = None, signal_hash: int = None):
        """!
        @brief Create a signal ID instance.

        @param signal_type The type of this signal.
        @param prn The signal's PRN.
        @param signal_hash A known integer signal hash.
        """
        if signal_hash is not None:
            if signal_type is not None or prn is not None:
                raise ValueError('You cannot specify both a signal hash and signal type/PRN.')

            self.signal_type = None
            self.prn = 0
            self.decode_hash(signal_hash)
        else:
            if signal_type is None:
                if prn is None:
                    self.signal_type = GNSSSignalType.UNKNOWN
                    self.prn = 0
                else:
                    raise ValueError(f'Signal type not specified.')
            elif prn is None:
                raise ValueError(f'PRN not specified.')
            else:
                self.signal_type = signal_type
                self.prn = prn

        self._hash = encode_signal_hash(signal_info=self.signal_type, prn=self.prn)

    def get_satellite_id(self) -> SatelliteID:
        """!
        @brief Get the @ref SatelliteID corresponding with this signal.

        @return The @ref SatelliteID for the satellite transmitting this signal.
        """
        return SatelliteID(system=self.signal_type.get_satellite_type(), prn=self.prn)

    def get_satellite_type(self) -> SatelliteType:
        return self.signal_type.get_satellite_type()

    def get_signal_type(self) -> GNSSSignalType:
        return self.signal_type

    def get_frequency_band(self) -> FrequencyBand:
        return self.signal_type.get_frequency_band()

    def get_signal_name(self) -> SignalName:
        return self.signal_type.get_signal_name()

    def get_gnss_component(self) -> GNSSComponent:
        return self.signal_type.get_gnss_component()

    def get_prn(self) -> int:
        return self.prn

    def decode_hash(self, signal_hash: int):
        _, self.prn, self.signal_type = decode_signal_hash(signal_hash)
        if self.signal_type is None:
            raise ValueError(f'Signal type not known for signal hash 0x{signal_hash:08x}.')
        self._hash = int(signal_hash)

    def encode_hash(self) -> int:
        return self._hash

    def to_string(self, short: bool = False) -> str:
        """!
        @brief Generate a human-readable string for this signal.

        @param short If `True`, output a compact format string.

        @return A string formatted as shown:
                - `short == False`: `Galileo E1-C PRN 5`
                - `short == True`: `E05 E1-C`
        """
        if short:
            if self.signal_type == GNSSSignalType.UNKNOWN:
                signal_str = 'UNKNOWN'
            else:
                signal_str = pretty_print_gnss_enum(self.signal_type, omit_satellite_type=True,
                                                    omit_component_hint=True)
            return '%s %s' % (self.get_satellite_id().to_string(short=True), signal_str)
        else:
            if self.prn > 0:
                return '%s PRN %d' % (pretty_print_gnss_enum(self.signal_type), self.prn)
            elif self.signal_type != GNSSSignalType.UNKNOWN:
                return '%s PRN ?' % (pretty_print_gnss_enum(self.signal_type))
            else:
                return 'Invalid Signal'

    def __lt__(self, other: Union['SignalID', int]):
        self_hash = self.encode_hash()
        other_hash = self.to_hash(other)
        # Note: Invalid signals < valid signals.
        if self_hash == INVALID_SIGNAL_HASH:
            return other_hash != INVALID_SIGNAL_HASH
        elif other_hash == INVALID_SIGNAL_HASH:
            return False
        else:
            return self_hash < other_hash

    def __eq__(self, other: Union['SignalID', int]):
        self_hash = self.encode_hash()
        other_hash = self.to_hash(other)
        return self_hash == other_hash

    def __int__(self):
        return self._hash

    def __hash__(self):
        return self._hash

    def __str__(self):
        return self.to_string(short=False)

    def __repr__(self):
        return f"[{self.to_string(short=True)} (0x{self.encode_hash():08x})]"

    def __getattr__(self, item):
        # Aliases for convenience/consistency with SatelliteID.
        if item == 'system':
            return self.get_satellite_type()
        elif item == 'sv':
            return self.get_satellite_id()
        else:
            raise AttributeError(f"Unknown attribute '{item}'.")

    @classmethod
    def to_id(cls, id: Union['SignalID', int]) -> 'SignalID':
        if isinstance(id, SignalID):
            return id
        else:
            signal_id = SignalID()
            signal_id.decode_hash(id)
            return signal_id

    @classmethod
    def to_hash(cls, id: Union['SignalID', int]) -> int:
        if isinstance(id, SignalID):
            return id.encode_hash()
        else:
            return id
