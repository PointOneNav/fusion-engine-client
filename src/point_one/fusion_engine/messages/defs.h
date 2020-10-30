/**************************************************************************/ /**
 * @brief Point One FusionEngine output message common definitions.
 * @file
 ******************************************************************************/

#pragma once

#include <cmath> // For NAN
#include <cstdint>
#include <ostream>
#include <string>

namespace point_one {
namespace fusion_engine {
namespace messages {

// Enforce 4-byte alignment and packing of all data structures and values so
// that floating point values are aligned on platforms that require it.
#pragma pack(push, 4)

/**
 * @defgroup enum_definitions Common Enumeration Definitions
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
 * @ingroup messages
 */
enum class MessageType : uint16_t {
  INVALID = 0, ///< Invalid message type

  // INS solution messages.
  POSE = 10000, ///< @ref PoseMessage
  GNSS_INFO = 10001, ///< @ref GNSSInfoMessage
  GNSS_SATELLITE = 10002, ///< @ref GNSSSatelliteMessage
  POSE_AUX = 10003, ///< @ref PoseAuxMessage

  // Sensor measurement messages.
  IMU_MEASUREMENT = 11000, ///< @ref IMUMeasurement

  // ROS messages.
  ROS_POSE = 12000, ///< @ref ros::PoseMessage
  ROS_GPS_FIX = 12010, ///< @ref ros::GPSFixMessage
  ROS_IMU = 12011, ///< @ref ros::IMUMessage
};

/** @} */

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
   * The number of full seconds since the epoch. Set to @ref INVALID if
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

  /**
   * The maximum expected message size (in bytes), used for sanity checking.
   */
  static const size_t MAX_MESSAGE_SIZE_BYTES = (1 << 24);

  /** Message sync bytes: always set to ASCII `.1` (0x2E, 0x31). */
  uint8_t sync[2] = {SYNC0, SYNC1};

  uint8_t reserved[2] = {0};

  /**
   * The 32-bit CRC of all bytes from and including the @ref protocol_version
   * field to the last byte in the message, including the message payload. This
   * uses the standard CRC-32 generator polynomial in reversed order
   * (0xEDB88320).
   *
   * See also @ref crc_support.
   */
  uint32_t crc = 0;

  /** The version of the P1 binary protocol being used. */
  uint8_t protocol_version = 2;

  uint8_t reserved_1 = 0;

  /** Type identifier for the serialized message to follow. */
  MessageType message_type = MessageType::INVALID;

  /** The sequence number of this message. */
  uint32_t sequence_number = 0;

  /** The size of the serialized message (bytes). */
  uint32_t payload_size_bytes = 0;

  /** Identifies the source of the serialized data. */
  uint32_t source_identifier = INVALID_SOURCE_ID;
};

#pragma pack(pop)

/**
 * @brief Get a human-friendly string name for the specified @ref SatelliteType
 *        (GNSS constellation).
 * @ingroup enum_definitions
 *
 * @param type The desired satellite type.
 *
 * @return The corresponding string name.
 */
inline std::string to_string(SatelliteType type) {
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

/**
 * @brief @ref SatelliteType stream operator.
 * @ingroup enum_definitions
 */
inline std::ostream& operator<<(std::ostream& stream, SatelliteType type) {
  return (stream << to_string(type));
}

/**
 * @brief Get a human-friendly string name for the specified @ref MessageType.
 * @ingroup enum_definitions
 *
 * @param type The desired message type.
 *
 * @return The corresponding string name.
 */
inline std::string to_string(MessageType type) {
  switch (type) {
    case MessageType::INVALID:
      return "Invalid";

    case MessageType::POSE:
      return "Pose";

    case MessageType::GNSS_INFO:
      return "GNSS Info";

    case MessageType::GNSS_SATELLITE:
      return "GNSS Satellite";

    case MessageType::POSE_AUX:
      return "Pose Auxiliary";

    case MessageType::IMU_MEASUREMENT:
      return "IMU Measurement";

    case MessageType::ROS_POSE:
      return "ROS Pose";

    case MessageType::ROS_GPS_FIX:
      return "ROS GPSFix";

    case MessageType::ROS_IMU:
      return "ROS IMU";

    default:
      return "Unrecognized Message (" + std::to_string((int)type) + ")";
  }
}

/**
 * @brief @ref MessageType stream operator.
 * @ingroup enum_definitions
 */
inline std::ostream& operator<<(std::ostream& stream, MessageType type) {
  return (stream << to_string(type));
}

/**
 * @brief Get a human-friendly string name for the specified @ref SolutionType.
 * @ingroup enum_definitions
 *
 * @param type The desired message type.
 *
 * @return The corresponding string name.
 */
inline std::string to_string(SolutionType type) {
  switch (type) {
    case SolutionType::Invalid:
      return "Invalid";

    case SolutionType::AutonomousGPS:
      return "Stand Alone GNSS";

    case SolutionType::DGPS:
      return "Differential GNSS";

    case SolutionType::RTKFixed:
      return "Fixed RTK GNSS";

    case SolutionType::RTKFloat:
      return "Real-valued Ambiguity RTK GNSS";

    case SolutionType::Integrate:
      return "Dead Reckoning";

    case SolutionType::Visual:
      return "Visual Navigation";

    case SolutionType::PPP:
      return "PPP GNSS";

    default:
      return "Unrecognized Solution Type (" + std::to_string((int)type) + ")";
  }
}

/**
 * @brief @ref SolutionType stream operator.
 * @ingroup enum_definitions
 */
inline std::ostream& operator<<(std::ostream& stream, SolutionType type) {
  return (stream << to_string(type));
}

/**
 * @defgroup messages Message Definitions
 * @brief Type definitions for all defined messages.
 *
 * See also @ref MessageType.
 */

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
