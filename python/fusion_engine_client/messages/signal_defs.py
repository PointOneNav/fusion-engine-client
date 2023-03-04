import re
from typing import List, Union

import numpy as np

from ..utils.enum_utils import IntEnum


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


class SatelliteTypeMask(IntEnum):
    GPS = (1 << SatelliteType.GPS)
    GLONASS = (1 << SatelliteType.GLONASS)
    LEO = (1 << SatelliteType.LEO)
    GALILEO = (1 << SatelliteType.GALILEO)
    BEIDOU = (1 << SatelliteType.BEIDOU)
    QZSS = (1 << SatelliteType.QZSS)
    MIXED = (1 << SatelliteType.MIXED)
    SBAS = (1 << SatelliteType.SBAS)
    IRNSS = (1 << SatelliteType.IRNSS)

    ALL = 0xFFFFFFFF

    @classmethod
    def to_bit_mask(cls, systems: List[Union[SatelliteType, str]]):
        mask = 0
        for system in systems:
            if isinstance(system, str):
                mask |= getattr(cls, system.upper())
            else:
                mask |= (1 << int(system))
        return mask

    @classmethod
    def bit_mask_to_systems(cls, mask: int):
        systems = []
        for system in SatelliteType:
            if (mask & (1 << int(system))) != 0:
                systems.append(system)
        return systems

    @classmethod
    def bit_mask_to_string(cls, mask: int):
        systems = cls.bit_mask_to_systems(mask)
        return ', '.join(str(s) for s in systems)


class SignalType(IntEnum):
    UNKNOWN = 0


class FrequencyBand(IntEnum):
    UNKNOWN = 0
    L1 = 1
    L2 = 2
    L5 = 5
    L6 = 6


class FrequencyBandMask(IntEnum):
    L1 = (1 << FrequencyBand.L1)
    L2 = (1 << FrequencyBand.L2)
    L5 = (1 << FrequencyBand.L5)
    L6 = (1 << FrequencyBand.L6)

    ALL = 0xFFFFFFFF

    @classmethod
    def to_bit_mask(cls, frequencies: List[Union[FrequencyBand, str]]):
        mask = 0
        for freq in frequencies:
            if isinstance(freq, str):
                mask |= getattr(cls, freq.upper())
            else:
                mask |= (1 << int(freq))
        return mask

    @classmethod
    def bit_mask_to_systems(cls, mask: int):
        frequencies = []
        for freq in FrequencyBand:
            if (mask & (1 << int(freq))) != 0:
                frequencies.append(freq)
        return frequencies

    @classmethod
    def bit_mask_to_string(cls, mask: int):
        systems = cls.bit_mask_to_systems(mask)
        return ', '.join(str(s) for s in systems)


_SHORT_FORMAT = re.compile(r'([%s])(\d+)(?:\s+(\w+))?' % ''.join(SatelliteTypeCharReverse.keys()))
_LONG_FORMAT = re.compile(r'(\w+)(?:\s+(\w+))(?:\s+PRN\s+(\d+))?')


def decode_signal_id(signal_id):
    """!
    @brief Convert a hashed signal ID to its components: system, signal type, and PRN.

    @param signal_id The signal hash, or a tuple containing enumeration values or
           string names.

    @return A tuple containing the @ref SatelliteType, @ref SignalType, and PRN (@c int).
    """
    if isinstance(signal_id, (int, float)) or np.issubdtype(signal_id, np.integer):
        signal_id = int(signal_id)

        system = int(signal_id / 1000000)
        signal_id -= system * 1000000

        signal_type = int(signal_id / 1000)
        signal_id -= signal_type * 1000

        prn = signal_id

        return SatelliteType(system), None, prn
    elif isinstance(signal_id, (tuple, list, set)):
        if len(signal_id) != 3:
            raise ValueError('Tuple must contain 3 elements: system, signal type, and PRN.')
        else:
            system, signal_type, prn = signal_id

            if isinstance(system, (int, float)) or np.issubdtype(system, np.integer):
                system = SatelliteType(int(system))
            elif isinstance(system, str):
                system = SatelliteType[system]

            # if isinstance(signal_type, (int, float)) or np.issubdtype(signal_type, np.integer):
            #     signal_type = SignalType(int(signal_type))
            # elif isinstance(signal_type, str):
            #     signal_type = SignalType[signal_type]

            return system, signal_type, prn
    else:
        raise ValueError('Unexpected input format (%s).' % type(signal_id))


def encode_signal_id(system, signal_type=None, prn=None):
    """!
    @param Encode a signal description into a numeric signal ID.

    If @c signal and @c prn are @c None, @c system will be interpreted as one of the following options:
    -# A dictionary containing any of the following keys: `system`, `signal_type`, `prn`
    -# An object with `system`, `signal_type`, and `prn` member variables
    -# A tuple containing all three values, with system and signal type values stored as integers/enumeration values or
       string names

    @param system The @ref SatelliteType of the signal, or one of the options listed above.
    @param signal_type The @ref SignalType of the signal.
    @param prn The signal's PRN.

    @return The encoded ID value.
    """
    if signal_type is None and prn is None:
        # If it's a tuple/list, extract the components from it.
        if isinstance(system, (tuple, list, set)):
            if len(system) == 3:
                system, signal_type, prn = system
            else:
                raise ValueError('Must specify a tuple containing system, signal type, and PRN.')
        # Similar for a dictionary or an object.
        elif isinstance(system, (object, dict)):
            signal_details = system
            if isinstance(signal_details, object):
                signal_details = signal_details.__dict__

            system = signal_details.get('system', SatelliteType.UNKNOWN)
            signal_type = signal_details.get('signal_type', SignalType.UNKNOWN)
            prn = signal_details.get('prn', 0)
        # If system is an integer, assume it's a complete signal ID and return it as is.
        elif isinstance(system, (int, float)) or np.issubdtype(system, np.integer):
            return int(system)
        else:
            raise ValueError('Unexpected input format.')

    if system is None:
        system = int(SatelliteType.UNKNOWN)
    elif isinstance(system, str):
        system = int(SatelliteType[system])
    elif isinstance(system, SatelliteType):
        system = int(system)

    if signal_type is None:
        signal_type = int(SignalType.UNKNOWN)
    # elif isinstance(signal_type, str):
    #     signal_type = int(SignalType[signal_type])
    # elif isinstance(signal_type, SignalType):
    #     signal_type = int(signal_type)

    return system * 1000000 + signal_type * 1000 + prn


def satellite_to_string(descriptor, short: bool = False):
    """!
    @brief Generate a human-readable string from a satellite descriptor.

    @param descriptor A signal/satellite descriptor compatible with @ref decode_signal_id().
    @param short If `True`, output a compact format string.

    @return A string formatted as shown:
            - `short == True`: `Galileo PRN 5`
            - `short == False`: `E05`
    """
    system, _, prn = decode_signal_id(descriptor)

    if short:
        return '%s%02d' % (SatelliteTypeChar[system], prn)
    else:
        return '%s PRN %d' % (str(system), prn)


def signal_from_string(string, return_encoded=False):
    m = _LONG_FORMAT.match(string)
    if m:
        try:
            system = SatelliteType[m.group(1)]
        except KeyError:
            raise ValueError("Unrecognized system '%s'." % m.group(1))

        if m.group(2):
            try:
                signal_type = SignalType[m.group(2)]
            except KeyError:
                raise ValueError("Unrecognized signal type '%s'." % m.group(2))
        else:
            signal_type = SignalType.UNKNOWN

        if m.group(3):
            prn = int(m.group(3))
        else:
            prn = 0
    else:
        m = _SHORT_FORMAT.match(string)
        if m:
            try:
                system = SatelliteTypeCharReverse[m.group(1)]
            except KeyError:
                raise ValueError("Unrecognized system character '%s'." % m.group(1))

            prn = int(m.group(2))

            if m.group(3):
                try:
                    signal_type = SignalType[m.group(3)]
                except KeyError:
                    raise ValueError("Unrecognized signal type '%s'." % m.group(3))
            else:
                signal_type = SignalType.UNKNOWN
        else:
            raise ValueError('Unrecognized string format.')

    if return_encoded:
        return encode_signal_id(system, signal_type, prn)
    else:
        return system, signal_type, prn


def signal_to_string(descriptor, short: bool = False):
    """!
    @brief Generate a human-readable string from a signal descriptor.

    @param descriptor A signal/satellite descriptor compatible with @ref decode_signal_id().
    @param short If `True`, output a compact format string.

    @return A string formatted as shown:
            - `short == True`: `Galileo E5a PRN 5`
            - `short == False`: `E05 E5a`
    """
    system, signal_type, prn = decode_signal_id(descriptor)

    if short:
        return '%s%02d %s' % (SatelliteTypeChar[system], prn, str(signal_type))
    else:
        return '%s %s PRN %d' % (str(system), str(signal_type), prn)


def signal_type_to_string(descriptor):
    """!
    @brief Generate a human-readable string from a signal type descriptor.

    @param descriptor A signal/satellite descriptor compatible with @ref decode_signal_id().

    @return A string formatted like `Galileo E5a`.
    """
    system, signal_type, _ = decode_signal_id(descriptor)
    return '%s %s' % (str(system), str(signal_type))


def get_system(descriptor):
    """!
    @brief Get the satellite type (system) enumeration for a particular signal.

    @param descriptor A signal/satellite descriptor compatible with @ref decode_signal_id().

    @return The @ref SatelliteType.
    """
    system, _, _ = decode_signal_id(descriptor)
    return system


def get_prn(descriptor):
    """!
    @brief Get the PRN for a particular signal.

    @param descriptor A signal/satellite descriptor compatible with @ref decode_signal_id().

    @return The PRN.
    """
    _, _, prn = decode_signal_id(descriptor)
    return prn


def get_satellite_id(descriptor):
    """!
    @brief Get a numeric ID for an individual satellite (can be used to represent all signals from a given SV).

    The signal type will be set to @c SignalType.UNKNOWN.

    @param descriptor A signal/satellite descriptor compatible with @ref decode_signal_id().

    @return The resulting ID value.
    """
    system, _, prn = decode_signal_id(descriptor)
    return encode_signal_id(system, SignalType.UNKNOWN, prn)


def is_same_satellite(a, b):
    """!
    @brief Check if two signals originate from the same satellite.

    @param a The first signal descriptor.
    @param b The first signal descriptor.
    """
    return get_satellite_id(a) == get_satellite_id(b)


def get_signal_type_id(descriptor):
    """!
    @brief Get a numeric ID for a signal type within a given constellation (can be used to represent all signals of that
           type across all satellites).

    The PRN will be set to 0.

    @param descriptor A signal/satellite descriptor compatible with @ref decode_signal_id().

    @return The resulting ID value.
    """
    system, descriptor, _ = decode_signal_id(descriptor)
    return encode_signal_id(system, descriptor, 0)


def is_same_signal_type(a, b):
    """!
    @brief Check if two signals are of the same type (e.g., GPS C/A).

    @param a The first signal descriptor.
    @param b The first signal descriptor.
    """
    return get_signal_type_id(a) == get_signal_type_id(b)
