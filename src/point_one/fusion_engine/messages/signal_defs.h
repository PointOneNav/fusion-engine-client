/**************************************************************************/ /**
 * @brief GNSS signal and frequency type definitions.
 ******************************************************************************/

#pragma once

#include <cstdint>

#include "point_one/fusion_engine/common/portability.h"

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
P1_CONSTEXPR_FUNC const char* to_string(SatelliteType type) {
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
inline p1_ostream& operator<<(p1_ostream& stream, SatelliteType type) {
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

static constexpr uint32_t SATELLITE_TYPE_MASK_ALL = 0xFFFFFFFF;

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

////////////////////////////////////////////////////////////////////////////////
// FrequencyBand
////////////////////////////////////////////////////////////////////////////////

/**
 * @name GNSS Constellation (System) Definitions
 * @{
 */

/**
 * @brief GNSS frequency band definitions.
 */
enum class FrequencyBand : uint8_t {
  UNKNOWN = 0,
  /**
   * L1 band = 1561.098 MHz (BeiDou B1) -> 1602.0 (GLONASS G1)
   * Includes: GPS/QZSS L1, Galileo E1 (same as GPS L1), BeiDou B1I and B1C
   * (same as GPS L1), GLONASS G1
   */
  L1 = 1,
  /**
   * L2 band = 1202.025 MHz (G3) -> 1248.06 (G2)
   * Includes: GPS L2, Galileo E5b, BeiDou B2I (same as Galileo E5b),
   * GLONASS G2 & G3
   */
  L2 = 2,
  /**
   * L5 band = 1176.45 MHz (L5)
   * Includes: GPS/QZSS L5, Galileo E5a, BeiDou B2a, IRNSS L5
   */
  L5 = 5,
  /**
   * L2 band = 1262.52 MHz (B3) -> 1278.75 (QZSS L6)
   * Includes: Galileo E6, BeiDou B3, QZSS L6
   */
  L6 = 6,
  MAX_VALUE = L6,
};

/**
 * @brief Get a human-friendly string name for the specified @ref FrequencyBand.
 * @ingroup enum_definitions
 *
 * @param type The desired frequency band.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(FrequencyBand type) {
  switch (type) {
    case FrequencyBand::UNKNOWN:
      return "Unknown";

    case FrequencyBand::L1:
      return "L1";

    case FrequencyBand::L2:
      return "L2";

    case FrequencyBand::L5:
      return "L5";

    case FrequencyBand::L6:
      return "L6";

    default:
      return "Invalid Frequency Band";
  }
}

/**
 * @brief @ref FrequencyBand stream operator.
 * @ingroup enum_definitions
 */
inline p1_ostream& operator<<(p1_ostream& stream, FrequencyBand type) {
  stream << to_string(type) << " (" << (int)type << ")";
  return stream;
}

/** @} */

/**
 * @defgroup freq_band_masks @ref FrequencyBand Bitmask Support
 * @ingroup config_types
 *
 * These values can be used to specify a bitmask for controlling enabled GNSS
 * frequency bands. The bit locations are equal to the values set by @ref
 * FrequencyBand.
 *
 * For example, the mask 0x22 enables L1 and L5. You can create that mask with
 * the `FREQUENCY_BAND_MASK_*` constants:
 * ```cpp
 * uint32_t mask = FREQUENCY_BAND_MASK_L1 | FREQUENCY_BAND_MASK_L5;
 * ```
 *
 * or by calling the @ref ToBitMask(FrequencyBand) helper function:
 * ```cpp
 * uint32_t mask = ToBitMask(FrequencyBand::L1, FrequencyBand::L5);
 * ```
 *
 * @{
 */

static constexpr uint32_t FREQUENCY_BAND_MASK_L1 =
    (1UL << static_cast<uint8_t>(FrequencyBand::L1));
static constexpr uint32_t FREQUENCY_BAND_MASK_L2 =
    (1UL << static_cast<uint8_t>(FrequencyBand::L2));
static constexpr uint32_t FREQUENCY_BAND_MASK_L5 =
    (1UL << static_cast<uint8_t>(FrequencyBand::L5));
static constexpr uint32_t FREQUENCY_BAND_MASK_L6 =
    (1UL << static_cast<uint8_t>(FrequencyBand::L6));

static constexpr uint32_t FREQUENCY_BAND_MASK_ALL = 0xFFFFFFFF;

/**
 * @brief Convert a @ref FrequencyBand to a corresponding frequency control
 *        bitmask value.
 *
 * For example:
 *
 * ```cpp
 * uint32_t mask = ToBitMask(FrequencyBand::L1);
 * ```
 *
 * generates the following bitmask:
 *
 * ```cpp
 * uint32_t mask = (1UL << static_cast<uint8_t>(FrequencyBand::L1));
 * ```
 *
 * @param type The desired frequency band.
 *
 * @return The corresponding bitmask.
 */
constexpr uint32_t ToBitMask(FrequencyBand type) {
  return (1U << (static_cast<uint8_t>(type)));
}

/**
 * @brief Convert two or more @ref FrequencyBand values to a bitmask.
 *
 * For example:
 *
 * ```cpp
 * uint32_t mask = ToBitMask(FrequencyBand::L1, FrequencyBand::L5);
 * ```
 *
 * generates the following bitmask:
 *
 * ```cpp
 * uint32_t mask = (1UL << static_cast<uint8_t>(FrequencyBand::L1)) |
 *                 (1UL << static_cast<uint8_t>(FrequencyBand::L5));
 * ```
 *
 * @tparam Args The type of the `others` values (@ref FrequencyBand)
 * @param first The first value.
 * @param others One or more additional values.
 *
 * @return The corresponding bitmask.
 */
template <typename... Args>
constexpr uint32_t ToBitMask(FrequencyBand first, Args... others) {
  return ToBitMask(first) | ToBitMask(others...);
}

/** @} */

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
