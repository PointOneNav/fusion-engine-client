/**************************************************************************/ /**
 * @brief GNSS signal and frequency type definitions.
 ******************************************************************************/

#pragma once

#include <cstdint>
#include <ostream>

namespace point_one {
namespace fusion_engine {
namespace messages {

////////////////////////////////////////////////////////////////////////////////
// SatelliteType
////////////////////////////////////////////////////////////////////////////////

/**
 * @name GNSS Constellation (System) Definitions
 * @{
 */

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

/** @} */

/**
 * @defgroup sat_type_masks @ref SatelliteType Bitmask Support
 * @ingroup config_types
 *
 * These values can be used to specify a bitmask for controlling enabled GNSS
 * constellations. The bit locations are equal to the values set by @ref
 * SatelliteType for each constellation.
 *
 * For example, the mask 0x32 enables GPS, Galileo, and BeiDou. You can create
 * that mask with the `SATELLITE_TYPE_MASK_*` constants:
 * ```cpp
 * uint32_t mask = SATELLITE_TYPE_MASK_GPS | SATELLITE_TYPE_MASK_GALILEO |
 *                 SATELLITE_TYPE_MASK_BEIDOU;
 * ```
 *
 * or by calling the @ref ToBitMask(SatelliteType) helper function:
 * ```cpp
 * uint32_t mask = ToBitMask(SatelliteType::GPS, SatelliteType::GALILEO,
 *                           SatelliteType::BEIDOU);
 * ```
 *
 * @{
 */

static constexpr uint32_t SATELLITE_TYPE_MASK_GPS =
    (1UL << static_cast<uint8_t>(SatelliteType::GPS));
static constexpr uint32_t SATELLITE_TYPE_MASK_GLONASS =
    (1UL << static_cast<uint8_t>(SatelliteType::GLONASS));
static constexpr uint32_t SATELLITE_TYPE_MASK_LEO =
    (1UL << static_cast<uint8_t>(SatelliteType::LEO));
static constexpr uint32_t SATELLITE_TYPE_MASK_GALILEO =
    (1UL << static_cast<uint8_t>(SatelliteType::GALILEO));
static constexpr uint32_t SATELLITE_TYPE_MASK_BEIDOU =
    (1UL << static_cast<uint8_t>(SatelliteType::BEIDOU));
static constexpr uint32_t SATELLITE_TYPE_MASK_QZSS =
    (1UL << static_cast<uint8_t>(SatelliteType::QZSS));
static constexpr uint32_t SATELLITE_TYPE_MASK_MIXED =
    (1UL << static_cast<uint8_t>(SatelliteType::MIXED));
static constexpr uint32_t SATELLITE_TYPE_MASK_SBAS =
    (1UL << static_cast<uint8_t>(SatelliteType::SBAS));
static constexpr uint32_t SATELLITE_TYPE_MASK_IRNSS =
    (1UL << static_cast<uint8_t>(SatelliteType::IRNSS));

/**
 * @brief Convert a @ref SatelliteType to a corresponding constellation control
 *        bitmask value.
 *
 * For example:
 *
 * ```cpp
 * uint32_t mask = ToBitMask(SatelliteType::GPS);
 * ```
 *
 * generates the following bitmask:
 *
 * ```cpp
 * uint32_t mask = (1UL << static_cast<uint8_t>(SatelliteType::GPS));
 * ```
 *
 * @param type The desired constellation.
 *
 * @return The corresponding bitmask.
 */
constexpr uint32_t ToBitMask(SatelliteType type) {
  return (1U << (static_cast<uint8_t>(type)));
}

/**
 * @brief Convert two or more @ref SatelliteType values to a bitmask.
 *
 * For example:
 *
 * ```cpp
 * uint32_t mask = ToBitMask(SatelliteType::GPS, SatelliteType::GALILEO,
 *                           SatelliteType::BEIDOU);
 * ```
 *
 * generates the following bitmask:
 *
 * ```cpp
 * uint32_t mask = (1UL << static_cast<uint8_t>(SatelliteType::GPS)) |
 *                 (1UL << static_cast<uint8_t>(SatelliteType::GALILEO)) |
 *                 (1UL << static_cast<uint8_t>(SatelliteType::BEIDOU));
 * ```
 *
 * @tparam Args The type of the `others` values (@ref SatelliteType)
 * @param first The first value.
 * @param others One or more additional values.
 *
 * @return The corresponding bitmask.
 */
template <typename... Args>
constexpr uint32_t ToBitMask(SatelliteType first, Args... others) {
  return ToBitMask(first) | ToBitMask(others...);
}

/** @} */

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
