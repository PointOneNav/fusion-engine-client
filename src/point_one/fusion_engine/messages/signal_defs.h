/**************************************************************************/ /**
 * @brief GNSS signal and frequency type definitions.
 ******************************************************************************/

#pragma once

#include <cstdint>
#include <ostream>

namespace point_one {
namespace fusion_engine {
namespace messages {

/**
 * @brief System/constellation type definitions.
 */
enum class SatelliteType : uint8_t {
  UNKNOWN = 0,
  GPS = 1,
  GLONASS = 2,
  LEO = 3,
  GALILEO = 4,
  BEIDOU = 5,
  QZSS = 6,
  MIXED = 7,
  SBAS = 8,
  IRNSS = 9,
  MAX_VALUE = IRNSS,
};

/**
 * @brief Get a human-friendly string name for the specified @ref SatelliteType
 *        (GNSS constellation).
 * @ingroup enum_definitions
 *
 * @param type The desired satellite type.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(SatelliteType type) {
  switch (type) {
    case SatelliteType::UNKNOWN:
      return "Unknown";

    case SatelliteType::GPS:
      return "GPS";

    case SatelliteType::GLONASS:
      return "GLONASS";

    case SatelliteType::LEO:
      return "LEO";

    case SatelliteType::GALILEO:
      return "Galileo";

    case SatelliteType::BEIDOU:
      return "BeiDou";

    case SatelliteType::QZSS:
      return "QZSS";

    case SatelliteType::MIXED:
      return "Mixed";

    case SatelliteType::SBAS:
      return "SBAS";

    case SatelliteType::IRNSS:
      return "IRNSS";

    default:
      return "Invalid System";
  }
}

/**
 * @brief @ref SatelliteType stream operator.
 * @ingroup enum_definitions
 */
inline std::ostream& operator<<(std::ostream& stream, SatelliteType type) {
  stream << to_string(type) << " (" << (int)type << ")";
  return stream;
}

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
