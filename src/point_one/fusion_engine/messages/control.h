/**************************************************************************/ /**
 * @brief Device operation control messages.
 * @file
 ******************************************************************************/

#pragma once

// If we are compiling under MSVC, disable warning C4200:
//   nonstandard extension used: zero-sized array in struct/union
// Zero-sized arrays are supported by MSVC, GCC, and Clang, and we use them as
// convenience placeholders for variable sized message payloads.
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable: 4200)
#endif

#include "point_one/fusion_engine/messages/defs.h"

namespace point_one {
namespace fusion_engine {
namespace messages {

// Enforce 4-byte alignment and packing of all data structures and values.
// Floating point values are aligned on platforms that require it. This is done
// with a combination of setting struct attributes, and manual alignment
// within the definitions. See the "Message Packing" section of the README.
#pragma pack(push, 1)

/**
 * @defgroup config_and_ctrl_messages Device Configuration and Control Message Definitions
 * @brief Messages for controlling device configuration and operation.
 * @ingroup messages
 *
 * When a configuration/control message is received, a device typically responds
 * with either a @ref CommandResponseMessage or another appropriate response.
 * For example, a @ref MessageRequest requesting @ref MessageType::VERSION_INFO
 * may result in a @ref VersionInfoMessage response, or a @ref
 * CommandResponseMessage indicating that directly requesting version messages
 * is not supported. See the documentation for the individual control messages
 * for details on the expected response.
 *
 * See also @ref messages.
 */

/**
 * @brief Response to indicate if command was processed successfully (@ref
 *        MessageType::COMMAND_RESPONSE, version 1.0).
 * @ingroup config_and_ctrl_messages
 */
struct alignas(4) CommandResponseMessage : public MessagePayload {
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
  };

  static constexpr MessageType MESSAGE_TYPE = MessageType::COMMAND_RESPONSE;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The sequence number of the command that triggered this response. */
  uint32_t source_seq_number = 0;

  /** The response status (success, error, etc.). */
  Response response = Response::OK;

  uint8_t reserved[3] = {0};
};

/**
 * @brief Request transmission of a specified message type, (@ref
 *        MessageType::MESSAGE_REQUEST, version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * On success, the device will output the requested message type.
 *
 * Not all message types may be requested explicitly. If a message type cannot
 * be requested on demand or is not supported, the device will respond with a
 * @ref CommandResponseMessage::Response::UNSUPPORTED_FEATURE message.
 *
 * @note
 * The generated response may not immediately follow the request if other
 * outbound messages are already enqueued to be sent.
 */
struct alignas(4) MessageRequest : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::MESSAGE_REQUEST;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The desired message type. */
  MessageType message_type = MessageType::INVALID;

  uint8_t reserved[2] = {0};
};

/**
 * @brief Perform a software or hardware reset (@ref MessageType::RESET_REQUEST,
 *        version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * This message contains a bitmask indicating the set of components to be reset.
 * Helper bitmasks are provided for common reset operations.
 */
struct alignas(4) ResetRequest : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::RESET_REQUEST;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * @name Runtime State Reset
   * @{
   */
  /** Restart the navigation engine, but do not clear its position estimate. */
  static constexpr uint32_t RESTART_NAVIGATION_ENGINE = 0x00000001;
  /** Delete all GNSS corrections information. */
  static constexpr uint32_t RESET_CORRECTIONS = 0x00000002;
  /** @} */

  /**
   * @name Clear Short Lived Data
   * @{
   */
  /**
   * Reset the navigation engine's estimate of position, velocity, and
   * orientation.
   */
  static constexpr uint32_t RESET_POSITION_DATA = 0x00000100;
  /** Delete all saved satellite ephemeris. */
  static constexpr uint32_t RESET_EPHEMERIS = 0x00000200;
  /** @} */

  /**
   * @name Clear Long Lived Data
   * @{
   */
  /**
   * Reset all stored navigation engine data, including position, velocity, and
   * orientation state, as well as training data.
   */
  static constexpr uint32_t RESET_NAVIGATION_ENGINE_DATA = 0x00001000;
  /**
   * Reset the device calibration data.
   *
   * @note
   * This does _not_ reset any existing navigation engine state. It is
   * recommended that you set @ref RESET_NAVIGATION_ENGINE_DATA as well under
   * normal circumstances.
   */
  static constexpr uint32_t RESET_CALIBRATION_DATA = 0x00002000;
  /** @} */

  /**
   * @name Clear Configuration Data
   * @{
   */
  /** Clear all configuration data. */
  static constexpr uint32_t RESET_CONFIG = 0x00100000;
  /** @} */

  /**
   * @name Device Reset Bitmasks
   * @{
   */
  /**
   * Perform a device hot start: reload the navigation engine and clear all
   * runtime data (GNSS corrections, etc.), but do not reset any saved state
   * data (position, orientation, training parameters, calibration, etc.).
   *
   * A hot start is typically used to restart the navigation engine in a
   * deterministic state, particularly for logging purposes.
   */
  static constexpr uint32_t HOT_START = 0x000000FF;

  /**
   * Perform a device warm start: reload the navigation engine, resetting the
   * saved position, velocity, and orientation, but do not reset training
   * parameters or calibration data.
   *
   * A warm start is typically used to reset the device's position estimate in
   * case of error.
   */
  static constexpr uint32_t WARM_START = 0x000001FF;

  /**
   * Perform a device cold start: reset the navigation engine including saved
   * position, velocity, and orientation state, but do not reset training data,
   * calibration data, or user configuration parameters.
   *
   * @note
   * To reset training or calibration data as well, set the @ref
   * RESET_NAVIGATION_ENGINE_DATA and @ref RESET_CALIBRATION_DATA bits.
   */
  static constexpr uint32_t COLD_START = 0x00000FFF;

  /**
   * Restart mask to set all persistent data, including calibration and user
   * configuration, back to factory defaults.
   *
   * Note: Upper 8 bits reserved for future use (e.g., hardware reset).
   */
  static constexpr uint32_t FACTORY_RESET = 0x00FFFFFF;
  /** @} */

  /** Bit mask of functionality to reset. */
  uint32_t reset_mask = 0;
};

/**
 * @brief Software and hardware version information, (@ref
 *        MessageType::VERSION_INFO, version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * This message contains version strings for each of the following, where
 * available:
 * - Firmware - The current version of the platform software/firmware being used
 * - Engine - The version of Point One FusionEngine being used
 * - Hardware - The version of the platform hardware being used
 * - GNSS Receiver - The version of firmware being used by the device's GNSS
 *   receiver
 *
 * The message payload specifies the length of each string (in bytes). It is
 * followed by each of the listed version strings consecutively. The strings are
 * _not_ null terminated.
 *
 * ```
 * {MessageHeader, VersionInfoMessage, "Firmware Version", "Engine Version",
 *  "Hardware Version", "Receiver Version"}
 * ```
 */
struct alignas(4) VersionInfoMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::VERSION_INFO;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The current system timestamp (in ns).*/
  int64_t system_time_ns = 0;

  /** The length of the firmware version string (in bytes). */
  uint8_t fw_version_length = 0;

  /** The length of the FusionEngine version string (in bytes). */
  uint8_t engine_version_length = 0;

  /** The length of the hardware version string (in bytes). */
  uint8_t hw_version_length = 0;

  /** The length of the GNSS receiver version string (in bytes). */
  uint8_t rx_version_length = 0;

  uint8_t reserved[4] = {0};

  /**
   * The beginning of the firmware version string.
   *
   * All other version strings follow immediately after this one in the data
   * buffer. For example, the FusionEngine version string can be obtained as
   * follows:
   * ```cpp
   * std::string engine_version_str(
   *     fw_version_str + message.fw_version_length,
   *     message.engine_version_length);
   * ```
   */
  char fw_version_str[0];
};

/**
 * @brief Notification of a system event for logging purposes (@ref
 *        MessageType::EVENT_NOTIFICATION, version 1.0).
 * @ingroup config_and_ctrl_messages
 */
struct alignas(4) EventNotificationMessage : public MessagePayload {
  enum class EventType : uint8_t {
    LOG = 0,
    RESET = 1,
    CONFIG_CHANGE = 2,
  };

  static const char* to_string(EventType type) {
    switch (type) {
      case EventType::LOG:
        return "Log";

      case EventType::RESET:
        return "Reset";

      case EventType::CONFIG_CHANGE:
        return "Config Change";

      default:
        return "Unknown";
    }
  }

  static constexpr MessageType MESSAGE_TYPE = MessageType::EVENT_NOTIFICATION;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The type of event that occurred. */
  EventType type = EventType::LOG;

  uint8_t reserved1[3] = {0};

  /** The current system timestamp (in ns).*/
  int64_t system_time_ns = 0;

  /** A bitmask of flags associated with the event. */
  uint64_t event_flags = 0;

  /** The number of bytes in the @ref event_description string. */
  uint16_t event_description_len_bytes = 0;

  uint8_t reserved2[2] = {0};

  /**
   * This is a dummy entry to provide a pointer to this offset.
   *
   * This is used for populating string describing the event, where applicable.
   */
  char* event_description[0];
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one

#ifdef _MSC_VER
#pragma warning(pop)
#endif
