/**************************************************************************/ /**
 * @brief Point One FusionEngine output message common definitions.
 ******************************************************************************/

#pragma once

#include <cmath> // For NAN
#include <cstdint>
#include <cstring>

namespace point_one {
namespace messages {

// Enforce byte alignment and packing of all data structures and values.
#pragma pack(push, 1)

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
  IRNSS = 9
};

/**
 * @brief Navigation solution type definitions.
 */
enum class SolutionType : uint8_t {
  /** Invalid, no position available. */
  Invalid = 0,
  /** Autonomous GPS fix, no correction data used. */
  AutonomousGPS = 1,
  /** DGPS using a local base station or WAAS. */
  DGPS = 2,
  /** RTK fixed integers (one or more fixed). */
  RTKFixed = 4,
  /** RTK float integers. */
  RTKFloat = 5,
  /** Integrated position using dead reckoning. */
  Integrate = 6,
  /** Using vision measurements. */
  Visual = 9,
  /** Using PPP. */
  PPP = 10,
};

/**
 * @brief Identifiers for the defined output message types.
 */
enum class MessageType : uint16_t {
  INVALID = 0,

  // INS solution messages.
  POSE = 10000,
  GNSS_INFO = 10001,
};

/**
 * @brief Generic timestamp representation.
 *
 * This structure may be used to store Point One system time values (referenced
 * to the start of the device), UNIX times (referenced to January 1, 1970), or
 * GPS times (referenced to January 6, 1980).
 */
struct Timestamp {
  static constexpr uint32_t INVALID = 0xFFFFFFFF;

  /**
   * The number of full seconds since the epoch. Set to @ref P1_INVALID_TIME if
   * the timestamp is invalid or unknown.
   */
  uint32_t seconds = INVALID;

  /** The fractional part of the second, expressed in nanoseconds. */
  uint32_t fraction_ns = INVALID;
};

/**
 * @brief The header present at the beginning of every message.
 *
 * The header is followed immediately in the binary stream by the message
 * payload specified by @ref message_type.
 */
struct MessageHeader {
  static constexpr uint8_t SYNC0 = 0x2E; // '.'
  static constexpr uint8_t SYNC1 = 0x31; // '1'

  static constexpr uint32_t INVALID_SOURCE_ID = 0xFFFFFFFF;

  /** Message sync bytes: always set to ASCII `.1` (0x2E, 0x31). */
  uint8_t sync[2] = {SYNC0, SYNC1};

  /**
   * The 32-bit CRC of all bytes from and including the @ref protocol_version
   * field to the last byte in the message. This uses the standard CRC-32C
   * generator polynomial (0x1EDC6F41).
   */
  uint32_t crc = 0;

  /** The version of the P1 binary protocol being used. */
  uint8_t protocol_version = 2;

  /** Type identifier for the serialized message to follow. */
  MessageType message_type = MessageType::INVALID;

  /** The size of the serialized message (bytes). */
  uint32_t payload_size_bytes = 0;

  /** Identifies the source of the serialized data. */
  uint32_t source_identifier = INVALID_SOURCE_ID;
};

#pragma pack(pop)

/******************************************************************************/
inline std::string GetMessageTypeName(MessageType type) {
  switch (type) {
    case MessageType::INVALID:
      return "Invalid";

    case MessageType::POSE:
      return "Pose";

    case MessageType::GNSS_INFO:
      return "GNSS Info";

    default:
      return "Unrecognized Message (" + std::to_string((int)type) + ")";
  }
}

/******************************************************************************/
inline std::string GetSatelliteTypeName(SatelliteType type) {
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
      return "Invalid System (" + std::to_string((int)type) + ")";
  }
}

} // namespace point_one
} // namespace messages
