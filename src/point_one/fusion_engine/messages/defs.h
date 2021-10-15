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

// Enforce 4-byte alignment and packing of all data structures and values.
// Floating point values are aligned on platforms that require it. This is done
// with a combination of setting struct attributes, and manual alignment
// within the definitions. See the "Message Packing" section of the README.
#pragma pack(push, 1)

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
  IRNSS = 9,
  MAX_VALUE = IRNSS,
};

/**
 * @brief Navigation solution type definitions.
 */
enum class SolutionType : uint8_t {
  /** Invalid, no position available. */
  Invalid = 0,
  /** Standalone GNSS fix, no correction data used. */
  AutonomousGPS = 1,
  /**
   * Differential GNSS pseudorange solution using a local RTK base station or
   * SSR or SBAS corrections.
   */
  DGPS = 2,
  /**
   * GNSS RTK solution with fixed integer carrier phase ambiguities (one or more
   * signals fixed).
   */
  RTKFixed = 4,
  /** GNSS RTK solution with floating point carrier phase ambiguities. */
  RTKFloat = 5,
  /** Integrated position using dead reckoning. */
  Integrate = 6,
  /** Using vision measurements. */
  Visual = 9,
  /**
   * GNSS precise point positioning (PPP) pseudorange/carrier phase solution.
   */
  PPP = 10,
  MAX_VALUE = PPP,
};

/**
 * @brief Identifiers for the defined output message types.
 * @ingroup messages
 */
enum class MessageType : uint16_t {
  INVALID = 0, ///< Invalid message type

  // Navigation solution messages.
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

  // Command and control messages.
  COMMAND_RESPONSE = 13000, ///< @ref CommandResponseMessage
  MESSAGE_REQUEST = 13001, ///< @ref MessageRequest
  RESET_REQUEST = 13002, ///< @ref ResetRequest
  VERSION_INFO = 13003, ///< @ref VersionInfoMessage
  EVENT_NOTIFICATION = 13004, ///< @ref EventNotificationMessage

  SET_CONFIG = 13100, ///< @ref SetConfigMessage
  GET_CONFIG = 13101, ///< @ref GetConfigMessage
  SAVE_CONFIG = 13102, ///< @ref SaveConfigMessage
  CONFIG_DATA = 13103, ///< @ref ConfigDataMessage

  MAX_VALUE = CONFIG_DATA, ///< The maximum defined @ref MessageType enum value.
};

/** @} */

/**
 * @brief Generic timestamp representation.
 *
 * This structure may be used to store Point One system time values (referenced
 * to the start of the device), UNIX times (referenced to January 1, 1970), or
 * GPS times (referenced to January 6, 1980).
 */
struct alignas(4) Timestamp {
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
 * @ingroup messages
 *
 * The header is followed immediately in the binary stream by the message
 * payload specified by @ref message_type.
 */
struct alignas(4) MessageHeader {
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

  /**
   * The version of the message type specified by @ref message_type to follow.
   */
  uint8_t message_version = 0;

  /** Type identifier for the serialized message to follow. */
  MessageType message_type = MessageType::INVALID;

  /** The sequence number of this message. */
  uint32_t sequence_number = 0;

  /** The size of the serialized message (bytes). */
  uint32_t payload_size_bytes = 0;

  /** Identifies the source of the serialized data. */
  uint32_t source_identifier = INVALID_SOURCE_ID;
};

/**
 * @brief The base class for all message payloads.
 * @ingroup messages
 */
struct MessagePayload {
  // Currently empty - used simply to distinguish between payload definitions
  // and other types.
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

/**
 * @brief Get a human-friendly string name for the specified @ref MessageType.
 * @ingroup enum_definitions
 *
 * @param type The desired message type.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(MessageType type) {
  switch (type) {
    case MessageType::INVALID:
      return "Invalid";

    // Navigation solution messages.
    case MessageType::POSE:
      return "Pose";

    case MessageType::GNSS_INFO:
      return "GNSS Info";

    case MessageType::GNSS_SATELLITE:
      return "GNSS Satellite";

    case MessageType::POSE_AUX:
      return "Pose Auxiliary";

    // Sensor measurement messages.
    case MessageType::IMU_MEASUREMENT:
      return "IMU Measurement";

    // ROS messages.
    case MessageType::ROS_POSE:
      return "ROS Pose";

    case MessageType::ROS_GPS_FIX:
      return "ROS GPSFix";

    case MessageType::ROS_IMU:
      return "ROS IMU";

    // Command and control messages.
    case MessageType::COMMAND_RESPONSE:
      return "Command Response";

    case MessageType::MESSAGE_REQUEST:
      return "Message Transmission Request";

    case MessageType::RESET_REQUEST:
      return "Reset Request";

    case MessageType::VERSION_INFO:
      return "Version Information";

    case MessageType::EVENT_NOTIFICATION:
      return "Event Notification";

    case MessageType::SET_CONFIG:
      return "Set Configuration Parameter";

    case MessageType::GET_CONFIG:
      return "Get Configuration Parameter";

    case MessageType::SAVE_CONFIG:
      return "Save Configuration";

    case MessageType::CONFIG_DATA:
      return "Configuration Parameter Value";

    default:
      return "Unrecognized Message";
  }
}

/**
 * @brief @ref MessageType stream operator.
 * @ingroup enum_definitions
 */
inline std::ostream& operator<<(std::ostream& stream, MessageType type) {
  stream << to_string(type) << " (" << (int)type << ")";
  return stream;
}

/**
 * @brief Get a human-friendly string name for the specified @ref SolutionType.
 * @ingroup enum_definitions
 *
 * @param type The desired message type.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(SolutionType type) {
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
      return "Unrecognized Solution Type";
  }
}

/**
 * @brief @ref SolutionType stream operator.
 * @ingroup enum_definitions
 */
inline std::ostream& operator<<(std::ostream& stream, SolutionType type) {
  stream << to_string(type) << " (" << (int)type << ")";
  return stream;
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
