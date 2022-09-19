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
   * The offset of the desired output location with respect to the vehicle
   * body frame (in meters).
   *
   * Payload format: @ref Point3f
   */
  OUTPUT_LEVER_ARM = 19,

  /**
   * Information about the vehicle including model and dimensions.
   *
   * Payload format: @ref VehicleDetails
   */
  VEHICLE_DETAILS = 20,

  /**
   * Information pertaining to wheel speed/rotation measurements.
   *
   * Payload format: @ref WheelConfig
   */
  WHEEL_CONFIG = 21,

  /**
   * Indicates the mode and direction used when capturing vehicle wheel tick
   * data from a voltage pulse on an I/O pin.
   *
   * Payload format: @ref HardwareTickConfig
   */
  HARDWARE_TICK_CONFIG = 22,

  /**
   * Configure the UART1 serial baud rate (in bits/second).
   *
   * Payload format: `uint32_t`
   */
  UART1_BAUD = 256,

  /**
   * Configure the UART2 serial baud rate (in bits/second).
   *
   * Payload format: `uint32_t`
   */
  UART2_BAUD = 257,

  /**
   * Force output the diagnostic message set on UART1.
   *
   * Payload format: `bool`
   */
  UART1_OUTPUT_DIAGNOSTICS_MESSAGES = 258,

  /**
   * Force output the diagnostic message set on UART2.
   *
   * Payload format: `bool`
   */
  UART2_OUTPUT_DIAGNOSTICS_MESSAGES = 259,

  /**
   * Enable watchdog timer to restart device after fatal errors.
   *
   * Payload format: `bool`
   */
  ENABLE_WATCHDOG_TIMER = 300,
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

    case ConfigType::VEHICLE_DETAILS:
      return "Vehicle Details";

    case ConfigType::WHEEL_CONFIG:
      return "Wheel Config";

    case ConfigType::HARDWARE_TICK_CONFIG:
      return "Hardware Tick Config";

    case ConfigType::UART1_BAUD:
      return "UART1 Baud Rate";

    case ConfigType::UART2_BAUD:
      return "UART2 Baud Rate";

    case ConfigType::UART1_OUTPUT_DIAGNOSTICS_MESSAGES:
      return "UART1 Diagnostic Messages Enabled";

    case ConfigType::UART2_OUTPUT_DIAGNOSTICS_MESSAGES:
      return "UART2 Diagnostic Messages Enabled";

    case ConfigType::ENABLE_WATCHDOG_TIMER:
      return "Watchdog Timer Enabled";

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

  /** Flag to immediately save the config after applying this setting. */
  static constexpr uint8_t FLAG_APPLY_AND_SAVE = 0x01;

  /** The type of parameter to be configured. */
  ConfigType config_type;

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
 * For example if the @ref config_type is @ref ConfigType::UART1_BAUD, the
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

  /**
   * Flag to indicate the active value for this configuration differs from the
   * value saved to persistent memory.
   */
  static constexpr uint8_t FLAG_ACTIVE_DIFFERS_FROM_SAVED = 0x1;

  /** The source of the parameter value (active, saved, etc.). */
  ConfigurationSource config_source = ConfigurationSource::ACTIVE;

  /** Flags that describe the configuration parameter. */
  uint8_t flags = 0;

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
 * @brief The make and model of the vehicle.
 * @ingroup config_and_ctrl_messages
 */
enum class VehicleModel : uint16_t {
  UNKNOWN_VEHICLE = 0,
  DATASPEED_CD4 = 1,
  // In general, all J1939 vehicles support a subset of the J1939 standard and
  // may be set to vehicle model `J1939`. Their 29-bit CAN IDs may differ
  // based on how the platform assigns message priorities and source
  // addresses, but the underlying program group number (PGN) and message
  // contents will be consistent.
  //
  // For most vehicles, it is not necessary to specify and particular make and
  // model.
  J1939 = 2,

  LEXUS_CT200H = 20,

  KIA_SORENTO = 40,
  KIA_SPORTAGE = 41,

  AUDI_Q7 = 60,
  AUDI_A8L = 61,

  TESLA_MODEL_X = 80,
  TESLA_MODEL_3 = 81,

  HYUNDAI_ELANTRA = 100,

  PEUGEOT_206 = 120,

  MAN_TGX = 140,

  FACTION = 160,

  LINCOLN_MKZ = 180,

  BMW_7 = 200,
};

/**
 * @brief Get a human-friendly string name for the specified @ref VehicleModel.
 * @ingroup config_and_ctrl_messages
 *
 * @param vehicle_model The desired vehicle model.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(VehicleModel vehicle_model) {
  switch (vehicle_model) {
    case VehicleModel::UNKNOWN_VEHICLE:
      return "UNKNOWN";
    case VehicleModel::DATASPEED_CD4:
      return "DATASPEED_CD4";
    case VehicleModel::J1939:
      return "J1939";
    case VehicleModel::LEXUS_CT200H:
      return "LEXUS_CT200H";
    case VehicleModel::KIA_SORENTO:
      return "KIA_SORENTO";
    case VehicleModel::KIA_SPORTAGE:
      return "KIA_SPORTAGE";
    case VehicleModel::AUDI_Q7:
      return "AUDI_Q7";
    case VehicleModel::AUDI_A8L:
      return "AUDI_A8L";
    case VehicleModel::TESLA_MODEL_X:
      return "TESLA_MODEL_X";
    case VehicleModel::TESLA_MODEL_3:
      return "TESLA_MODEL_3";
    case VehicleModel::HYUNDAI_ELANTRA:
      return "HYUNDAI_ELANTRA";
    case VehicleModel::PEUGEOT_206:
      return "PEUGEOT_206";
    case VehicleModel::MAN_TGX:
      return "MAN_TGX";
    case VehicleModel::FACTION:
      return "FACTION";
    case VehicleModel::LINCOLN_MKZ:
      return "LINCOLN_MKZ";
    case VehicleModel::BMW_7:
      return "BMW_7";
    default:
      return "UNRECOGNIZED";
  }
}

/**
 * @brief @ref VehicleModel stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream,
                                VehicleModel vehicle_model) {
  stream << to_string(vehicle_model) << " (" << (int)vehicle_model << ")";
  return stream;
}

/**
 * @brief Information about the vehicle including model and dimensions.
 * @ingroup config_and_ctrl_messages
 */
struct alignas(4) VehicleDetails {
  VehicleModel vehicle_model = VehicleModel::UNKNOWN_VEHICLE;
  uint8_t reserved[10] = {0};

  /** The distance between the front axle and rear axle (in meters). */
  float wheelbase_m = NAN;

  /** The distance between the two front wheels (in meters). */
  float front_track_width_m = NAN;

  /** The distance between the two rear wheels (in meters). */
  float rear_track_width_m = NAN;
};

/**
 * @brief The type of vehicle/wheel speed measurements produced by the vehicle.
 * @ingroup config_and_ctrl_messages
 */
enum class WheelSensorType : uint8_t {
  /** Wheel/vehicle speed data not available. */
  NONE = 0,
  /**
   * Individual wheel rotation rates, reported as an encoder tick rate (in
   * ticks/second). Will be scaled to meters/second using the specified scale
   * factor.
   */
  TICK_RATE = 1,
  /**
   * Individual wheel rotational angles, reported as accumulated encoder
   * ticks.
   * */
  TICKS = 2,
  /** Individual wheel speeds, reported in meters/second. */
  WHEEL_SPEED = 3,
  /** A single value indicating the vehicle speed (in meters/second). */
  VEHICLE_SPEED = 4,
  /** A single wheel rotational angle, reported as accumulated encoder ticks. */
  VEHICLE_TICKS = 5,
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        WheelSensorType.
 * @ingroup config_and_ctrl_messages
 *
 * @param wheel_sensor_type The desired wheel sensor type.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(WheelSensorType wheel_sensor_type) {
  switch (wheel_sensor_type) {
    case WheelSensorType::NONE: {
      return "None";
    }
    case WheelSensorType::TICK_RATE: {
      return "Tick Rate";
    }
    case WheelSensorType::TICKS: {
      return "Ticks";
    }
    case WheelSensorType::WHEEL_SPEED: {
      return "Wheel Speed";
    }
    case WheelSensorType::VEHICLE_SPEED: {
      return "Vehicle Speed";
    }
    case WheelSensorType::VEHICLE_TICKS: {
      return "Vehicle Ticks";
    }
    default: {
      return "None";
    }
  }
}

/**
 * @brief @ref WheelSensorType stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream,
                                WheelSensorType wheel_sensor_type) {
  stream << to_string(wheel_sensor_type) << " (" << (int)wheel_sensor_type
         << ")";
  return stream;
}

/**
 * @brief The type of vehicle/wheel speed measurements to be applied.
 * @ingroup config_and_ctrl_messages
 */
enum class AppliedSpeedType : uint8_t {
  /** Speed data not applied to the system. */
  NONE = 0,
  /** Rear wheel speed data to be applied to the system (recommended). */
  REAR_WHEELS = 1,
  /** Front wheel speed data to be applied to the system. */
  FRONT_WHEELS = 2,
  /** Front and rear wheel speed data to be applied to the system. */
  FRONT_AND_REAR_WHEELS = 3,
  /** Individual vehicle speed to be applied to the system. */
  VEHICLE_BODY = 4,
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        AppliedSpeedType.
 * @ingroup config_and_ctrl_messages
 *
 * @param applied_speed_type The desired applied speed type.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(AppliedSpeedType applied_speed_type) {
  switch (applied_speed_type) {
    case AppliedSpeedType::NONE: {
      return "None";
    }
    case AppliedSpeedType::REAR_WHEELS: {
      return "Rear Wheels";
    }
    case AppliedSpeedType::FRONT_WHEELS: {
      return "Front Wheels";
    }
    case AppliedSpeedType::FRONT_AND_REAR_WHEELS: {
      return "Front and Rear Wheels";
    }
    case AppliedSpeedType::VEHICLE_BODY: {
      return "Vehicle Body";
    }
    default: {
      return "Unrecognized";
    }
  }
}

/**
 * @brief @ref AppliedSpeedType stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream,
                                AppliedSpeedType applied_speed_type) {
  stream << to_string(applied_speed_type) << " (" << (int)applied_speed_type
         << ")";
  return stream;
}

/**
 * @brief Indication of which of the vehicle's wheels are steered.
 * @ingroup config_and_ctrl_messages
 */
enum class SteeringType : uint8_t {
  /** Steered wheels unknown. */
  UNKNOWN = 0,
  /** Front wheels are steered. */
  FRONT = 1,
  /** Front and rear wheels are steered. */
  FRONT_AND_REAR = 2,
};

/**
 * @brief Get a human-friendly string name for the specified @ref SteeringType.
 * @ingroup config_and_ctrl_messages
 *
 * @param steering_type The desired steering type.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(SteeringType steering_type) {
  switch (steering_type) {
    case SteeringType::UNKNOWN: {
      return "Unknown Steering";
    }
    case SteeringType::FRONT: {
      return "Front Steering";
    }
    case SteeringType::FRONT_AND_REAR: {
      return "Front and Rear Steering";
    }
    default: {
      return "Unrecognized";
    }
  }
}

/**
 * @brief @ref SteeringType stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream,
                                SteeringType steering_type) {
  stream << to_string(steering_type) << " (" << (int)steering_type << ")";
  return stream;
}

/**
 * @brief Vehicle/wheel speed measurement configuration settings.
 * @ingroup config_and_ctrl_messages
 *
 * See:
 * - @ref WheelSpeedMeasurement
 * - @ref VehicleSpeedMeasurement
 * - @ref WheelTickMeasurement
 * - @ref VehicleTickMeasurement
 */
struct alignas(4) WheelConfig {
  /**
   * The type of vehicle/wheel speed measurements produced by the vehicle.
   */
  WheelSensorType wheel_sensor_type = WheelSensorType::NONE;

  /**
   * The type of vehicle/wheel speed measurements to be applied to the
   * navigation solution.
   */
  AppliedSpeedType applied_speed_type = AppliedSpeedType::REAR_WHEELS;

  /** Indication of which of the vehicle's wheels are steered. */
  SteeringType steering_type = SteeringType::UNKNOWN;

  uint8_t reserved1[1] = {0};

  /**
   * The nominal rate at which wheel speed measurements will be provided (in
   * seconds).
   */
  float wheel_update_interval_sec = NAN;

  /**
   * The nominal rate at which wheel tick measurements will be provided (in
   * seconds).
   */
  float wheel_tick_output_interval_sec = NAN;

  /**
   * Ratio between angle of the steering wheel and the angle of the wheels on
   * the ground.
   */
  float steering_ratio = NAN;

  /**
   * The scale factor to convert from wheel encoder ticks to distance (in
   * meters/tick). Used for @ref WheelSensorType::TICKS and
   * @ref WheelSensorType::TICK_RATE.
   */
  float wheel_ticks_to_m = NAN;

  /**
   * The maximum value (inclusive) before the wheel tick measurement will roll
   * over.
   *
   * The rollover behavior depends on the value of @ref wheel_ticks_signed. For
   * example, a maximum value of 10 will work as follows:
   * - `wheel_ticks_signed == true`: [-11, 10]
   * - `wheel_ticks_signed == false`: [0, 10]
   *
   * Signed values are assumed to be asymmetric, consistent with a typical 2's
   * complement rollover.
   */
  uint32_t wheel_tick_max_value = 0;

  /**
   * `true` if the reported wheel tick measurements should be interpreted as
   * signed integers, or `false` if they should be interpreted as unsigned
   * integers.
   *
   * See @ref wheel_tick_max_value for details.
   */
  bool wheel_ticks_signed = false;

  /**
   * `true` if the wheel tick measurements increase by a positive amount when
   * driving forward or backward. `false` if wheel tick measurements decrease
   * when driving backward.
   */
  bool wheel_ticks_always_increase = true;

  uint8_t reserved2[2] = {0};
};

/**
 * @brief The signal edge to use when capturing a wheel tick voltage signal.
 * @ingroup config_and_ctrl_messages
 */
enum class TickMode : uint8_t {
  /** Wheel tick capture disabled. */
  OFF = 0,
  /** Capture a wheel tick on the rising edge of the incoming pulse. */
  RISING_EDGE = 1,
  /** Capture a wheel tick on the falling edge of the incoming pulse. */
  FALLING_EDGE = 2,
};

inline const char* to_string(TickMode tick_mode) {
  switch (tick_mode) {
    case TickMode::OFF:
      return "OFF";
    case TickMode::RISING_EDGE:
      return "RISING_EDGE";
    case TickMode::FALLING_EDGE:
      return "FALLING_EDGE";
    default:
      return "UNRECOGNIZED";
  }
}

/**
 * @brief @ref TickMode stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream, TickMode tick_mode) {
  stream << to_string(tick_mode) << " (" << (int)tick_mode << ")";
  return stream;
}

/**
 * @brief The way to interpret an incoming voltage signal, used to indicate
 *        direction of a hardware wheel tick pulse, if available.
 * @ingroup config_and_ctrl_messages
 */
enum class TickDirection : uint8_t {
  /** Wheel tick direction not provided. */
  OFF = 0,
  /**
   * Assume vehicle is moving forward when direction signal voltage is high, and
   * backward when direction signal is low.
   */
  FORWARD_ACTIVE_HIGH = 1,
  /**
   * Assume vehicle is moving forward when direction signal voltage is low, and
   * backward when direction signal is high.
   */
  FORWARD_ACTIVE_LOW = 2,
};

inline const char* to_string(TickDirection tick_direction) {
  switch (tick_direction) {
    case TickDirection::OFF:
      return "OFF";
    case TickDirection::FORWARD_ACTIVE_HIGH:
      return "FORWARD_ACTIVE_HIGH";
    case TickDirection::FORWARD_ACTIVE_LOW:
      return "FORWARD_ACTIVE_LOW";
    default:
      return "UNRECOGNIZED";
  }
}

/**
 * @brief @ref TickDirection stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream,
                                TickDirection tick_direction) {
  stream << to_string(tick_direction) << " (" << (int)tick_direction << ")";
  return stream;
}

/**
 * @brief Hardware wheel encoder configuration settings.
 * @ingroup config_and_ctrl_messages
 *
 * See @ref VehicleTickMeasurement.
 */
struct alignas(4) HardwareTickConfig {
  /**
   * If enabled -- tick mode is not @ref TickMode::OFF -- the device will
   * accumulate ticks received on the I/O pin, and use them as an indication of
   * vehicle speed. If enabled, you must also specify @ref wheel_ticks_to_m to
   * indicate the mapping of wheel tick encoder angle to tire circumference. All
   * other wheel tick-related parameters such as tick capture rate, rollover
   * value, etc. will be set internally.
   *
   * @warning
   * Do not enable this feature if a wheel tick voltage signal is not present.
   */
  TickMode tick_mode = TickMode::OFF;

  /**
   * When direction is @ref TickDirection::OFF, the incoming ticks will be
   * treated as unsigned, meaning the tick count will continue to increase in
   * either direction of travel. If direction is not @ref TickDirection::OFF,
   * a second direction I/O pin will be used to indicate the direction of
   * travel and the accumulated tick count will increase/decrease accordingly.
   */
  TickDirection tick_direction = TickDirection::OFF;

  uint8_t reserved1[2] = {0};

  /**
   * The scale factor to convert from wheel encoder ticks to distance (in
   * meters/tick). Used for @ref WheelSensorType::TICKS and
   * @ref WheelSensorType::TICK_RATE.
   */
  float wheel_ticks_to_m = NAN;
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
  /** This is used for requesting the configuration for all protocols. */
  ALL = 0xFF,
};

/** Setting message_id to this value acts as a wild card. */
constexpr uint16_t ALL_MESSAGES_ID = 0xFFFF;

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
    case ProtocolType::ALL:
      return "ALL";
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
 * @brief Integer ID for NMEA messages.
 */
enum class NmeaMessageType : uint16_t {
  INVALID = 0,

  /**
   * @name Standard NMEA Messages
   * @{
   */
  GGA = 1,
  GLL = 2,
  GSA = 3,
  GSV = 4,
  RMC = 5,
  VTG = 6,
  /** @} */

  /**
   * @name Point One Proprietary Messages
   * @{
   */
  P1CALSTATUS = 1000,
  P1MSG = 1001,
  /** @} */

  /**
   * @name Quectel Proprietary Messages
   * @{
   */
  PQTMVERNO = 1200,
  PQTMVER = 1201,
  PQTMGNSS = 1202,
  /** @} */
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        NmeaMessageType.
 * @ingroup config_and_ctrl_messages
 *
 * @param value The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(NmeaMessageType value) {
  switch (value) {
    case NmeaMessageType::INVALID:
      return "INVALID";
    case NmeaMessageType::GGA:
      return "GGA";
    case NmeaMessageType::GLL:
      return "GLL";
    case NmeaMessageType::GSA:
      return "GSA";
    case NmeaMessageType::GSV:
      return "GSV";
    case NmeaMessageType::RMC:
      return "RMC";
    case NmeaMessageType::VTG:
      return "VTG";
    case NmeaMessageType::P1CALSTATUS:
      return "P1CALSTATUS";
    case NmeaMessageType::P1MSG:
      return "P1MSG";
    case NmeaMessageType::PQTMVERNO:
      return "PQTMVERNO";
    case NmeaMessageType::PQTMVER:
      return "PQTMVER";
    case NmeaMessageType::PQTMGNSS:
      return "PQTMGNSS";
    default:
      return "Unrecognized";
  }
}

/**
 * @brief @ref NmeaMessageType stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream, NmeaMessageType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief The output rate for a message type on an interface.
 */
enum class MessageRate : uint8_t {
  /**
   * Disable output of this message.
   */
  OFF = 0,
  /**
   * Output this message each time a new value is available.
   */
  ON_CHANGE = 1,
  /** Alias for @ref MessageRate::ON_CHANGE. */
  MAX_RATE = 1,
  /**
   * Output this message at this interval. Not supported for all messages or
   * platforms.
   */
  INTERVAL_10_MS = 2,
  /**
   * Output this message at this interval. Not supported for all messages or
   * platforms.
   */
  INTERVAL_20_MS = 3,
  /**
   * Output this message at this interval. Not supported for all messages or
   * platforms.
   */
  INTERVAL_40_MS = 4,
  /**
   * Output this message at this interval. Not supported for all messages or
   * platforms.
   */
  INTERVAL_50_MS = 5,
  /**
   * Output this message at this interval. Not supported for all messages or
   * platforms.
   */
  INTERVAL_100_MS = 6,
  /**
   * Output this message at this interval. Not supported for all messages or
   * platforms.
   */
  INTERVAL_200_MS = 7,
  /**
   * Output this message at this interval. Not supported for all messages or
   * platforms.
   */
  INTERVAL_500_MS = 8,
  /**
   * Output this message at this interval. Not supported for all messages or
   * platforms.
   */
  INTERVAL_1_S = 9,
  /**
   * Output this message at this interval. Not supported for all messages or
   * platforms.
   */
  INTERVAL_2_S = 10,
  /**
   * Output this message at this interval. Not supported for all messages or
   * platforms.
   */
  INTERVAL_5_S = 11,
  /**
   * Output this message at this interval. Not supported for all messages or
   * platforms.
   */
  INTERVAL_10_S = 12,
  /**
   * Restore this message's rate back to its default value.
   */
  DEFAULT = 255
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        MessageRate.
 * @ingroup config_and_ctrl_messages
 *
 * @param value The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(MessageRate value) {
  switch (value) {
    case MessageRate::OFF:
      return "OFF";
    case MessageRate::ON_CHANGE:
      return "ON_CHANGE";
    case MessageRate::INTERVAL_10_MS:
      return "INTERVAL_10_MS";
    case MessageRate::INTERVAL_20_MS:
      return "INTERVAL_20_MS";
    case MessageRate::INTERVAL_40_MS:
      return "INTERVAL_40_MS";
    case MessageRate::INTERVAL_50_MS:
      return "INTERVAL_50_MS";
    case MessageRate::INTERVAL_100_MS:
      return "INTERVAL_100_MS";
    case MessageRate::INTERVAL_200_MS:
      return "INTERVAL_200_MS";
    case MessageRate::INTERVAL_500_MS:
      return "INTERVAL_500_MS";
    case MessageRate::INTERVAL_1_S:
      return "INTERVAL_1_S";
    case MessageRate::INTERVAL_2_S:
      return "INTERVAL_2_S";
    case MessageRate::INTERVAL_5_S:
      return "INTERVAL_5_S";
    case MessageRate::INTERVAL_10_S:
      return "INTERVAL_10_S";
    case MessageRate::DEFAULT:
      return "DEFAULT";
    default:
      return "Unrecognized";
  }
}

/**
 * @brief @ref MessageRate stream operator.
 * @ingroup config_and_ctrl_messages
 */
inline std::ostream& operator<<(std::ostream& stream, MessageRate val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief Set the output rate for the requested message types (@ref
 *        MessageType::SET_MESSAGE_RATE, version 1.0).
 *
 * Multiple message rates can be configured with a single command if wild cards
 * are used for the interface, protocol, or message ID. When multiple messages
 * are specified, the following behaviors apply:
 * - Messages that are currently @ref MessageRate::OFF will not be changed
 *   unless the @ref FLAG_INCLUDE_DISABLED_MESSAGES bit is set in the @ref flags
 *   or the new rate is @ref MessageRate::DEFAULT.
 * - If the rate is an interval, it will only affect the messages that support
 *   being rate controlled.
 *
 * Setting all the messages on an interface to @ref MessageRate::DEFAULT will
 * also restore the default `*_OUTPUT_DIAGNOSTICS_MESSAGES` configuration option
 * value for that interface. See @ref ConfigType.
 *
 * @section set_rate_examples Typical Use Cases
 *
 * @subsection set_rate_restore Restore Default Settings For All Messages
 *
 * To restore the default configuration on UART1 for all message types across all
 * supported protocols, specify the following:
 * - Interface transport type: @ref TransportType::SERIAL
 * - Interface index: 1
 * - Protocol: @ref ProtocolType::ALL
 * - Message ID: @ref ALL_MESSAGES_ID
 * - Rate: @ref MessageRate::DEFAULT
 *
 * @subsection set_rate_restore_nmea Restore Default Settings For All NMEA
 *
 * To restore the default configuration on UART1 for all NMEA message types,
 * specify the following:
 * - Interface transport type: @ref TransportType::SERIAL
 * - Interface index: 1
 * - Protocol: @ref ProtocolType::NMEA
 * - Message ID: @ref ALL_MESSAGES_ID
 * - Rate: @ref MessageRate::DEFAULT
 *
 * @subsection set_rate_change_enabled_rate Change UART1 Output Rate To 1 Hz:
 *
 * To change the rate of all rate-controlled messages (e.g., FusionEngine @ref
 * PoseMessage, NMEA GGA) to 1 Hz on UART1, specify the following:
 * - Interface transport type: @ref TransportType::SERIAL
 * - Interface index: 1
 * - Protocol: @ref ProtocolType::ALL
 * - Message ID: @ref ALL_MESSAGES_ID
 * - Rate: @ref MessageRate::INTERVAL_1_S
 *
 * @note
 * Note that this will not affect any message types that are not rate controlled
 * (e.g., @ref MessageType::EVENT_NOTIFICATION).
 *
 * @subsection set_rate_max_all Change The Uart1 Output Rates For All Messages To Their Max:
 *
 * To change the rate of all messages to their max rate on UART1, specify the
 * following:
 * - Interface transport type: @ref TransportType::SERIAL
 * - Interface index: 1
 * - Protocol: @ref ProtocolType::ALL
 * - flags: @ref FLAG_INCLUDE_DISABLED_MESSAGES
 * - Message ID: @ref ALL_MESSAGES_ID
 * - Rate: @ref MessageRate::ON_CHANGE
 *
 * @note
 * This will enabled every message regardless of whether it's @ref
 * MessageRate::OFF or whether or not it's rate controlled.
 *
 * @subsection set_and_save_rate_max_all Change And Save The UART1 Output Rates For All Messages To Their Max:
 *
 * To change the rate of all messages to their max rate on UART1, specify the
 * following:
 * - Interface transport type: @ref TransportType::SERIAL
 * - Interface index: 1
 * - Protocol: @ref ProtocolType::ALL
 * - flags: 0x03 (@ref FLAG_INCLUDE_DISABLED_MESSAGES | @ref FLAG_APPLY_AND_SAVE)
 * - Message ID: @ref ALL_MESSAGES_ID
 * - Rate: @ref MessageRate::ON_CHANGE
 *
 * @note
 * Both of the bit flags are set for this message. This will cause the
 * configuration to be saved to non-volatile memory.
 *
 * @ingroup config_and_ctrl_messages
 */
struct alignas(4) SetMessageRate : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::SET_MESSAGE_RATE;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** Flag to immediately save the config after applying this setting. */
  static constexpr uint8_t FLAG_APPLY_AND_SAVE = 0x01;

  /**
   * Flag to apply bulk interval changes to all messages instead of just
   * enabled messages.
   */
  static constexpr uint8_t FLAG_INCLUDE_DISABLED_MESSAGES = 0x02;

  /**
   * The output interface to configure. If @ref TransportType::ALL, set rates on
   * all supported interfaces.
   */
  InterfaceID output_interface = {};

  /**
   * The message protocol being configured. If @ref ProtocolType::ALL, set rates
   * on all supported protocols and @ref message_id is ignored.
   */
  ProtocolType protocol = ProtocolType::INVALID;

  /** Bitmask of additional flags to modify the command. */
  uint8_t flags = 0;

  /**
   * The ID of the desired message type (e.g., 10000 for FusionEngine
   * @ref MessageType::POSE messages). See @ref NmeaMessageType for NMEA-0183
   * messages. If @ref ALL_MESSAGES_ID, set the rate for all messages on the
   * selected interface and protocol.
   */
  uint16_t message_id = ALL_MESSAGES_ID;

  /** The desired message rate. */
  MessageRate rate = MessageRate::OFF;

  uint8_t reserved2[3] = {0};
};

/**
 * @brief Get the configured output rate for the he requested message type on
 *        the specified interface (@ref MessageType::GET_MESSAGE_RATE,
 *        version 1.0).
 * @ingroup config_and_ctrl_messages
 *
 * Multiple message rates can be requested with a single command if wild cards
 * are used for the protocol, or message ID.
 *
 * The device will respond with a @ref MessageRateResponse
 * containing the values.
 */
struct alignas(4) GetMessageRate : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::GET_MESSAGE_RATE;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * The output interface to be queried. @ref TransportType::ALL is not
   * supported.
   */
  InterfaceID output_interface = {};

  /**
   * The desired message protocol. If @ref ProtocolType::ALL, return the current
   * settings for all supported protocols and @ref message_id is ignored.
   */
  ProtocolType protocol = ProtocolType::INVALID;

  /** The source of the parameter value (active, saved, etc.). */
  ConfigurationSource request_source = ConfigurationSource::ACTIVE;

  /**
   * The ID of the desired message type (e.g., 10000 for FusionEngine
   * @ref MessageType::POSE messages). See @ref NmeaMessageType for NMEA-0183
   * messages. If @ref ALL_MESSAGES_ID, return the current settings for all
   * supported messages on the selected interface and protocol.
   */
  uint16_t message_id = ALL_MESSAGES_ID;
};

/**
 * @brief An element of a @ref MessageRateResponse message.
 * @ingroup config_and_ctrl_messages
 */
struct alignas(4) MessageRateResponseEntry {
  /**
   * Flag to indicate the active value for this configuration differs from the
   * value saved to persistent memory.
   */
  static constexpr uint8_t FLAG_ACTIVE_DIFFERS_FROM_SAVED = 0x1;

  /** The protocol of the message being returned. */
  ProtocolType protocol = ProtocolType::INVALID;

  /** Flags that describe the entry. */
  uint8_t flags = 0;

  /**
   * The ID of the returned message type (e.g., 10000 for FusionEngine
   * @ref MessageType::POSE messages). See @ref NmeaMessageType for NMEA-0183
   * messages.
   */
  uint16_t message_id = 0;

  /** The current configuration for this message. */
  MessageRate configured_rate = MessageRate::OFF;

  /**
   * The currently active output rate for this message, factoring in effects of
   * additional configuration settings that may override the configured rate
   * such as enabling diagnostic output.
   */
  MessageRate effective_rate = MessageRate::OFF;

  uint8_t reserved1[2] = {0};
};

/**
 * @brief Response to a @ref GetMessageRate request (@ref
 *        MessageType::MESSAGE_RATE_RESPONSE, version 1.1).
 * @ingroup config_and_ctrl_messages
 */
struct alignas(4) MessageRateResponse : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::MESSAGE_RATE_RESPONSE;
  static constexpr uint8_t MESSAGE_VERSION = 1;

  /** The source of the parameter value (active, saved, etc.). */
  ConfigurationSource config_source = ConfigurationSource::ACTIVE;

  /** The response status (success, error, etc.). */
  Response response = Response::OK;

  /** The number of rates reported by this message. */
  uint16_t num_rates = 0;

  /** The output interface corresponding with this response. */
  InterfaceID output_interface = {};

  /* This in then followed by an array of num_rates MessageRateResponseEntry */
  // MessageRateResponseEntry rates[num_rates]
};

/** @} */

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one

#ifdef _MSC_VER
#  pragma warning(pop)
#endif
