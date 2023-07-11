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
#  pragma warning(push)
#  pragma warning(disable : 4200)
#endif

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
struct P1_ALIGNAS(4) CommandResponseMessage : public MessagePayload {
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
 * @ref Response::UNSUPPORTED_FEATURE message.
 *
 * @note
 * The generated response may not immediately follow the request if other
 * outbound messages are already enqueued to be sent.
 *
 * # Expected Response
 * The requested message type, or @ref CommandResponseMessage on error.
 */
struct P1_ALIGNAS(4) MessageRequest : public MessagePayload {
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
 *
 * # Expected Response
 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request succeeded.
 */
struct P1_ALIGNAS(4) ResetRequest : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::RESET_REQUEST;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * @name Runtime State Reset
   * @{
   */
  /** Restart the navigation engine, but do not clear its position estimate. */
  static constexpr uint32_t RESTART_NAVIGATION_ENGINE = 0x00000001;
  /** Delete all GNSS corrections information. */
  static constexpr uint32_t RESET_GNSS_CORRECTIONS = 0x00000002;
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
  /**
   * Reset bias estimates, and other IMU corrections that are typically
   * estimated quickly.
   */
  static constexpr uint32_t RESET_FAST_IMU_CORRECTIONS = 0x00000400;
  /** @} */

  /**
   * @name Clear Long Lived Data
   * @{
   */
  /**
   * Reset all stored navigation engine data, including position, velocity, and
   * orientation state (same as @ref RESET_POSITION_DATA), plus all IMU
   * corrections and other training data.
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
   * @name Software Reboot And Special Reset Modes
   * @{
   */
  /**
   * Reboot the GNSS measurement engine (GNSS receiver), in addition to
   * performing any other requested resets (e.g., @ref RESET_EPHEMERIS). If no
   * other resets are specified, the GNSS receiver will reboot and should
   * perform a hot start.
   */
  static constexpr uint32_t REBOOT_GNSS_MEASUREMENT_ENGINE = 0x01000000;
  /** Reboot the navigation processor. */
  static constexpr uint32_t REBOOT_NAVIGATION_PROCESSOR = 0x02000000;
  /**
   * Perform a diagnostic log reset to guarantee deterministic performance for
   * data post-processing and diagnostic support.
   *
   * Diagnostic log resets are useful when capturing data to be sent to Point
   * One for analysis and support. Performing a diagnostic reset guarantees that
   * the performance of the device seen in real time can be reproduced during
   * post-processing.
   *
   * This reset performs the following:
   * - Restart the navigation engine (@ref RESTART_NAVIGATION_ENGINE)
   * - Clear any stored data in RAM that was received since startup such as
   *   ephemeris or GNSS corrections
   *   - This is _not_ the same as @ref RESET_EPHEMERIS; this action does not
   *     reset ephemeris data stored in persistent storage
   * - Flush internal data buffers on the device
   *
   * Note that this does _not_ reset the navigation engine's position data,
   * training parameters, or calibration. If the navigation engine has existing
   * position information, it will be used.
   *
   * This reset may be combined with other resets as needed to clear additional
   * information.
   */
  static constexpr uint32_t DIAGNOSTIC_LOG_RESET = 0x04000000;
  /** @} */

  /**
   * @name Device Reset Bitmasks
   * @{
   */
  /**
   * Perform a device hot start.
   *
   * This will reset the navigation engine into a known state, using previously
   * stored position and time information. The device will begin navigating
   * immediately if possible.
   *
   * To be reset:
   * - The navigation engine (@ref RESTART_NAVIGATION_ENGINE)
   *
   * Not reset/performed:
   * - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
   * - Position, velocity, orientation (@ref RESET_POSITION_DATA)
   * - GNSS ephemeris data (@ref RESET_EPHEMERIS)
   * - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
   * - Training parameters (slowly estimated IMU corrections, temperature
   *   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
   * - Calibration data (@ref RESET_CALIBRATION_DATA)
   * - User configuration settings (@ref RESET_CONFIG)
   * - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
   * - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
   */
  static constexpr uint32_t HOT_START = 0x00000001;

  /**
   * Perform a device warm start.
   *
   * During a warm start, the device retains its knowledge of approximate
   * position and time, plus almanac data if available, but resets all ephemeris
   * data. As a result, the device will need to download ephemeris data before
   * continuing to navigate with GNSS.
   *
   * To be reset:
   * - The navigation engine (i.e., perform a hot start, @ref
   *   RESTART_NAVIGATION_ENGINE)
   * - GNSS ephemeris data (@ref RESET_EPHEMERIS)
   *
   * Not reset/performed:
   * - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
   * - Position, velocity, orientation (@ref RESET_POSITION_DATA)
   * - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
   * - Training parameters (slowly estimated IMU corrections, temperature
   *   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
   * - Calibration data (@ref RESET_CALIBRATION_DATA)
   * - User configuration settings (@ref RESET_CONFIG)
   * - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
   * - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
   */
  static constexpr uint32_t WARM_START = 0x00000201;

  /**
   * Perform a PVT reset: reset all position, velocity, orientation, and time
   * information (i.e., the navigation engine's kinematic state).
   *
   * A PVT reset is typically used to reset the kinematic portion of the
   * navigation engine's state if you are experiencing errors on startup or
   * after a @ref HOT_START.
   *
   * To be reset:
   * - The navigation engine (@ref RESTART_NAVIGATION_ENGINE)
   * - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
   * - Position, velocity, orientation (@ref RESET_POSITION_DATA)
   *
   * Not reset/performed:
   * - GNSS ephemeris data (@ref RESET_EPHEMERIS)
   * - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
   * - Training parameters (slowly estimated IMU corrections, temperature
   *   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
   * - Calibration data (@ref RESET_CALIBRATION_DATA)
   * - User configuration settings (@ref RESET_CONFIG)
   * - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
   * - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
   */
  static constexpr uint32_t PVT_RESET = 0x000001FF;

  /**
   * Perform a device cold start.
   *
   * A cold start is typically used to reset the device's state estimate in the
   * case of error that cannot be resolved by a @ref WARM_START.
   *
   * To be reset:
   * - The navigation engine (@ref RESTART_NAVIGATION_ENGINE)
   * - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
   * - Position, velocity, orientation (@ref RESET_POSITION_DATA)
   * - GNSS ephemeris data (@ref RESET_EPHEMERIS)
   * - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
   *
   * Not reset/performed:
   * - Training parameters (slowly estimated IMU corrections, temperature
   *   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
   * - Calibration data (@ref RESET_CALIBRATION_DATA)
   * - User configuration settings (@ref RESET_CONFIG)
   * - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
   * - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
   *
   * @note
   * To reset training or calibration data as well, set the @ref
   * RESET_NAVIGATION_ENGINE_DATA and @ref RESET_CALIBRATION_DATA bits.
   */
  static constexpr uint32_t COLD_START = 0x00000FFF;

  /**
   * Restart mask to set all persistent data, including calibration and user
   * configuration, back to factory defaults.
   */
  static constexpr uint32_t FACTORY_RESET = 0xFFFFFFFF;
  /** @} */

  /** Bit mask of functionality to reset. */
  uint32_t reset_mask = 0;
};

/**
 * @brief Software version information, (@ref
 *        MessageType::VERSION_INFO, version 1.0).
 * @ingroup config_and_ctrl_messages
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
 * _not_ null terminated.
 *
 * ```
 * {MessageHeader, VersionInfoMessage, "Firmware Version", "Engine Version",
 *  "OS Version", "Receiver Version"}
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
  //char fw_version_str[0];
};

/**
 * @brief Identifies a FusionEngine device.
 * @ingroup config_and_ctrl_messages
 */
enum class DeviceType : uint8_t {
  /** Unable to map device to a defined entry. */
  UNKNOWN = 0,
  /** Device is a Point One Atlas. */
  ATLAS = 1,
  /** Device is a Quectel LG69T-AM system. */
  LG69T_AM = 2,
  /** Device is a Quectel LG69T-AP system. */
  LG69T_AP = 3,
  /** Device is a Quectel LG69T-AH system. */
  LG69T_AH = 4,
};

/**
 * @brief Get a human-friendly string name for the specified @ref DeviceType.
 * @ingroup config_and_ctrl_messages
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
 * @ingroup config_and_ctrl_messages
 *
 * This message contains ID data for each of the following, where available:
 * - HW - A unique ROM identifier pulled from the device HW (for example, a CPU
 *   serial number)
 * - User - A value set by the user to identify a device
 * - Receiver - A unique ROM identifier pulled from the GNSS receiver
 *
 * The message payload specifies the length of each string (in bytes). It is
 * followed by each of the listed IDs consecutively. The values are _not_ null
 * terminated and the way each field is populated (strings or binary) depends on
 * the type of device, indicated by @ref device_type.
 *
 * ```
 * {MessageHeader, VersionInfoMessage, "HW ID", "User ID", "Receiver ID"}
 * ```
 */
struct P1_ALIGNAS(4) DeviceIDMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::DEVICE_ID;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The current system timestamp (in ns).*/
  int64_t system_time_ns = 0;

  /** The type of device this message originated from.*/
  DeviceType device_type = DeviceType::UNKNOWN;

  /** The length of the HW ID (in bytes). */
  uint8_t hw_id_length = 0;

  /** The length of the user specified ID (in bytes). */
  uint8_t user_id_length = 0;

  /** The length of the GNSS receiver ID (in bytes). */
  uint8_t receiver_id_length = 0;

  uint8_t reserved[4] = {0};

  /**
   * The beginning of the hw ID data.
   *
   * All other ID strings follow immediately after this one in the data buffer.
   * For example, the user ID can be obtained as follows:
   * ```cpp
   * std::vector<uint8_t> user_id_data(
   *     hw_id_data + message.hw_id_length,
   *     hw_id_data + message.hw_id_length + message.user_id_length);
   * ```
   */
  //uint8_t hw_id_data[0];
};

/**
 * @brief Notification of a system event for logging purposes (@ref
 *        MessageType::EVENT_NOTIFICATION, version 1.0).
 * @ingroup config_and_ctrl_messages
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

  /**
   * This is a dummy entry to provide a pointer to this offset.
   *
   * This is used for populating string describing the event, or other binary
   * content where applicable.
   */
  //char* event_description[0];
};

/**
 * @brief Perform a device shutdown (@ref
 *        MessageType::SHUTDOWN_REQUEST, version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * # Expected Response
 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request succeeded.
 */
struct P1_ALIGNAS(4) ShutdownRequest : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::SHUTDOWN_REQUEST;
  static constexpr uint8_t MESSAGE_VERSION = 0;
  /** A bitmask of flags associated with the event. */
  uint64_t shutdown_flags = 0;
  uint8_t reserved1[8] = {0};
};

/**
 * @brief Start up a device (@ref
 *        MessageType::STARTUP_REQUEST, version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * # Expected Response
 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request succeeded.
 */
struct P1_ALIGNAS(4) StartupRequest : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::STARTUP_REQUEST;
  static constexpr uint8_t MESSAGE_VERSION = 0;
  /** A bitmask of flags associated with the event. */
  uint64_t startup_flags = 0;
  uint8_t reserved1[8] = {0};
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one

#ifdef _MSC_VER
#  pragma warning(pop)
#endif
