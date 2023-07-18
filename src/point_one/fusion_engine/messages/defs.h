/**************************************************************************/ /**
 * @brief Point One FusionEngine output message common definitions.
 * @file
 ******************************************************************************/

#pragma once

#include <cmath> // For NAN
#include <cstdint>
#include <string>

#include "point_one/fusion_engine/common/portability.h"
#include "point_one/fusion_engine/messages/signal_defs.h"

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
  CALIBRATION_STATUS = 10004, ///< @ref CalibrationStatusMessage
  RELATIVE_ENU_POSITION = 10005, ///< @ref RelativeENUPositionMessage

  // Device status messages.
  SYSTEM_STATUS = 10500, ///< @ref SystemStatusMessage

  // Sensor measurement messages.
  IMU_OUTPUT = 11000, ///< @ref IMUOutput
  RAW_HEADING_OUTPUT = 11001, ///< @ref RawHeadingOutput
  RAW_IMU_OUTPUT = 11002, ///< @ref RawIMUOutput
  HEADING_OUTPUT = 11003, ///< @ref HeadingOutput

  // Vehicle measurement messages.
  DEPRECATED_WHEEL_SPEED_MEASUREMENT =
      11101, ///< @ref DeprecatedWheelSpeedMeasurement
  DEPRECATED_VEHICLE_SPEED_MEASUREMENT =
      11102, ///< @ref DeprecatedVehicleSpeedMeasurement

  WHEEL_TICK_INPUT = 11103, ///< @ref WheelTickInput
  VEHICLE_TICK_INPUT = 11104, ///< @ref VehicleTickInput
  WHEEL_SPEED_INPUT = 11105, ///< @ref WheelSpeedInput
  VEHICLE_SPEED_INPUT = 11106, ///< @ref VehicleSpeedInput

  RAW_WHEEL_TICK_OUTPUT = 11123, ///< @ref RawWheelTickOutput
  RAW_VEHICLE_TICK_OUTPUT = 11124, ///< @ref RawVehicleTickOutput
  RAW_WHEEL_SPEED_OUTPUT = 11125, ///< @ref RawWheelSpeedOutput
  RAW_VEHICLE_SPEED_OUTPUT = 11126, ///< @ref RawVehicleSpeedOutput

  WHEEL_SPEED_OUTPUT = 11135, ///< @ref WheelSpeedOutput
  VEHICLE_SPEED_OUTPUT = 11136, ///< @ref VehicleSpeedOutput

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
  SHUTDOWN_REQUEST = 13005, ///< @ref ShutdownRequest
  FAULT_CONTROL = 13006, ///< @ref FaultControlMessage
  DEVICE_ID = 13007, ///< @ref DeviceIDMessage
  STARTUP_REQUEST = 13008, ///< @ref StartupRequest

  SET_CONFIG = 13100, ///< @ref SetConfigMessage
  GET_CONFIG = 13101, ///< @ref GetConfigMessage
  SAVE_CONFIG = 13102, ///< @ref SaveConfigMessage
  CONFIG_RESPONSE = 13103, ///< @ref ConfigResponseMessage

  IMPORT_DATA = 13110, ///< @ref ImportDataMessage
  EXPORT_DATA = 13111, ///< @ref ExportDataMessage
  PLATFORM_STORAGE_DATA = 13113, ///< @ref PlatformStorageDataMessage

  SET_MESSAGE_RATE = 13220, ///< @ref SetMessageRate
  GET_MESSAGE_RATE = 13221, ///< @ref GetMessageRate
  MESSAGE_RATE_RESPONSE = 13222, ///< @ref MessageRateResponse

  LBAND_FRAME = 14000, ///< @ref LBandFrameMessage

  /// The maximum defined @ref MessageType enum value.
  MAX_VALUE = LBAND_FRAME,
};

/**
 * @brief Get a human-friendly string name for the specified @ref MessageType.
 * @ingroup enum_definitions
 *
 * @param type The desired message type.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(MessageType type) {
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

    case MessageType::CALIBRATION_STATUS:
      return "Calibration Status";

    case MessageType::RELATIVE_ENU_POSITION:
      return "Relative ENU Position";

    // Device status messages.
    case MessageType::SYSTEM_STATUS:
      return "System Status";

    // Sensor measurement messages.
    case MessageType::IMU_OUTPUT:
      return "IMU Output";

    case MessageType::RAW_HEADING_OUTPUT:
      return "Raw heading output";

    case MessageType::RAW_IMU_OUTPUT:
      return "Raw IMU Output";

    case MessageType::HEADING_OUTPUT:
      return "Heading Output";

    case MessageType::DEPRECATED_WHEEL_SPEED_MEASUREMENT:
      return "Wheel Speed Measurement";

    case MessageType::DEPRECATED_VEHICLE_SPEED_MEASUREMENT:
      return "Vehicle Speed Measurement";

    case MessageType::WHEEL_TICK_INPUT:
      return "Wheel Tick Input";

    case MessageType::VEHICLE_TICK_INPUT:
      return "Vehicle Tick Input";

    case MessageType::WHEEL_SPEED_INPUT:
      return "Wheel Speed Input";

    case MessageType::VEHICLE_SPEED_INPUT:
      return "Vehicle Speed Input";

    case MessageType::RAW_WHEEL_TICK_OUTPUT:
      return "Raw Wheel Tick Output";

    case MessageType::RAW_VEHICLE_TICK_OUTPUT:
      return "Raw Vehicle Tick Output";

    case MessageType::RAW_WHEEL_SPEED_OUTPUT:
      return "Raw Wheel Speed Output";

    case MessageType::RAW_VEHICLE_SPEED_OUTPUT:
      return "Raw Vehicle Speed Output";

    case MessageType::WHEEL_SPEED_OUTPUT:
      return "Wheel Speed Output";

    case MessageType::VEHICLE_SPEED_OUTPUT:
      return "Vehicle Speed Output";

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

    case MessageType::SHUTDOWN_REQUEST:
      return "Shutdown Request";

    case MessageType::STARTUP_REQUEST:
      return "Startup Request";

    case MessageType::DEVICE_ID:
      return "Device ID Information";

    case MessageType::FAULT_CONTROL:
      return "Fault Control";

    case MessageType::SET_CONFIG:
      return "Set Configuration Parameter";

    case MessageType::GET_CONFIG:
      return "Get Configuration Parameter";

    case MessageType::SAVE_CONFIG:
      return "Save Configuration";

    case MessageType::CONFIG_RESPONSE:
      return "Configuration Parameter Value";

    case MessageType::SET_MESSAGE_RATE:
      return "Set Message Rate";

    case MessageType::GET_MESSAGE_RATE:
      return "Get Message Rate";

    case MessageType::MESSAGE_RATE_RESPONSE:
      return "Message Rate Response";

    case MessageType::IMPORT_DATA:
      return "Import Data To Device";

    case MessageType::EXPORT_DATA:
      return "Export Data From Device";

    case MessageType::PLATFORM_STORAGE_DATA:
      return "Platform Data Contents";

    case MessageType::LBAND_FRAME:
      return "L-band Frame Contents";
  }
  return "Unrecognized Message";
}

/**
 * @brief @ref MessageType stream operator.
 * @ingroup enum_definitions
 */
inline p1_ostream& operator<<(p1_ostream& stream, MessageType type) {
  stream << to_string(type) << " (" << (int)type << ")";
  return stream;
}

/**
 * @brief Check if the specified message type is a user command.
 * @ingroup messages
 *
 * See also @ref IsResponse().
 *
 * @param message_type The message type in question.
 *
 * @return `true` if the message is a FusionEngine command.
 */
P1_CONSTEXPR_FUNC bool IsCommand(MessageType message_type) {
  switch (message_type) {
    case MessageType::MESSAGE_REQUEST:
    case MessageType::RESET_REQUEST:
    case MessageType::SHUTDOWN_REQUEST:
    case MessageType::FAULT_CONTROL:
    case MessageType::SET_CONFIG:
    case MessageType::GET_CONFIG:
    case MessageType::SAVE_CONFIG:
    case MessageType::IMPORT_DATA:
    case MessageType::EXPORT_DATA:
    case MessageType::SET_MESSAGE_RATE:
    case MessageType::GET_MESSAGE_RATE:
      return true;
    default:
      return false;
  }
}

/**
 * @brief Check if the specified message type is a response to a user command.
 * @ingroup messages
 *
 * See also @ref IsCommand().
 *
 * @param message_type The message type in question.
 *
 * @return `true` if the message is a FusionEngine command response.
 */
P1_CONSTEXPR_FUNC bool IsResponse(MessageType message_type) {
  switch (message_type) {
    case MessageType::COMMAND_RESPONSE:
    case MessageType::CONFIG_RESPONSE:
    case MessageType::MESSAGE_RATE_RESPONSE:
      return true;
    default:
      return false;
  }
}

/** @brief Command response status indicators. */
enum class Response : uint8_t {
  OK = 0,
  /**
   * A version specified in the command or subcommand could not be handled.
   * This could mean that the version was too new, or it was old and there was
   * not a translation for it.
   */
  UNSUPPORTED_CMD_VERSION = 1,
  /**
   * The command interacts with a feature that is not present on the target
   * device (e.g., Setting the baud rate on a device without a serial port).
   */
  UNSUPPORTED_FEATURE = 2,
  /**
   * One or more values in the command were not in acceptable ranges (e.g., An
   * undefined enum value, or an invalid baud rate).
   */
  VALUE_ERROR = 3,
  /**
   * The command would require adding too many elements to an internal
   * storage.
   */
  INSUFFICIENT_SPACE = 4,
  /**
   * There was a runtime failure executing the command.
   */
  EXECUTION_FAILURE = 5,
  /**
   * The header `payload_size_bytes` is in conflict with the size of the
   * message based on its type and type specific length fields.
   */
  INCONSISTENT_PAYLOAD_LENGTH = 6,
  /**
   * Requested data was corrupted and not available.
   */
  DATA_CORRUPTED = 7,
  /**
   * The requested data isn't available.
   */
  NO_DATA_STORED = 8,
  /**
   * The device is in a state where it can't process the command.
   */
  UNAVAILABLE = 9,
};

/**
 * @brief Get a human-friendly string name for the specified @ref Response.
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(Response val) {
  switch (val) {
    case Response::OK:
      return "Ok";
    case Response::UNSUPPORTED_CMD_VERSION:
      return "Unsupported Command Version";
    case Response::UNSUPPORTED_FEATURE:
      return "Unsupported Feature";
    case Response::VALUE_ERROR:
      return "Value Error";
    case Response::INSUFFICIENT_SPACE:
      return "Insufficient Space";
    case Response::EXECUTION_FAILURE:
      return "Execution Failure";
    case Response::INCONSISTENT_PAYLOAD_LENGTH:
      return "Inconsistent Payload Length";
    case Response::DATA_CORRUPTED:
      return "Data Corrupted";
    case Response::NO_DATA_STORED:
      return "No Data Stored";
    case Response::UNAVAILABLE:
      return "Device Unavailable";
    default:
      return "Unrecognized";
  }
}

/**
 * @brief @ref Response stream operator.
 */
inline p1_ostream& operator<<(p1_ostream& stream, Response val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief Navigation solution type definitions.
 */
enum class SolutionType : uint8_t {
  /** Invalid, no position available. */
  Invalid = 0,
  /** Standalone GNSS fix, no GNSS corrections data used. */
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
 * @brief Get a human-friendly string name for the specified @ref SolutionType.
 * @ingroup enum_definitions
 *
 * @param type The desired message type.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(SolutionType type) {
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
inline p1_ostream& operator<<(p1_ostream& stream, SolutionType type) {
  stream << to_string(type) << " (" << (int)type << ")";
  return stream;
}

/** @} */

/**
 * @brief Generic timestamp representation.
 *
 * This structure may be used to store Point One system time values (referenced
 * to the start of the device), UNIX times (referenced to January 1, 1970), or
 * GPS times (referenced to January 6, 1980).
 */
struct P1_ALIGNAS(4) Timestamp {
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
struct P1_ALIGNAS(4) MessageHeader {
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
 * @brief Check if the specified message is a user command.
 * @ingroup messages
 *
 * See @ref IsCommand() for details.
 *
 * @param header Header of a received FusionEngine message.
 *
 * @return `true` if the message is a FusionEngine command.
 */
P1_CONSTEXPR_FUNC bool IsCommand(const MessageHeader& header) {
  return IsCommand(header.message_type);
}

/**
 * @brief Check if the specified message type is a response to a user command.
 * @ingroup messages
 *
 * See @ref IsResponse() for details.
 *
 * @param header Header of a received FusionEngine message.
 *
 * @return `true` if the message is a FusionEngine command response.
 */
P1_CONSTEXPR_FUNC bool IsResponse(const MessageHeader& header) {
  return IsResponse(header.message_type);
}

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
 * @defgroup messages Message Definitions
 * @brief Type definitions for all defined messages.
 *
 * See also @ref MessageType.
 */

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
