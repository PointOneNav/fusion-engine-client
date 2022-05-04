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
#  pragma warning(push)
#  pragma warning(disable : 4200)
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
   * The vehicle model.
   *
   * Payload format: @ref VehicleModelConfig
   */
  VEHICLE_MODEL = 20,

  /**
   * The outer dimensions of the vehicle.
   *
   * Payload format: @ref VehicleDimensions
   */
  VEHICLE_DIMENSIONS = 21,

  /**
   * Information pertaining to wheel measurements.
   *
   * Payload format: @ref WheelConfig
   */
  WHEEL_CONFIG = 22,

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

    case ConfigType::VEHICLE_MODEL:
      return "Vehicle Model";

    case ConfigType::VEHICLE_DIMENSIONS:
      return "Vehicle Dimensions";

    case ConfigType::WHEEL_CONFIG:
      return "Wheel Config";

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
      return "Unrecognized";
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

  /** Flag to immediately save the config after applying this setting. */
  static constexpr uint8_t FLAG_APPLY_AND_SAVE = 0x01;

  /** Bitmask of additional flags to modify the command. */
  uint8_t flags = 0;

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
 * The device will respond with a @ref ConfigResponseMessage containing the
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
 *        MessageType::CONFIG_RESPONSE, version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * This message is followed by `N` bytes, where `N` is equal to @ref
 * config_length_bytes that make up the data associated with @ref config_type.
 * For example if the @ref config_type is @ref ConfigType::UART0_BAUD, the
 * payload will include a single 32-bit unsigned integer:
 *
 * ```
 * {MessageHeader, ConfigResponseMessage, uint32_t}
 * ```
 *
 * In response to a @ref GetConfigMessage with an invalid or unsupported @ref
 * ConfigType, @ref config_type in the resulting @ref ConfigResponseMessage will
 * be set to @ref ConfigType::INVALID, and @ref response will indicate the
 * reason. Note that all @ref GetConfigMessage requests, including invalid and
 * rejected requests, will receive a @ref ConfigResponseMessage, not a
 * @ref CommandResponseMessage.
 */
struct alignas(4) ConfigResponseMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::CONFIG_RESPONSE;
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

  /** The response status (success, error, etc.). */
  Response response = Response::OK;

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

/**
 * @brief The vehicle model.
 */
struct alignas(4) VehicleModelConfig {
  enum class VehicleModel : uint16_t {
    UNKNOWN_VEHICLE = 0,

    LEXUS_CT200H = 100,

    KIA_SORENTO = 200,
    KIA_SPORTAGE = 201,

    AUDI_Q7 = 300,
    AUDI_A8L = 301,

    TESLA_MODEL_X = 400,
    TESLA_MODEL_3 = 401,

    HYUNDAI_ELANTRA = 501
  };

  VehicleModel vehicle_model = VehicleModel::UNKNOWN_VEHICLE;
  uint8_t reserved[10] = {0};
};

/**
 * @brief Outer dimensions of the vehicle in meters.
 *
 */
struct alignas(4) VehicleDimensions {
  /** The distance between the front axle and rear axle in meters. */
  float wheelbase_m = NAN;

  /** The distance between the two rear wheels in meters. */
  float rear_track_width_m = NAN;
};

/**
 * @brief Information pertaining to wheel speeds.
 *
 */
struct alignas(4) WheelConfig {
  /** Determines how speeds are measured. */
  enum class WheelSensorType : uint8_t {
    NONE = 0,           ///< Speeds not to be used.
    TICK_RATE = 1,      ///< Use differential wheel speeds.
    TICKS = 2,          ///< Use physical wheel ticks.
    WHEEL_SPEED = 3,    ///< Use differential wheel speeds.
    VEHICLE_SPEED = 4,  ///< Use one uniform speed for the body of the vehicle.
  };

  /** Determines how speeds are applied to system. */
  enum class AppliedSpeedType : uint8_t {
    APPLIED_NONE = 0,           ///< Speeds not to be applied to system.
    REAR_WHEELS = 1,            ///< Use rear wheel speeds only (recommended).
    FRONT_WHEELS = 2,           ///< Use front wheel speeds only.
    FRONT_AND_REAR_WHEELS = 3,  ///< Use front and rear wheel speeds.
    VEHICLE_BODY = 4,           ///< Use one uniform speed for the vehicle.
  };

  /** Determines which wheels of the vehicle are steered. */
  enum class SteeringType : uint8_t {
    UNKNOWN_STEERING = 0,
    FRONT_STEERING = 1,
    FRONT_AND_REAR_STEERING = 2,
  };

  WheelSensorType wheel_sensor_type = WheelSensorType::NONE;
  AppliedSpeedType applied_speed_type = AppliedSpeedType::REAR_WHEELS;
  SteeringType steering_type = SteeringType::UNKNOWN_STEERING;
  uint8_t reserved1[1] = {0};

  /** Measures how often wheel tick measurements are updated. */
  float wheel_update_interval_sec = NAN;

  /** Ratio between steering wheel angle and road wheel angle. */
  float steering_ratio = NAN;

  /** Wheel tick distance in meters. */
  float wheel_ticks_to_m = NAN;

  /** The maximum value that wheel ticks will increment to before restarting to
   *  zero.
   */
  uint32_t wheel_tick_max_value = 0;

  /**
   * Determines whether wheel ticks are signed based on the direction the
   * wheels are turning.
   */
  bool wheel_ticks_signed = false;

  /**
   * Determines if wheel tick value solely increases, regardless of the
   * direction the wheels are turning. To be used in conjunction with @ref
   * wheel_ticks_signed.
   */
  bool wheel_ticks_always_increase = true;

  uint8_t reserved2[2] = {0};
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
 * @brief Get a human-friendly string name for the specified @ref
 *        ProtocolType.
 * @ingroup config_and_ctrl_messages
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(ProtocolType val) {
  switch (val) {
    case ProtocolType::INVALID:
      return "Invalid";
    case ProtocolType::FUSION_ENGINE:
      return "FusionEngine";
    case ProtocolType::NMEA:
      return "NMEA";
    case ProtocolType::RTCM:
      return "RTCM";
    default:
      return "Unrecognized";
  }
}

/**
 * @brief @ref ProtocolType stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream, ProtocolType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

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
  /**
   * @brief Reserved value for @ref update_period_ms to indicate that the
   *        message should come out at its max rate.
   *
   * Also used for messages that output at a fixed rate.
   */
  static constexpr uint16_t MAX_RATE = 0xFFFF;

  /** @brief The type of message to configure. */
  MsgType type;
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
  /** This is used for requesting the configuration for all interfaces. */
  ALL = 255,
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        TransportType.
 * @ingroup config_and_ctrl_messages
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(TransportType val) {
  switch (val) {
    case TransportType::INVALID:
      return "Invalid";
    case TransportType::SERIAL:
      return "Serial";
    case TransportType::FILE:
      return "File";
    case TransportType::TCP_CLIENT:
      return "TCP Client";
    case TransportType::TCP_SERVER:
      return "TCP Server";
    case TransportType::UDP_CLIENT:
      return "UDP Client";
    case TransportType::UDP_SERVER:
      return "UDP Server";
    case TransportType::ALL:
      return "All";
    default:
      return "Unrecognized";
  }
}

/**
 * @brief @ref TransportType stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream, TransportType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief Identifies an IO interface.
 *
 * (e.g., serial port 0 or TCP server 2)
 */
struct alignas(4) InterfaceID {
  /** The interface's transport type. **/
  TransportType type = TransportType::INVALID;
  /** An identifier for the instance of this transport. */
  uint8_t index = 0;
  uint8_t reserved[2] = {0};

  bool operator==(const InterfaceID& other) const {
    return type == other.type && index == other.index;
  }

  bool inline operator!=(const InterfaceID& other) const {
    return !(*this == other);
  }
};

/**
 * @brief @ref InterfaceID stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream, InterfaceID val) {
  stream << "[type=" << to_string(val.type) << ", index=" << (int)val.index
         << "]";
  return stream;
}

/**
 * @brief The ways that this configuration message can be applied to the
 *        previous list of values for that configuration type.
 */
enum class UpdateAction : uint8_t {
  /**
   * Replace the previous list of values with the set provided in
   * this configuration.
   */
  REPLACE = 0
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        UpdateAction.
 * @ingroup config_and_ctrl_messages
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(UpdateAction val) {
  switch (val) {
    case UpdateAction::REPLACE:
      return "Replace";
    default:
      return "Unrecognized";
  }
}

/**
 * @brief @ref UpdateAction stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream, UpdateAction val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief Configure which stream(s) will be sent to an output interface.
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
  /** The stream this message configures. */
  uint8_t stream_index = 0;
  /**
   * The type of action this configuration message applies to the
   * previous state of the output stream.
   */
  UpdateAction update_action = UpdateAction::REPLACE;
  /** The number of `msg_rates` entries this message contains. */
  uint16_t num_msgs = 0;
  /** Placeholder pointer for variable length set of messages. */
  MsgRate msg_rates[0];
};

/**
 * @brief Configuration for the streams associated with a single output
 *        interface.
 *
 * This object is used in the payload of the @ref
 * SetOutputInterfaceConfigMessage and @ref
 * OutputInterfaceConfigResponseMessage messages. The declared contents are
 * followed by `N` `uint8_t` stream indices, where `N` is equal to @ref
 * num_streams. For example:
 *
 * ```
 * {MessageHeader, SetOutputInterfaceConfigMessage,
 *  OutputInterfaceConfigEntry, uint8_t, uint8_t,  ...}
 * ```
 */
struct alignas(4) OutputInterfaceConfigEntry {
  /** The output interface to configure. */
  InterfaceID output_interface;
  /** The number of `stream_indices` entries this message contains. */
  uint8_t num_streams = 0;
  uint8_t reserved[3] = {0};
  /**
   * Placeholder pointer for variable length set of indices.
   *
   * In the future these streams will be user defined, but for now they are:
   * - `0`: All FusionEngine messages.
   * - `1`: All NMEA messages.
   * - `2`: All RTCM messages.
   */
  uint8_t stream_indices[0];
};

/**
 * @brief Configure the set of output streams enabled for a given output
 *        interface (@ref MessageType::SET_OUTPUT_INTERFACE_CONFIG, version
 *        1.0).
 * @ingroup config_and_ctrl_messages

 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request was accepted. Not all interfaces defined in @ref
 * InterfaceID are supported on all devices.
 *
 * Parameter changes are applied to the device's active configuration
 * immediately, but are not saved to persistent storage and will be restored to
 * their previous values on reset. To save configuration settings to persistent
 * storage, see @ref SaveConfigMessage.
 */
struct alignas(4) SetOutputInterfaceConfigMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::SET_OUTPUT_INTERFACE_CONFIG;
  static constexpr uint8_t MESSAGE_VERSION = 0;
  /**
   * The type of action this configuration message applies to the
   * previous list of streams.
   */
  UpdateAction update_action = UpdateAction::REPLACE;
  uint8_t reserved[3] = {0};

  /**
   * The new output interface configuration to be applied.
   */
  OutputInterfaceConfigEntry output_interface_data;
};

/**
 * @brief Query the set of message streams configured to be output by the device
 *        on a specified interface. (@ref
 *        MessageType::GET_OUTPUT_INTERFACE_CONFIG, version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * The device will respond with a @ref OutputInterfaceConfigResponseMessage
 * containing the values.
 */
struct alignas(4) GetOutputInterfaceConfigMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::GET_OUTPUT_INTERFACE_CONFIG;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The config source to request data from (active, saved, etc.). */
  ConfigurationSource request_source = ConfigurationSource::ACTIVE;

  uint8_t reserved[3] = {0};

  /**
   * The output interface to get the config for. If the `type` is @ref
   * TransportType::ALL then request the configuration for all interfaces.
   */
  InterfaceID output_interface;
};

/**
 * @brief Response to a @ref GetOutputInterfaceConfigMessage request (@ref
 *        MessageType::OUTPUT_INTERFACE_CONFIG_RESPONSE, version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * This message is followed by `N` @ref OutputInterfaceConfigEntry objects,
 * where `N` is equal to @ref number_of_interfaces. Each of these interfaces is
 * variable size, and the sum of the objects should add up to the message size
 * from the header.
 *
 * For example if the @ref number_of_interfaces is 2 and both interfaces have
 * two streams the payload will look as follows:
 *
 * ```
 * {MessageHeader, OutputInterfaceConfigResponseMessage,
 *  OutputInterfaceConfigEntry, uint8_t, uint8_t,
 *  OutputInterfaceConfigEntry, uint8_t, uint8_t}
 * ```
 */
struct alignas(4) OutputInterfaceConfigResponseMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::OUTPUT_INTERFACE_CONFIG_RESPONSE;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The source of the parameter value (active, saved, etc.). */
  ConfigurationSource config_source = ConfigurationSource::ACTIVE;

  /** The response status (success, error, etc.). */
  Response response = Response::OK;

  /**
   * Set to `true` if the active configuration differs from the saved
   * configuration for this parameter.
   */
  bool active_differs_from_saved = false;

  /** The number of output interfaces to follow. */
  uint8_t number_of_interfaces = 0;

  /**
   * A pointer to the beginning of the interface data.
   */
  // Note: This causes a compiler error on MSVC so it is not included:
  //       https://docs.microsoft.com/en-us/cpp/error-messages/compiler-errors-1/compiler-error-c2233
  // OutputInterfaceConfigEntry output_interface_data[0];
};

/** @} */

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one

#ifdef _MSC_VER
#  pragma warning(pop)
#endif
