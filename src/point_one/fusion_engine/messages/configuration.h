/**************************************************************************/ /**
 * @brief Device configuration settings control messages.
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

#include <ostream>

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
 * @brief An identifier for the contents of a parameter configuration message.
 * @ingroup config_and_ctrl_messages
 *
 * See also @ref SetConfigMessage.
 */
enum class ConfigType : uint16_t {
  INVALID = 0,

  /**
   * The location of the device IMU with respect to the vehicle body frame (in
   * meters).
   *
   * Payload format: @ref Point3f
   */
  DEVICE_LEVER_ARM = 16,

  /**
   * The orientation of the device IMU with respect to the vehicle body axes.
   *
   * Payload format: @ref CoarseOrientation
   */
  DEVICE_COARSE_ORIENTATION = 17,

  /**
   * The location of the GNSS antenna with respect to the vehicle body frame (in
   * meters).
   *
   * Payload format: @ref Point3f
   */
  GNSS_LEVER_ARM = 18,

  /**
   * The location of the desired output location with respect to the vehicle
   * body frame (in meters).
   *
   * Payload format: @ref Point3f
   */
  OUTPUT_LEVER_ARM = 19,

  /**
   * Configure the UART0 serial baud rate (in bits/second).
   *
   * Payload format: `uint32_t`
   */
  UART0_BAUD = 256,

  /**
   * Configure the UART1 serial baud rate (in bits/second).
   *
   * Payload format: `uint32_t`
   */
  UART1_BAUD = 257,
};

/**
 * @brief Get a human-friendly string name for the specified @ref ConfigType.
 * @ingroup config_and_ctrl_messages
 *
 * @param type The desired configuration parameter type.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(ConfigType type) {
  switch (type) {
    case ConfigType::INVALID:
      return "Invalid";

    case ConfigType::DEVICE_LEVER_ARM:
      return "Device Lever Arm";

    case ConfigType::DEVICE_COARSE_ORIENTATION:
      return "Device Coarse Orientation";

    case ConfigType::GNSS_LEVER_ARM:
      return "GNSS Lever Arm";

    case ConfigType::OUTPUT_LEVER_ARM:
      return "Output Lever Arm";

    case ConfigType::UART0_BAUD:
      return "UART0 Baud Rate";

    case ConfigType::UART1_BAUD:
      return "UART1 Baud Rate";

    default:
      return "Unrecognized Configuration";
  }
}

/**
 * @brief @ref ConfigType stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream, ConfigType type) {
  stream << to_string(type) << " (" << (int)type << ")";
  return stream;
}

/**
 * @brief The type of a device's configuration settings.
 * @ingroup config_and_ctrl_messages
 */
enum class ConfigurationSource : uint8_t {
  ACTIVE = 0, ///< Active configuration currently in use by the device.
  SAVED = 1, ///< Settings currently saved to persistent storage.
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        ConfigurationSource.
 * @ingroup config_and_ctrl_messages
 *
 * @param source The desired configuration source.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(ConfigurationSource source) {
  switch (source) {
    case ConfigurationSource::ACTIVE:
      return "Active";

    case ConfigurationSource::SAVED:
      return "Saved";

    default:
      return "Unrecognized Source";
  }
}

/**
 * @brief @ref ConfigurationSource stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream,
                                ConfigurationSource source) {
  stream << to_string(source) << " (" << (int)source << ")";
  return stream;
}

/**
 * @brief The type configuration save operation to be performed.
 * @ingroup config_and_ctrl_messages
 */
enum class SaveAction : uint8_t {
  /** Save all active parameters to persistent storage. */
  SAVE = 0,
  /** Revert the active configuration to previously saved values. */
  REVERT_TO_SAVED = 1,
  /** Reset the active _and_ saved configuration to default values. */
  REVERT_TO_DEFAULT = 2,
};

/**
 * @brief Get a human-friendly string name for the specified @ref SaveAction.
 * @ingroup config_and_ctrl_messages
 *
 * @param action The desired save operation.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(SaveAction action) {
  switch (action) {
    case SaveAction::SAVE:
      return "Save";

    case SaveAction::REVERT_TO_SAVED:
      return "Revert To Saved";

    case SaveAction::REVERT_TO_DEFAULT:
      return "Revert To Default";

    default:
      return "Unknown";
  }
}

/**
 * @brief @ref SaveAction stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream, SaveAction action) {
  stream << to_string(action) << " (" << (int)action << ")";
  return stream;
}

/**
 * @brief Set a user configuration parameter (@ref MessageType::SET_CONFIG,
 *        version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * The format of the parameter value, @ref config_change_data, is defined by the
 * the specified @ref config_type (@ref ConfigType). For example, an antenna
 * lever arm definition may require three 32-bit `float` values, one for each
 * axis, while a serial port baud rate may be specified as single 32-bit
 * unsigned integer (`uint32_t`).
 *
 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request was accepted. Not all parameters defined in @ref
 * ConfigType are supported on all devices.
 *
 * Parameter changes are applied to the device's active configuration
 * immediately, but are not saved to persistent storage and will be restored to
 * their previous values on reset. To save configuration settings to persistent
 * storage, see @ref SaveConfigMessage.
 */
struct alignas(4) SetConfigMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::SET_CONFIG;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The type of parameter to be configured. */
  ConfigType config_type;

  uint8_t reserved[2] = {0};

  /** The size of the parameter value, @ref config_change_data (in bytes). */
  uint32_t config_length_bytes = 0;

  /**
   * A pointer to the beginning of the configuration parameter value.
   *
   * The size and format of the contents is specified by the @ref config_type.
   * See @ref ConfigType.
   */
  uint8_t config_change_data[0];
};

/**
 * @brief Query the value of a user configuration parameter (@ref
 *        MessageType::GET_CONFIG, version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * The device will respond with a @ref ConfigDataMessage containing the
 * requested parameter value, or a @ref CommandResponseMessage on failure.
 */
struct alignas(4) GetConfigMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::GET_CONFIG;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The desired parameter. */
  ConfigType config_type = ConfigType::INVALID;

  /** The config source to request data from (active, saved, etc.). */
  ConfigurationSource request_source = ConfigurationSource::ACTIVE;

  uint8_t reserved[1] = {0};
};

/**
 * @brief Save or reload configuration settings (@ref MessageType::SAVE_CONFIG,
 *        version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request was accepted.
 */
struct alignas(4) SaveConfigMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::SAVE_CONFIG;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The action to performed. */
  SaveAction action = SaveAction::SAVE;

  uint8_t reserved[3] = {0};
};

/**
 * @brief Response to a @ref GetConfigMessage request (@ref
 *        MessageType::CONFIG_DATA, version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * This message is followed by `N` bytes, where `N` is equal to @ref
 * config_length_bytes that make up the data associated with @ref config_type.
 * For example if the @ref config_type is @ref ConfigType::UART0_BAUD, the
 * payload will include a single 32-bit unsigned integer:
 *
 * ```
 * {MessageHeader, ConfigDataMessage, uint32_t}
 * ```
 *
 * In response to a @ref GetConfigMessage with an invalid or unsupported @ref
 * ConfigType, @ref config_type in the resulting @ref ConfigDataMessage will be
 * set to @ref ConfigType::INVALID. Note that invalid and rejected requests will
 * receive a @ref ConfigDataMessage, not a @ref CommandResponseMessage.
 */
struct alignas(4) ConfigDataMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::CONFIG_DATA;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The source of the parameter value (active, saved, etc.). */
  ConfigurationSource config_source = ConfigurationSource::ACTIVE;

  /**
   * Set to `true` if the active configuration differs from the saved
   * configuration for this parameter.
   */
  bool active_differs_from_saved = false;

  /** The type of configuration parameter contained in this message. */
  ConfigType config_type = ConfigType::INVALID;

  uint8_t reserved[4] = {0};

  /** The size of the parameter value, @ref config_change_data (in bytes). */
  uint32_t config_length_bytes = 0;

  /**
   * A pointer to the beginning of the configuration parameter value.
   *
   * The size and format of the contents is specified by the @ref config_type.
   * See @ref ConfigType.
   */
  uint8_t config_change_data[0];
};

/**************************************************************************/ /**
 * @name Configuration Settings Type Definitions
 * @{
 ******************************************************************************/

/**
 * @brief A 3-dimensional vector (used for lever arms, etc.).
 */
struct alignas(4) Point3f {
  float x = NAN;
  float y = NAN;
  float z = NAN;
};

/**
 * @brief The orientation of a device with respect to the vehicle body axes.
 *
 * A device's orientation is defined by specifying how the +x and +z axes of its
 * IMU are aligned with the vehicle body axes. For example, in a car:
 * - `forward,up`: device +x = vehicle +x, device +z = vehicle +z (i.e.,
 *   IMU pointed towards the front of the vehicle).
 * - `left,up`: device +x = vehicle +y, device +z = vehicle +z (i.e., IMU
 *   pointed towards the left side of the vehicle)
 * - `up,backward`: device +x = vehicle +z, device +z = vehicle -x (i.e.,
 *   IMU pointed vertically upward, with the top of the IMU pointed towards the
 *   trunk)
 */
struct alignas(4) CoarseOrientation {
  enum class Direction : uint8_t {
    FORWARD = 0, ///< Aligned with vehicle +x axis.
    BACKWARD = 1, ///< Aligned with vehicle -x axis.
    LEFT = 2, ///< Aligned with vehicle +y axis.
    RIGHT = 3, ///< Aligned with vehicle -y axis.
    UP = 4, ///< Aligned with vehicle +z axis.
    DOWN = 5, ///< Aligned with vehicle -z axis.
    INVALID = 255
  };

  /** The direction of the device +x axis relative to the vehicle body axes. */
  Direction x_direction = Direction::FORWARD;

  /** The direction of the device +z axis relative to the vehicle body axes. */
  Direction z_direction = Direction::UP;

  uint8_t reserved[2] = {0};
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one

#ifdef _MSC_VER
#pragma warning(pop)
#endif
