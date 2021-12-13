/**************************************************************************/ /**
 * @brief Device configuration settings control messages.
 * @file
 ******************************************************************************/

#pragma once

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
   * Configure the set of protocols and messages enabled for a given output
   * stream.
   *
   * Payload format: @ref OutputStreamMsgsConfig
   */
  OUTPUT_STREAM_MSGS = 1,

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
constexpr const char* to_string(ConfigType type) {
  switch (type) {
    case ConfigType::INVALID:
      return "Invalid";

    case ConfigType::OUTPUT_STREAM_MSGS:
      return "Output Stream Messages";

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
 * @param type The desired configuration source.
 *
 * @return The corresponding string name.
 */
constexpr const char* to_string(ConfigurationSource type) {
  switch (type) {
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
                                ConfigurationSource type) {
  stream << to_string(type) << " (" << (int)type << ")";
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
 * @param type The desired save operation.
 *
 * @return The corresponding string name.
 */
static constexpr const char* to_string(SaveAction action) {
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
inline std::ostream& operator<<(std::ostream& stream, SaveAction type) {
  stream << to_string(type) << " (" << (int)type << ")";
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

  /** The version of the configuration contents. */
  uint8_t config_version = 0;

  uint8_t reserved[1] = {0};

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
 * In response to a @ref GetConfigMessage with an invalid @ref ConfigType or an
 * unsupported version, @ref config_type will be set to @ref
 * ConfigType::INVALID.
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

  /**
   * The version of the configuration parameter payload reported by this
   * message.
   */
  uint8_t config_version = 0;

  uint8_t reserved[3] = {0};

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

/** @} */

/**************************************************************************/ /**
 * @name Input/Output Stream Control
 * @{
 ******************************************************************************/

/**
 * @brief The framing protocol of a message.
 */
enum class ProtocolType : uint8_t {
  INVALID = 0,
  FUSION_ENGINE = 1,
  NMEA = 2,
  RTCM = 3,
};

/**
 * @brief Identifies a message type.
 */
struct alignas(4) MsgType {
  ProtocolType protocol = ProtocolType::INVALID;
  uint8_t reserved[1] = {0};
  uint16_t msg_id = 0;
};

/**
 * @brief An output rate for a message.
 */
struct alignas(4) MsgRate {
  /** @brief The type of message to configure. */
  MsgType type;
  /**
   * @brief Reserved value for @ref update_period_ms to indicate that the
   *        message should come out at its max rate.
   *
   * Also used for messages that output at a fixed rate.
   */
  static constexpr uint16_t MAX_RATE = 0xFFFF;
  /** @brief The desired message update interval (in ms). */
  uint16_t update_period_ms = 0;
  uint8_t reserved[2] = {0};
};

/**
 * @brief Type of IO interface transport.
 */
enum class TransportType : uint8_t {
  INVALID = 0,
  SERIAL = 1,
  FILE = 2,
  TCP_CLIENT = 3,
  TCP_SERVER = 4,
  UDP_CLIENT = 5,
  UDP_SERVER = 6,
};

/**
 * @brief Identifies an IO interface.
 */
struct alignas(4) InterfaceID {
  TransportType type = TransportType::INVALID;
  /**
   * @brief An identifier for the instance of this transport.
   *
   * For example serial port 1 or serial port 2.
   */
  uint8_t index = 0;
  uint8_t reserved[2] = {0};
};

/**
 * @brief Configuration for an output Stream.
 *
 * Sets the messages associated with an output stream and which output interface
 * it they should be sent out.
 *
 * This message is followed by `N` @ref MsgRate objects, where `N`
 * is equal to @ref num_msgs. For example:
 *
 * ```
 * {MessageHeader, SetConfigMessage, OutputStreamMsgsConfig,
 *  MsgRate, MsgRate,  ...}
 * ```
 */
struct alignas(4) OutputStreamMsgsConfig {
  /**
   * @brief The ways that this configuration message can be applied to the
   *        previous state of the output stream.
   */
  enum class Action : uint8_t {
    /**
     * @brief Replace the previous messages in this stream with the set provided
     *        in this configuration.
     */
    REPLACE = 0
  };
  /** @brief The stream this message configures. */
  uint8_t stream_index = 0;
  /**
   * @brief The type of action this configuration message applies to the
   *        previous state of the output stream.
   */
  Action update_action = Action::REPLACE;
  uint8_t reserved1[2] = {0};
  /** The output interface to send this stream's messages to. */
  InterfaceID stream_output_interface;
  /** The number of `msg_rates` entries this message contains. */
  uint16_t num_msgs = 0;
  uint8_t reserved2[2] = {0};
  /** Placeholder pointer for variable length set of messages. */
  MsgRate msg_rates[0];
};

// TODO: Add `OutputStreamInterfacesConfig` to configure the list of
// `InterfaceID` associated with a stream.

/** @} */

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
