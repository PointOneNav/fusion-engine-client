/**************************************************************************/ /**
 * @brief Device status messages.
 * @file
 ******************************************************************************/

#pragma once

#include "point_one/fusion_engine/common/portability.h"
#include "point_one/fusion_engine/messages/defs.h"

namespace point_one {
namespace fusion_engine {
namespace messages {

// Enforce 4-byte alignment and packing of all data structures and values.
// Floating point values are aligned on platforms that require it. This is done
// with a combination of setting struct attributes, and manual alignment
// within the definitions. See the "Message Packing" section of the README.
#pragma pack(push, 1)

/**************************************************************************/ /**
 * @defgroup device_status Device Status/Information Messages
 * @brief Messages for indicating high-level device status (notifications,
 *        software version, etc.).
 * @ingroup messages
 * @ingroup config_and_ctrl_messages
 *
 * See also @ref messages and @ref config_and_ctrl_messages.
 ******************************************************************************/

/**
 * @brief Software version information, (@ref
 *        MessageType::VERSION_INFO, version 1.0).
 * @ingroup device_status
 *
 * This message contains version strings for each of the following, where
 * available:
 * - Firmware - The current version of the platform software/firmware being used
 * - Engine - The version of Point One FusionEngine being used
 * - OS - The version of the operating system/kernel/bootloader being used
 * - GNSS Receiver - The version of firmware being used by the device's GNSS
 *   receiver
 *
 * The message payload specifies the length of each string (in bytes). It is
 * followed by each of the listed version strings consecutively. The strings are
 * _not_ null-terminated.
 *
 * ```
 * {MessageHeader, VersionInfoMessage, "Firmware Version", "Engine Version",
 *  "OS Version", "Receiver Version"}
 * ```
 *
 * The following is an example of extracting the firmware and engine version
 * strings from a byte array containing the entire message:
 * ```cpp
 * auto message = *reinterpret_cast<const VersionInfoMessage*>(buffer);
 * buffer += sizeof(VersionInfoMessage);
 * std::string fw_version(buffer, message.fw_version_length);
 * buffer += message.fw_version_length;
 * std::string engine_version(buffer, message.engine_version_length);
 * ```
 */
struct P1_ALIGNAS(4) VersionInfoMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::VERSION_INFO;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The current system timestamp (in ns).*/
  int64_t system_time_ns = 0;

  /** The length of the firmware version string (in bytes). */
  uint8_t fw_version_length = 0;

  /** The length of the FusionEngine version string (in bytes). */
  uint8_t engine_version_length = 0;

  /** The length of the OS version string (in bytes). */
  uint8_t os_version_length = 0;

  /** The length of the GNSS receiver version string (in bytes). */
  uint8_t rx_version_length = 0;

  uint8_t reserved[4] = {0};
};

/**
 * @brief Identifies a FusionEngine device.
 * @ingroup device_status
 */
enum class DeviceType : uint8_t {
  /** Unable to map device to a defined entry. */
  UNKNOWN = 0,
  /** Point One Atlas. */
  ATLAS = 1,
  /** Quectel LG69T-AM system. */
  LG69T_AM = 2,
  /** Quectel LG69T-AP system. */
  LG69T_AP = 3,
  /** Quectel LG69T-AH system. */
  LG69T_AH = 4,
  /** Nexar Beam2K system. */
  NEXAR_BEAM2K = 5,
  /** Point One SSR client running on an LG69T platform. */
  SSR_LG69T = 6,
  /** Point One SSR client running on a desktop platform. */
  SSR_DESKTOP = 7,
};

/**
 * @brief Get a human-friendly string name for the specified @ref DeviceType.
 * @ingroup device_status
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(DeviceType val) {
  switch (val) {
    case DeviceType::UNKNOWN:
      return "Unknown";
    case DeviceType::ATLAS:
      return "ATLAS";
    case DeviceType::LG69T_AM:
      return "LG69T_AM";
    case DeviceType::LG69T_AP:
      return "LG69T_AP";
    case DeviceType::LG69T_AH:
      return "LG69T_AH";
    case DeviceType::NEXAR_BEAM2K:
      return "NEXAR_BEAM2K";
    case DeviceType::SSR_LG69T:
      return "SSR_LG69T";
    case DeviceType::SSR_DESKTOP:
      return "SSR_DESKTOP";
  }
  return "Unrecognized";
}

/**
 * @brief @ref DeviceType stream operator.
 * @ingroup measurement_messages
 */
inline p1_ostream& operator<<(p1_ostream& stream, DeviceType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief Device identifier information (@ref MessageType::DEVICE_ID, version
 *        1.0).
 * @ingroup device_status
 *
 * This message contains ID fields for each of the following, where applicable.
 * - Hardware - A unique ROM identifier pulled from the device hardware (for
 *   example, a CPU serial number)
 * - User - A value set by the user to identify a device
 * - Receiver - A unique ROM identifier pulled from the GNSS receiver
 *
 * The message payload specifies the length of each field (in bytes), and is
 * followed by each of the ID values. ID values may be strings or binary,
 * depending on the type of device (@ref device_type). Strings are _not_
 * null-terminated.
 *
 * ```
 * {MessageHeader, DeviceIDMessage, "HW ID", "User ID", "Receiver ID"}
 * ```
 *
 * The following is an example of extracting the hardware and user IDs from a
 * byte array containing the entire message (assuming both are strings for this
 * example device):
 * ```cpp
 * auto message = *reinterpret_cast<const DeviceIDMessage*>(buffer);
 * buffer += sizeof(DeviceIDMessage);
 * std::string hw_id(buffer, message.hw_id_length);
 * buffer += message.hw_id_length;
 * std::string user_id(buffer, message.user_id_length);
 * ```
 */
struct P1_ALIGNAS(4) DeviceIDMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::DEVICE_ID;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The current system timestamp (in ns).*/
  int64_t system_time_ns = 0;

  /** The type of device this message originated from.*/
  DeviceType device_type = DeviceType::UNKNOWN;

  /** The length of the harware ID (in bytes). */
  uint8_t hw_id_length = 0;

  /** The length of the user specified ID (in bytes). */
  uint8_t user_id_length = 0;

  /** The length of the GNSS receiver ID (in bytes). */
  uint8_t receiver_id_length = 0;

  uint8_t reserved[4] = {0};
};

/**
 * @brief Notification of a system event for logging purposes (@ref
 *        MessageType::EVENT_NOTIFICATION, version 1.0).
 * @ingroup device_status
 *
 * This message is followed by a string describing the event or additional
 * binary content, depending on the type of event. The length of the description
 * is @ref event_description_len_bytes. Strings are _not_ null-terminated.
 *
 * ```
 * {MessageHeader, EventNotificationMessage, "Description"}
 * ```
 */
struct P1_ALIGNAS(4) EventNotificationMessage : public MessagePayload {
  enum class EventType : uint8_t {
    /**
     * Event containing a logged message string from the device.
     */
    LOG = 0,
    /**
     * Event indicating a device reset occurred. The event flags will be set to
     * the requested reset bitmask, if applicable (see @ref ResetRequest). The
     * payload will contain a string describing the cause of the reset.
     */
    RESET = 1,
    /**
     * Notification that the user configuration has been changed. Intended for
     * diagnostic purposes.
     */
    CONFIG_CHANGE = 2,
    /**
     * Notification that the user performed a command (e.g., configuration
     * request, fault injection enable/disable).
     */
    COMMAND = 3,
    /**
     * Record containing the response to a user command. Response events are not
     * output on the interface on which the command was received; that interface
     * will receive the response itself.
     */
    COMMAND_RESPONSE = 4,
  };

  static P1_CONSTEXPR_FUNC const char* to_string(EventType type) {
    switch (type) {
      case EventType::LOG:
        return "Log";

      case EventType::RESET:
        return "Reset";

      case EventType::CONFIG_CHANGE:
        return "Config Change";

      case EventType::COMMAND:
        return "Command";

      case EventType::COMMAND_RESPONSE:
        return "Command Response";

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

  /** The number of bytes in the event description string. */
  uint16_t event_description_len_bytes = 0;

  uint8_t reserved2[2] = {0};
};

/**
 * @brief System status information (@ref
 *        MessageType::SYSTEM_STATUS, version 1.0).
 * @ingroup device_status
 *
 * @note
 * All data is timestamped using the Point One Time, which is a monotonic
 * timestamp referenced to the start of the device. Corresponding messages (@ref
 * SystemStatusMessage) may be associated using their @ref p1_time values.
 */

struct P1_ALIGNAS(4) SystemStatusMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::SYSTEM_STATUS;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  static constexpr int16_t INVALID_TEMPERATURE = INT16_MAX;

  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /**
   * The temperature of the GNSS receiver (in deg Celcius * 2^-7). Set to
   * 0x7FFF if invalid.
   */
  int16_t gnss_temperature = INVALID_TEMPERATURE;

  uint8_t reserved[118] = {0};
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
