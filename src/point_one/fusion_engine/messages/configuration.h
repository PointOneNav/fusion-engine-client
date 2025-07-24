/**************************************************************************/ /**
 * @brief Device configuration settings control messages.
 * @file
 ******************************************************************************/

#pragma once

#include "point_one/fusion_engine/common/portability.h"
#include "point_one/fusion_engine/messages/data_version.h"
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
 * @defgroup config_types Device Configuration Settings Control
 * @brief Messages/types for configuring device parameters (lever arms,
 *        orientation, wheel speed settings, etc.).
 * @ingroup config_and_ctrl_messages
 *
 * See also @ref import_export.
 ******************************************************************************/

/**
 * @brief An identifier for the contents of a parameter configuration message.
 * @ingroup config_types
 *
 * See also @ref SetConfigMessage.
 */
enum class ConfigType : uint16_t {
  INVALID = 0,

  /**
   * The location of the device IMU with respect to the vehicle body frame,
   * resolved in the vehicle body frame (in meters).
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
   * The location of the primary GNSS antenna with respect to the vehicle body
   * frame, resolved in the vehicle body frame (in meters).
   *
   * Payload format: @ref Point3f
   */
  GNSS_LEVER_ARM = 18,

  /**
   * The offset of the desired output location with respect to the vehicle
   * body frame, resolved in the vehicle body frame (in meters).
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
   * Information pertaining to wheel speed/rotation measurements when wheel data
   * is transmitted via software.
   *
   * @note
   * For hardware wheel tick voltage capture, use @ref
   * ConfigType::HARDWARE_TICK_CONFIG instead.
   *
   * Payload format: @ref WheelConfig
   */
  WHEEL_CONFIG = 21,

  /**
   * Indicates the mode and direction used when capturing vehicle wheel tick
   * data from a voltage pulse on an I/O pin.
   *
   * @note
   * For software wheel tick capture (wheel ticks sent as FusionEngine messages
   * or on a CAN bus), use @ref ConfigType::WHEEL_CONFIG instead.
   *
   * Payload format: @ref HardwareTickConfig
   */
  HARDWARE_TICK_CONFIG = 22,

  /**
   * Used to set horizontal (yaw) & vertical (pitch) biases (in degrees) on
   * a dual-antenna heading platform configuration (deprecated).
   *
   * @deprecated
   * Use @ref ConfigType::GNSS_AUX_LEVER_ARM instead.
   */
  DEPRECATED_HEADING_BIAS = 23,

  /**
   * The location of the secondary GNSS antenna with respect to the vehicle body
   * frame on a dual-antenna platform, resolved in the vehicle body frame (in
   * meters).
   *
   * For dual-antenna systems, the secondary or auxiliary antenna is used to
   * measure vehicle yaw and pitch.
   *
   * Payload format: @ref Point3f
   */
  GNSS_AUX_LEVER_ARM = 24,

  /**
   * A bitmask indicating which GNSS constellations are enabled.
   *
   * Payload format: `uint32_t` (see @ref sat_type_masks)
   */
  ENABLED_GNSS_SYSTEMS = 50,

  /**
   * A bitmask indicating which GNSS frequency bands are enabled.
   *
   * Payload format: `uint32_t` (see @ref freq_band_masks)
   */
  ENABLED_GNSS_FREQUENCY_BANDS = 51,

  /**
   * Specify a UTC leap second count override value to use for all UTC time
   * conversions. Setting this value will disable all internal leap second
   * sources, including data received from the GNSS almanac decoded from
   * available signals.
   *
   * Set to -1 to disable leap second override and re-enable internal leap
   * second handling.
   *
   * Payload format: `int32_t`
   */
  LEAP_SECOND = 52,

  /**
   * Specify a GPS legacy week rollover count override to use when converting
   * all legacy 10-bit GPS week numbers. Setting this value will disable all
   * internal week rollover sources, including data received from modern GPS
   * navigation messages (CNAV, CNAV2) or non-GPS constellations.
   *
   * Set to -1 to disable week rollover override and re-enable internal
   * handling.
   *
   * Payload format: `int32_t`
   */
  GPS_WEEK_ROLLOVER = 53,

  /**
   * Ionospheric delay model configuration.
   *
   * Payload format: @ref IonosphereConfig
   */
  IONOSPHERE_CONFIG = 54,

  /**
   * Tropospheric delay model configuration.
   *
   * Payload format: @ref TroposphereConfig
   */
  TROPOSPHERE_CONFIG = 55,

  /**
   * Change a configuration setting for a specified output interface.
   *
   * Payload format: `InterfaceConfigSubmessage`
   */
  INTERFACE_CONFIG = 200,

  /**
   * Configure the UART1 serial baud rate (in bits/second).
   *
   * @deprecated
   * The @ref ConfigType::INTERFACE_CONFIG type combined with @ref
   * InterfaceConfigType::BAUD_RATE in the @ref InterfaceConfigSubmessage should
   * be used to configure this value going forward.
   *
   * Payload format: `uint32_t`
   */
  UART1_BAUD = 256,

  /**
   * Configure the UART2 serial baud rate (in bits/second).
   *
   * @deprecated
   * The @ref ConfigType::INTERFACE_CONFIG type combined with @ref
   * InterfaceConfigType::BAUD_RATE in the @ref InterfaceConfigSubmessage should
   * be used to configure this value going forward.
   *
   * Payload format: `uint32_t`
   */
  UART2_BAUD = 257,

  /**
   * Enable/disable output of diagnostic data on UART1.
   *
   * @deprecated
   * The @ref ConfigType::INTERFACE_CONFIG type combined with @ref
   * InterfaceConfigType::OUTPUT_DIAGNOSTICS_MESSAGES in the @ref
   * InterfaceConfigSubmessage should be used to configure this value going
   * forward.
   *
   * @note
   * Enabling this setting will override the message rate/off settings for some
   * FusionEngine messages.
   *
   * Payload format: `bool`
   */
  UART1_OUTPUT_DIAGNOSTICS_MESSAGES = 258,

  /**
   * Enable/disable output of diagnostic data on UART2.
   *
   * @deprecated
   * The @ref ConfigType::INTERFACE_CONFIG type combined with @ref
   * InterfaceConfigType::OUTPUT_DIAGNOSTICS_MESSAGES in the @ref
   * InterfaceConfigSubmessage should be used to configure this value going
   * forward.
   *
   * @note
   * Enabling this setting will override the message rate/off settings for some
   * FusionEngine messages.
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

  /**
   * A string for identifying a device.
   *
   * This is a string of ASCII characters padded to 32 bytes with `NULL`.
   *
   * Payload format: `char[32]`
   */
  USER_DEVICE_ID = 301,

  /**
   * A bitmask indicating which profiling features are enabled.
   *
   * Payload format: `uint8_t` (`0` for disabled and `0xFF` for all features
   * enabled. Individual bits are device specific.)
   */
  PROFILING_MASK = 310,

  /**
   * Configuration of L-band Demodulator Parameters.
   *
   * @note
   * This setting is only available on devices with an L-band receiver.
   *
   * Payload format: @ref LBandConfig
   */
  LBAND_PARAMETERS = 1024,
};

/**
 * @brief Get a human-friendly string name for the specified @ref ConfigType.
 * @ingroup config_types
 *
 * @param type The desired configuration parameter type.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(ConfigType type) {
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

    case ConfigType::DEPRECATED_HEADING_BIAS:
      return "Heading Bias";

    case ConfigType::GNSS_AUX_LEVER_ARM:
      return "GNSS Aux Lever Arm";

    case ConfigType::ENABLED_GNSS_SYSTEMS:
      return "Enabled GNSS Systems";

    case ConfigType::ENABLED_GNSS_FREQUENCY_BANDS:
      return "Enabled GNSS Frequency Bands";

    case ConfigType::LEAP_SECOND:
      return "Leap Second";

    case ConfigType::GPS_WEEK_ROLLOVER:
      return "GPS Week Rollover";

    case ConfigType::IONOSPHERE_CONFIG:
      return "Ionosphere Config";

    case ConfigType::TROPOSPHERE_CONFIG:
      return "Troposphere Config";

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

    case ConfigType::USER_DEVICE_ID:
      return "User Device ID";

    case ConfigType::PROFILING_MASK:
      return "Profiling Features Enabled";

    case ConfigType::INTERFACE_CONFIG:
      return "Interface Submessage";

    case ConfigType::LBAND_PARAMETERS:
      return "LBand Parameters";
  }
  return "Unrecognized Configuration";
}

/**
 * @brief @ref ConfigType stream operator.
 * @ingroup config_types
 */
inline p1_ostream& operator<<(p1_ostream& stream, ConfigType type) {
  stream << to_string(type) << " (" << (int)type << ")";
  return stream;
}

/**
 * @brief The type of a device's configuration settings.
 * @ingroup config_types
 */
enum class ConfigurationSource : uint8_t {
  ACTIVE = 0, ///< Active configuration currently in use by the device.
  SAVED = 1, ///< Settings currently saved to persistent storage.
  /**
   * Read only device defaults. Attempting to write to this source will fail
   * with a @ref Response::VALUE_ERROR.
   */
  DEFAULT = 2,
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        ConfigurationSource.
 * @ingroup config_types
 *
 * @param source The desired configuration source.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(ConfigurationSource source) {
  switch (source) {
    case ConfigurationSource::ACTIVE:
      return "Active";

    case ConfigurationSource::SAVED:
      return "Saved";

    case ConfigurationSource::DEFAULT:
      return "Default";
  }

  return "Unrecognized Source";
}

/**
 * @brief @ref ConfigurationSource stream operator.
 * @ingroup config_types
 */
inline p1_ostream& operator<<(p1_ostream& stream, ConfigurationSource source) {
  stream << to_string(source) << " (" << (int)source << ")";
  return stream;
}

/**
 * @brief The type configuration save operation to be performed.
 * @ingroup config_types
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
 * @ingroup config_types
 *
 * @param action The desired save operation.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(SaveAction action) {
  switch (action) {
    case SaveAction::SAVE:
      return "Save";

    case SaveAction::REVERT_TO_SAVED:
      return "Revert To Saved";

    case SaveAction::REVERT_TO_DEFAULT:
      return "Revert To Default";
  }

  return "Unrecognized";
}

/**
 * @brief @ref SaveAction stream operator.
 * @ingroup config_types
 */
inline p1_ostream& operator<<(p1_ostream& stream, SaveAction action) {
  stream << to_string(action) << " (" << (int)action << ")";
  return stream;
}

/**
 * @brief Set a user configuration parameter (@ref MessageType::SET_CONFIG,
 *        version 1.0).
 * @ingroup config_types
 *
 * This message must be followed by the parameter value to be used:
 *
 * ```
 * {MessageHeader, SetConfigMessage, Parameter[data_length_bytes]}
 * ```
 *
 * The format of the parameter value is defined by the the specified @ref
 * config_type (@ref ConfigType). For example, an antenna lever arm definition
 * may require three 32-bit `float` values, one for each axis, while a serial
 * port baud rate may be specified as single 32-bit unsigned integer
 * (`uint32_t`).
 *
 * Not all parameters defined in @ref ConfigType are supported on all devices.
 *
 * Parameter changes are applied to the device's active configuration
 * immediately, but are not saved to persistent storage and will be restored to
 * their previous values on reset. To save configuration settings to persistent
 * storage, see @ref SaveConfigMessage.
 *
 * # Expected Response
 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request succeeded.
 */
struct P1_ALIGNAS(4) SetConfigMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::SET_CONFIG;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** Flag to immediately save the config after applying this setting. */
  static constexpr uint8_t FLAG_APPLY_AND_SAVE = 0x01;
  /**
   * Flag to restore the config_type back to its default value.
   *
   * When set, the @ref config_length_bytes should be 0 and no data should be
   * included unless the config_type is @ref ConfigType::INTERFACE_CONFIG. In
   * that case the @ref config_length_bytes should be
   * `sizeof(InterfaceConfigSubmessage)` with a an @ref
   * InterfaceConfigSubmessage as the parameter value without any further
   * payload.
   */
  static constexpr uint8_t FLAG_REVERT_TO_DEFAULT = 0x02;

  /** The type of parameter to be configured. */
  ConfigType config_type;

  /** Bitmask of additional flags to modify the command. */
  uint8_t flags = 0;

  uint8_t reserved[1] = {0};

  /** The size of the parameter value (in bytes). */
  uint32_t config_length_bytes = 0;
};

/**
 * @brief Query the value of a user configuration parameter (@ref
 *        MessageType::GET_CONFIG, version 1.1).
 * @ingroup config_types
 *
 * # Expected Response
 * The device will respond with a @ref ConfigResponseMessage containing the
 * requested parameter value or an error @ref Response value if the request did
 * not succeed.
 */
struct P1_ALIGNAS(4) GetConfigMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::GET_CONFIG;
  static constexpr uint8_t MESSAGE_VERSION = 1;

  /** The desired parameter. */
  ConfigType config_type = ConfigType::INVALID;

  /** The config source to request data from (active, saved, etc.). */
  ConfigurationSource request_source = ConfigurationSource::ACTIVE;

  uint8_t reserved[1] = {0};

  /**
   * When @ref config_type is @ref ConfigType::INTERFACE_CONFIG, a @ref
   * InterfaceConfigSubmessage must be added to the end of this message with
   * empty @ref InterfaceConfigSubmessage::config_data.
   */
  //uint8_t optional_submessage_header[0];
};

/**
 * @brief Save or reload configuration settings (@ref MessageType::SAVE_CONFIG,
 *        version 1.0).
 * @ingroup config_types
 *
 * # Expected Response
 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request succeeded.
 */
struct P1_ALIGNAS(4) SaveConfigMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::SAVE_CONFIG;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The action to performed. */
  SaveAction action = SaveAction::SAVE;

  uint8_t reserved[3] = {0};
};

/**
 * @brief Response to a @ref GetConfigMessage request (@ref
 *        MessageType::CONFIG_RESPONSE, version 1.0).
 * @ingroup config_types
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
 * The @ref response field will indicate the status of the requested value. If
 * the response is not @ref Response::OK, the parameter value may be omitted and
 * @ref config_length_bytes will be set to 0.
 *
 * In response to a @ref GetConfigMessage with an invalid or unsupported @ref
 * ConfigType, @ref config_type in the resulting @ref ConfigResponseMessage will
 * be set to @ref ConfigType::INVALID, and @ref response will indicate the
 * reason. Note that all @ref GetConfigMessage requests, including invalid and
 * rejected requests, will receive a @ref ConfigResponseMessage, not a
 * @ref CommandResponseMessage.
 */
struct P1_ALIGNAS(4) ConfigResponseMessage : public MessagePayload {
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

  /** The size of the parameter value (in bytes). */
  uint32_t config_length_bytes = 0;

  /**
   * A pointer to the beginning of the configuration parameter value.
   *
   * The size and format of the contents is specified by the @ref config_type.
   * See @ref ConfigType.
   */
  //uint8_t config_change_data[0];
};

/**
 * @brief A 3-dimensional vector (used for lever arms, etc.).
 * @ingroup config_types
 */
struct P1_ALIGNAS(4) Point3f {
  float x = NAN;
  float y = NAN;
  float z = NAN;
};

/**
 * @brief The orientation of a device with respect to the vehicle body axes.
 * @ingroup config_types
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
struct P1_ALIGNAS(4) CoarseOrientation {
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
 * @ingroup config_types
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
  LEXUS_RX450H = 21,

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
  FACTION_V2 = 161,

  LINCOLN_MKZ = 180,

  BMW_7 = 200,
  BMW_MOTORRAD = 201,

  VW_4 = 220,

  RIVIAN = 240,

  FLEXRAY_DEVICE_AUDI_ETRON = 260,

  ISUZU_F_SERIES = 280,
};

/**
 * @brief Get a human-friendly string name for the specified @ref VehicleModel.
 * @ingroup config_types
 *
 * @param vehicle_model The desired vehicle model.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(VehicleModel vehicle_model) {
  switch (vehicle_model) {
    case VehicleModel::UNKNOWN_VEHICLE:
      return "UNKNOWN";
    case VehicleModel::DATASPEED_CD4:
      return "DATASPEED_CD4";
    case VehicleModel::J1939:
      return "J1939";
    case VehicleModel::LEXUS_CT200H:
      return "LEXUS_CT200H";
    case VehicleModel::LEXUS_RX450H:
      return "LEXUS_RX450H";
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
    case VehicleModel::FACTION_V2:
      return "FACTION_V2";
    case VehicleModel::LINCOLN_MKZ:
      return "LINCOLN_MKZ";
    case VehicleModel::BMW_7:
      return "BMW_7";
    case VehicleModel::BMW_MOTORRAD:
      return "BMW_MOTORRAD";
    case VehicleModel::VW_4:
      return "VW_4";
    case VehicleModel::RIVIAN:
      return "RIVIAN";
    case VehicleModel::FLEXRAY_DEVICE_AUDI_ETRON:
      return "FLEXRAY_DEVICE_AUDI_ETRON";
    case VehicleModel::ISUZU_F_SERIES:
      return "ISUZU_F_SERIES";
  }

  return "UNRECOGNIZED";
}

/**
 * @brief @ref VehicleModel stream operator.
 * @ingroup config_types
 */
inline p1_ostream& operator<<(p1_ostream& stream, VehicleModel vehicle_model) {
  stream << to_string(vehicle_model) << " (" << (int)vehicle_model << ")";
  return stream;
}

/**
 * @brief Information about the vehicle including model and dimensions.
 * @ingroup config_types
 */
struct P1_ALIGNAS(4) VehicleDetails {
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
 * @ingroup config_types
 */
enum class WheelSensorType : uint8_t {
  /** Wheel/vehicle speed data not available. */
  NONE = 0,
  // RESERVED = 1,
  /**
   * Individual rotational angle measurements for multiple wheels, reported as
   * accumulated encoder ticks. See @ref WheelTickInput.
   * */
  TICKS = 2,
  /**
   * Individual speed measurements for multiple wheels, reported in
   * meters/second. See @ref WheelSpeedInput.
   */
  WHEEL_SPEED = 3,
  /**
   * A single value indicating the vehicle speed (in meters/second). See @ref
   * VehicleSpeedInput.
   */
  VEHICLE_SPEED = 4,
  /**
   * A single wheel rotational angle, reported as accumulated encoder ticks. See
   * @ref VehicleSpeedInput.
   */
  VEHICLE_TICKS = 5,
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        WheelSensorType.
 * @ingroup config_types
 *
 * @param wheel_sensor_type The desired wheel sensor type.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(WheelSensorType wheel_sensor_type) {
  switch (wheel_sensor_type) {
    case WheelSensorType::NONE:
      return "None";
    case WheelSensorType::TICKS:
      return "Ticks";
    case WheelSensorType::WHEEL_SPEED:
      return "Wheel Speed";
    case WheelSensorType::VEHICLE_SPEED:
      return "Vehicle Speed";
    case WheelSensorType::VEHICLE_TICKS:
      return "Vehicle Ticks";
  }

  return "None";
}

/**
 * @brief @ref WheelSensorType stream operator.
 * @ingroup config_types
 */
inline p1_ostream& operator<<(p1_ostream& stream,
                              WheelSensorType wheel_sensor_type) {
  stream << to_string(wheel_sensor_type) << " (" << (int)wheel_sensor_type
         << ")";
  return stream;
}

/**
 * @brief The type of vehicle/wheel speed measurements to be applied.
 * @ingroup config_types
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
 * @ingroup config_types
 *
 * @param applied_speed_type The desired applied speed type.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(AppliedSpeedType applied_speed_type) {
  switch (applied_speed_type) {
    case AppliedSpeedType::NONE:
      return "None";
    case AppliedSpeedType::REAR_WHEELS:
      return "Rear Wheels";
    case AppliedSpeedType::FRONT_WHEELS:
      return "Front Wheels";
    case AppliedSpeedType::FRONT_AND_REAR_WHEELS:
      return "Front and Rear Wheels";
    case AppliedSpeedType::VEHICLE_BODY:
      return "Vehicle Body";
  }

  return "Unrecognized";
}

/**
 * @brief @ref AppliedSpeedType stream operator.
 * @ingroup config_types
 */
inline p1_ostream& operator<<(p1_ostream& stream,
                              AppliedSpeedType applied_speed_type) {
  stream << to_string(applied_speed_type) << " (" << (int)applied_speed_type
         << ")";
  return stream;
}

/**
 * @brief Indication of which of the vehicle's wheels are steered.
 * @ingroup config_types
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
 * @ingroup config_types
 *
 * @param steering_type The desired steering type.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(SteeringType steering_type) {
  switch (steering_type) {
    case SteeringType::UNKNOWN:
      return "Unknown Steering";
    case SteeringType::FRONT:
      return "Front Steering";
    case SteeringType::FRONT_AND_REAR:
      return "Front and Rear Steering";
  }

  return "Unrecognized";
}

/**
 * @brief @ref SteeringType stream operator.
 * @ingroup config_types
 */
inline p1_ostream& operator<<(p1_ostream& stream, SteeringType steering_type) {
  stream << to_string(steering_type) << " (" << (int)steering_type << ")";
  return stream;
}

/**
 * @brief Software vehicle/wheel speed measurement configuration settings.
 * @ingroup config_types
 *
 * @warning
 * The @ref WheelConfig payload is intended for use on vehicles where wheel
 * speed or angle (tick) data is received via software, either using
 * FusionEngine measurement messages, or from another software data source such
 * as a vehicle CAN bus. For vehicles using a hardware wheel tick voltage
 * signal, use @ref HardwareTickConfig instead.
 *
 * Wheel data may be differential (measurements from each individual wheel), or
 * scalar (a single speed measurement for the vehicle body).
 *
 * When using software wheel data, you must also specify @ref VehicleDetails,
 * which is used to describe the vehicle dimensions and make/model.
 *
 * See also:
 * - @ref WheelSpeedInput
 * - @ref VehicleSpeedInput
 * - @ref WheelTickInput
 * - @ref VehicleTickInput
 */
struct P1_ALIGNAS(4) WheelConfig {
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
   * The rate at which wheel speed/tick measurements will be sent to the device
   * (in seconds).
   *
   * @note
   * This parameter is required when using software wheel measurements. It
   * may not be `NAN` if wheel measurements are enabled, and cannot be
   * determined automatically by the device.
   */
  float wheel_update_interval_sec = NAN;

  /**
   * Override the rate at which wheel tick measurements will be used by the
   * navigation engine (in seconds).
   *
   * If this parameter is `NAN` (default), the best rate will be selected
   * automatically by the device based on the input rate (@ref
   * wheel_update_interval_sec) and the wheel tick quantization (@ref
   * wheel_ticks_to_m).
   *
   * @warning
   * For most system configurations, we recommend setting this value to `NAN` to
   * let the device choose the appropriate setting. Use this setting with
   * caution.
   */
  float wheel_tick_output_interval_sec = NAN;

  /**
   * Ratio between angle of the steering wheel and the angle of the wheels on
   * the ground.
   *
   * Used when applying measurements from steered wheels only, ignored
   * otherwise.
   */
  float steering_ratio = NAN;

  /**
   * The scale factor to convert from wheel encoder ticks to distance (in
   * meters/tick).
   *
   * Used for @ref WheelSensorType::TICKS and @ref
   * WheelSensorType::VEHICLE_TICKS, ignored for wheel speed input.
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
   *
   * Used for @ref WheelSensorType::TICKS and @ref
   * WheelSensorType::VEHICLE_TICKS, ignored for wheel speed input.
   */
  uint32_t wheel_tick_max_value = 0;

  /**
   * `true` if the reported wheel tick measurements should be interpreted as
   * signed integers, or `false` if they should be interpreted as unsigned
   * integers.
   *
   * Used for @ref WheelSensorType::TICKS and @ref
   * WheelSensorType::VEHICLE_TICKS, ignored for wheel speed input. See
   * @ref wheel_tick_max_value for details.
   */
  bool wheel_ticks_signed = false;

  /**
   * `true` if the wheel tick measurements increase by a positive amount when
   * driving forward or backward. `false` if wheel tick measurements decrease
   * when driving backward.
   *
   * Used for @ref WheelSensorType::TICKS and @ref
   * WheelSensorType::VEHICLE_TICKS, ignored for wheel speed input.
   */
  bool wheel_ticks_always_increase = true;

  uint8_t reserved2[2] = {0};
};

/**
 * @brief The signal edge to use when capturing a wheel tick voltage signal.
 * @ingroup config_types
 */
enum class TickMode : uint8_t {
  /** Wheel tick capture disabled. */
  OFF = 0,
  /** Capture a wheel tick on the rising edge of the incoming pulse. */
  RISING_EDGE = 1,
  /** Capture a wheel tick on the falling edge of the incoming pulse. */
  FALLING_EDGE = 2,
};

P1_CONSTEXPR_FUNC const char* to_string(TickMode tick_mode) {
  switch (tick_mode) {
    case TickMode::OFF:
      return "OFF";
    case TickMode::RISING_EDGE:
      return "RISING_EDGE";
    case TickMode::FALLING_EDGE:
      return "FALLING_EDGE";
  }

  return "UNRECOGNIZED";
}

/**
 * @brief @ref TickMode stream operator.
 * @ingroup config_types
 */
inline p1_ostream& operator<<(p1_ostream& stream, TickMode tick_mode) {
  stream << to_string(tick_mode) << " (" << (int)tick_mode << ")";
  return stream;
}

/**
 * @brief The way to interpret an incoming voltage signal, used to indicate
 *        direction of a hardware wheel tick pulse, if available.
 * @ingroup config_types
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

P1_CONSTEXPR_FUNC const char* to_string(TickDirection tick_direction) {
  switch (tick_direction) {
    case TickDirection::OFF:
      return "OFF";
    case TickDirection::FORWARD_ACTIVE_HIGH:
      return "FORWARD_ACTIVE_HIGH";
    case TickDirection::FORWARD_ACTIVE_LOW:
      return "FORWARD_ACTIVE_LOW";
  }

  return "UNRECOGNIZED";
}

/**
 * @brief @ref TickDirection stream operator.
 * @ingroup config_types
 */
inline p1_ostream& operator<<(p1_ostream& stream,
                              TickDirection tick_direction) {
  stream << to_string(tick_direction) << " (" << (int)tick_direction << ")";
  return stream;
}

/**
 * @brief Hardware wheel tick encoder configuration settings.
 * @ingroup config_types
 *
 * @warning
 * The @ref HardwareTickConfig payload is intended for use on vehicles with a
 * physical voltage signal, generated by a wheel encoder, that produces a series
 * of voltage pulses (encoder ticks) as the vehicle’s wheel rotates. These ticks
 * will be captured by the device on an input pin and used to indicate vehicle
 * speed. For vehicles using software wheel speed/tick information, including
 * data send using FusionEngine messages or a vehicle CAN bus, use @ref
 * WheelConfig instead.
 *
 * @note
 * In addition to the wheel tick signal, an optional voltage signal may be
 * provided to indicate vehicle direction. If this signal is not connected, the
 * @ref tick_direction setting MUST be set to `OFF` otherwise there will be
 * substantial errors in dead reckoning.
 *
 * See also @ref VehicleTickInput.
 */
struct P1_ALIGNAS(4) HardwareTickConfig {
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
   * meters/tick). Used for @ref WheelSensorType::TICKS.
   */
  float wheel_ticks_to_m = NAN;
};

/**
 * @brief The ionospheric delay model to use.
 * @ingroup config_types
 */
enum class IonoDelayModel : uint8_t {
  /** Select the best available ionospheric delay model. */
  AUTO = 0,
  /** Ionospheric delay model disabled. */
  OFF = 1,
  /** Use the Klobuchar ionospheric model. */
  KLOBUCHAR = 2,
  /** Use the SBAS ionospheric model. */
  SBAS = 3,
};

P1_CONSTEXPR_FUNC const char* to_string(IonoDelayModel iono_delay_model) {
  switch (iono_delay_model) {
    case IonoDelayModel::AUTO:
      return "AUTO";
    case IonoDelayModel::OFF:
      return "OFF";
    case IonoDelayModel::KLOBUCHAR:
      return "KLOBUCHAR";
    case IonoDelayModel::SBAS:
      return "SBAS";
  }

  return "UNRECOGNIZED";
}

/**
 * @brief @ref IonoDelayModel stream operator.
 * @ingroup config_types
 */
inline p1_ostream& operator<<(p1_ostream& stream,
                              IonoDelayModel iono_delay_model) {
  stream << to_string(iono_delay_model) << " (" << (int)iono_delay_model << ")";
  return stream;
}

/**
 * @brief Ionospheric delay model configuration.
 * @ingroup config_types
 */
struct P1_ALIGNAS(4) IonosphereConfig {
  /** The ionospheric delay model to use. */
  IonoDelayModel iono_delay_model = IonoDelayModel::AUTO;

  uint8_t reserved[3] = {0};
};

/**
 * @brief The tropospheric delay model to use.
 * @ingroup config_types
 */
enum class TropoDelayModel : uint8_t {
  /** Select the best available tropospheric delay model. */
  AUTO = 0,
  /** Tropospheric delay model disabled. */
  OFF = 1,
  /** Use the Saastamoinen tropospheric model. */
  SAASTAMOINEN = 2,
};

P1_CONSTEXPR_FUNC const char* to_string(TropoDelayModel tropo_delay_model) {
  switch (tropo_delay_model) {
    case TropoDelayModel::AUTO:
      return "AUTO";
    case TropoDelayModel::OFF:
      return "OFF";
    case TropoDelayModel::SAASTAMOINEN:
      return "SAASTAMOINEN";
  }

  return "UNRECOGNIZED";
}

/**
 * @brief @ref TropoDelayModel stream operator.
 * @ingroup config_types
 */
inline p1_ostream& operator<<(p1_ostream& stream,
                              TropoDelayModel tropo_delay_model) {
  stream << to_string(tropo_delay_model) << " (" << (int)tropo_delay_model
         << ")";
  return stream;
}

/**
 * @brief Tropospheric delay model configuration.
 * @ingroup config_types
 */
struct P1_ALIGNAS(4) TroposphereConfig {
  /** The tropospheric delay model to use. */
  TropoDelayModel tropo_delay_model = TropoDelayModel::AUTO;

  uint8_t reserved[3] = {0};
};

/**************************************************************************/ /**
 * @defgroup import_export Device Configuration Import/Export
 * @brief Messages for importing/exporting device configuration.
 * @ingroup config_and_ctrl_messages
 *
 * See also @ref config_types.
 ******************************************************************************/

/**
 * @brief Type of data stored on device.
 * @ingroup import_export
 */
enum class DataType : uint8_t {
  CALIBRATION_STATE = 0,
  CRASH_LOG = 1,
  FILTER_STATE = 2,
  USER_CONFIG = 3,
  INVALID = 255
};

/**
 * @brief Get a string representation of a @ref DataType.
 * @ingroup import_export
 *
 * @param type The requested type.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(DataType type) {
  switch (type) {
    case DataType::CALIBRATION_STATE:
      return "CalibrationState";
    case DataType::CRASH_LOG:
      return "CrashLog";
    case DataType::FILTER_STATE:
      return "FilterState";
    case DataType::USER_CONFIG:
      return "UserConfig";
    case DataType::INVALID:
      return "Invalid";
  }

  return "Unrecognized";
}

/**
 * @brief @ref DataType stream operator.
 * @ingroup import_export
 */
inline p1_ostream& operator<<(p1_ostream& stream, DataType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief Import data from the host to the device (@ref
 *        MessageType::IMPORT_DATA, version 1.0).
 * @ingroup import_export
 *
 * This message must be followed by @ref data_length_bytes bytes containing
 * the data to be imported:
 *
 * ```
 * {MessageHeader, ImportDataMessage, Payload[data_length_bytes]}
 * ```
 *
 * # Expected Response
 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request succeeded.
 */
struct P1_ALIGNAS(4) ImportDataMessage {
  static constexpr MessageType MESSAGE_TYPE = MessageType::IMPORT_DATA;
  static constexpr uint8_t MESSAGE_VERSION = 0;
  /**
   * The type of data being imported.
   */
  DataType data_type = DataType::INVALID;
  /**
   * The location of the data to update (active, saved, etc.). For data that
   * doesn't have separate active and saved copies, this parameter is ignored.
   */
  ConfigurationSource source = ConfigurationSource::ACTIVE;
  uint8_t reserved1[2] = {0};
  /** @brief Version of data contents. */
  DataVersion data_version;
  uint8_t reserved2[4] = {0};
  /** @brief Number of bytes to update. */
  uint32_t data_length_bytes = 0;
};

/**
 * @brief Export data from the device (@ref
 *        MessageType::EXPORT_DATA, version 1.0).
 * @ingroup import_export
 *
 * # Expected Response
 * The device will respond with a @ref PlatformStorageDataMessage.
 */
struct P1_ALIGNAS(4) ExportDataMessage {
  static constexpr MessageType MESSAGE_TYPE = MessageType::EXPORT_DATA;
  static constexpr uint8_t MESSAGE_VERSION = 0;
  /**
   * The type of data to be exported.
   */
  DataType data_type = DataType::INVALID;
  /**
   * The source to copy this data from. If the data_type doesn't separate active
   * and saved data, this will be ignored.
   */
  ConfigurationSource source = ConfigurationSource::ACTIVE;
  uint8_t reserved[2] = {0};
};

/**
 * @brief Message for reporting platform storage data (@ref
 *        MessageType::PLATFORM_STORAGE_DATA, version 1.0).
 * @ingroup import_export
 *
 * This message will be followed by @ref data_length_bytes bytes containing
 * the data storage contents:
 *
 * ```
 * {MessageHeader, PlatformStorageDataMessage, Payload[data_length_bytes]}
 * ```
 *
 * See also @ref ExportDataMessage.
 *
 * Changes:
 * - Version 1: Added `data_validity` field.
 * - Version 2: Changed data_validity to a @ref Response enum and added
 *              @ref source field.
 * - Version 3: Added @ref flags field.
 */
struct P1_ALIGNAS(4) PlatformStorageDataMessage {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::PLATFORM_STORAGE_DATA;
  static constexpr uint8_t MESSAGE_VERSION = 3;

  /** @ref DataType::USER_CONFIG flag field is not set. */
  static constexpr uint8_t FLAG_USER_CONFIG_PLATFORM_NOT_SPECIFIED = 0;
  /** @ref DataType::USER_CONFIG flag for POSIX platforms. */
  static constexpr uint8_t FLAG_USER_CONFIG_PLATFORM_POSIX = 1;
  /** @ref DataType::USER_CONFIG flag for embedded platforms. */
  static constexpr uint8_t FLAG_USER_CONFIG_PLATFORM_EMBEDDED = 2;
  /** @ref DataType::USER_CONFIG flag for embedded SSR platforms. */
  static constexpr uint8_t FLAG_USER_CONFIG_PLATFORM_EMBEDDED_SSR = 3;
  /** @ref DataType::USER_CONFIG flag for the SSR client library. */
  static constexpr uint8_t FLAG_USER_CONFIG_SSR_CLIENT = 254;

  /**
   * The type of data contained in this message.
   */
  DataType data_type = DataType::INVALID;
  /**
   * The status of the specified data type on the device.
   */
  Response response = Response::OK;
  /**
   * The source this data was copied from. If the @ref data_type doesn't
   * separate active and saved data, this will be set to @ref
   * ConfigurationSource::ACTIVE.
   */
  ConfigurationSource source = ConfigurationSource::ACTIVE;
  /**
   * @ref DataType specific flags.
   *
   * Currently, only defined for @ref DataType::USER_CONFIG contents. This value
   * can optionally set to one of the `FLAG_USER_CONFIG_PLATFORM_*` values to
   * indicate which type of platform the UserConfig is valid for. This value
   * can be left at `0` for backwards compatibility or to indicate the platform
   * type is unknown.
   */
  uint8_t flags = 0;
  /** Version of data contents. */
  DataVersion data_version;
  /** Number of bytes in data contents. */
  uint32_t data_length_bytes = 0;
};

/**************************************************************************/ /**
 * @defgroup io_interfaces Input/Output Interface And Message Rate Control
 * @brief Messages for controlling device output (e.g., define TCP server
 *        parameters, configure message output rates).
 * @ingroup config_and_ctrl_messages
 ******************************************************************************/

/**
 * @brief An identifier for the contents of a output interface configuration
 *        submessage.
 * @ingroup io_interfaces
 *
 * See also @ref InterfaceConfigSubmessage.
 */
enum class InterfaceConfigType : uint8_t {
  INVALID = 0,

  /**
   * Enable/disable output of diagnostic data on this interface.
   *
   * Valid for:
   * - All @ref TransportType
   *
   * @note
   * Enabling this setting will override the message rate/off settings for some
   * FusionEngine messages.
   *
   * Payload format: `bool`
   */
  OUTPUT_DIAGNOSTICS_MESSAGES = 1,

  /**
   * Configure the serial baud rate (in bits/second).
   *
   * Valid for:
   * - @ref TransportType::SERIAL
   *
   * Payload format: `uint32_t`
   */
  BAUD_RATE = 2,

  /**
   * Configure the remote network IP address or hostname for a client to connect
   * to.
   *
   * Valid for:
   * - @ref TransportType::TCP
   * - @ref TransportType::UDP
   *
   * Payload format: `char[64]` containing a NULL terminated string.
   */
  REMOTE_ADDRESS = 3,

  /**
   * Configure the network port.
   *
   * Valid for:
   * - @ref TransportType::TCP
   * - @ref TransportType::UDP
   * - @ref TransportType::WEBSOCKET
   *
   * Payload format: `uint16_t`
   */
  PORT = 4,

  /**
   * Enable/disable the interface.
   *
   * Valid for all @ref TransportType values.
   *
   * Payload format: `bool`
   */
  ENABLED = 5,

  /**
   * Set the interface direction (client/server).
   *
   * Valid for:
   * - @ref TransportType::TCP
   * - @ref TransportType::WEBSOCKET
   * - @ref TransportType::UNIX
   *
   * Payload format: @ref TransportDirection
   */
  DIRECTION = 6,

  /**
   * Set the UNIX domain socket type (streaming/datagram/sequenced).
   *
   * Valid for:
   * - @ref TransportType::UNIX
   *
   * Payload format: @ref SocketType
   */
  SOCKET_TYPE = 7,

  /**
   * Configure the path to a local file or UNIX domain socket.
   *
   * Valid for:
   * - @ref TransportType::FILE
   * - @ref TransportType::UNIX
   *
   * Payload format: `char[64]` containing a NULL terminated string.
   */
  FILE_PATH = 8,
};

/**
 * @brief Get a human-friendly string name for the specified @ref ConfigType.
 * @ingroup io_interfaces
 *
 * @param type The desired configuration parameter type.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(InterfaceConfigType type) {
  switch (type) {
    case InterfaceConfigType::INVALID:
      return "Invalid";

    case InterfaceConfigType::OUTPUT_DIAGNOSTICS_MESSAGES:
      return "Diagnostic Messages Enabled";

    case InterfaceConfigType::BAUD_RATE:
      return "Serial Baud Rate";

    case InterfaceConfigType::REMOTE_ADDRESS:
      return "Remote Network Address";

    case InterfaceConfigType::PORT:
      return "Network Port";

    case InterfaceConfigType::ENABLED:
      return "Interface Enabled";

    case InterfaceConfigType::DIRECTION:
      return "Transport Direction";

    case InterfaceConfigType::SOCKET_TYPE:
      return "Socket Type";

    case InterfaceConfigType::FILE_PATH:
      return "File Path";
  }

  return "Unrecognized Configuration";
}

/**
 * @brief @ref InterfaceConfigType stream operator.
 * @ingroup io_interfaces
 */
inline p1_ostream& operator<<(p1_ostream& stream, InterfaceConfigType type) {
  stream << to_string(type) << " (" << (int)type << ")";
  return stream;
}

/**
 * @brief The framing protocol of a message.
 * @ingroup io_interfaces
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
 * @ingroup io_interfaces
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(ProtocolType val) {
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
  }

  return "Unrecognized";
}

/**
 * @brief @ref ProtocolType stream operator.
 * @ingroup io_interfaces
 */
inline p1_ostream& operator<<(p1_ostream& stream, ProtocolType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief Type of I/O interface transport.
 * @ingroup io_interfaces
 */
enum class TransportType : uint8_t {
  INVALID = 0,
  /** A serial data interface (e.g. an RS232 connection). */
  SERIAL = 1,
  /** A interface that writes to a file. */
  FILE = 2,
  // RESERVED = 3,
  /**
   * A TCP client or server.
   *
   * A TCP client will connect to a specified TCP server address and port. A TCP
   * server will listen for incoming client connections, and may communicate
   * with multiple clients at a time. Responses to commands will be sent only to
   * the the issuing client. All other configured output messages will be sent
   * to all clients.
   *
   * See also @ref TransportDirection.
   */
  TCP = 4,
  /**
   * A UDP client or server.
   *
   * UDP connections are stateless, unlike TCP. A UDP interface will listen for
   * incoming messages on a specified port. It may optionally be configured to
   * sent output to a specific hostname or IP address, including broadcast or
   * multicast addresses. If an address is not specified, the interface will not
   * send any output automatically, but it will respond to incoming commands,
   * sending responses back to the remote client's address and port.
   */
  UDP = 5,
  // RESERVED = 6,
  /**
   * A WebSocket client or server.
   *
   * WebSocket connections are similar to TCP connections, and use TCP as their
   * underlying transport, but use the WebSocket protocol to send and receive
   * data.
   *
   * See also @ref TransportDirection.
   */
  WEBSOCKET = 7,
  /**
   * A UNIX domain socket client or server.
   *
   * UNIX domain socket connections may be configured as either client that
   * connects to an existing server, or a server that listens for one or more
   * incoming client connections. UNIX domain sockets may operate in one of
   * three possible modes:
   * - A connection-oriented streaming mode where packet boundaries are not
   *   preserved (similar to TCP)
   * - Datagram mode where packet boundaries are preserved but connections
   *   between the client and server are not maintained, and the interface sends
   *   output to an optional configured file (similar to UDP)
   * - Sequenced packet mode, which is connection-oriented (like TCP) but also
   *   preserves message boundaries (like UDP) and guarantees in-order delivery
   *
   * For a UNIX domain socket, you must specify:
   * - The @ref TransportDirection (client or server)
   * - The @ref SocketType (streaming, datagram, or sequenced)
   * - The path to a socket file to connect to (client) or create (server)
   */
  UNIX = 8,
  /**
   * Set/get the configuration for the interface on which the command was
   * received.
   */
  CURRENT = 254,
  /** Set/get the configuration for the all I/O interfaces. */
  ALL = 255,
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        TransportType.
 * @ingroup io_interfaces
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(TransportType val) {
  switch (val) {
    case TransportType::INVALID:
      return "Invalid";
    case TransportType::SERIAL:
      return "Serial";
    case TransportType::FILE:
      return "File";
    case TransportType::TCP:
      return "TCP";
    case TransportType::UDP:
      return "UDP";
    case TransportType::WEBSOCKET:
      return "WebSocket";
    case TransportType::UNIX:
      return "UNIX";
    case TransportType::CURRENT:
      return "Current";
    case TransportType::ALL:
      return "All";
  }

  return "Unrecognized";
}

/**
 * @brief @ref TransportType stream operator.
 * @ingroup io_interfaces
 */
inline p1_ostream& operator<<(p1_ostream& stream, TransportType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief The direction (client/server) for an individual interface.
 * @ingroup io_interfaces
 */
enum class TransportDirection : uint8_t {
  INVALID = 0,
  /** A server listening for one or more incoming remote connections. */
  SERVER = 1,
  /** A client connecting to a specified remote server. */
  CLIENT = 2,
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        TransportDirection.
 * @ingroup io_interfaces
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(TransportDirection val) {
  switch (val) {
    case TransportDirection::INVALID:
      return "INVALID";
    case TransportDirection::SERVER:
      return "SERVER";
    case TransportDirection::CLIENT:
      return "CLIENT";
  }

  return "Unrecognized";
}

/**
 * @brief @ref TransportDirection stream operator.
 * @ingroup io_interfaces
 */
inline p1_ostream& operator<<(p1_ostream& stream, TransportDirection val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief The socket type specifying how data is transmitted for UNIX domain
 *        sockets.
 * @ingroup io_interfaces
 */
enum class SocketType : uint8_t {
  INVALID = 0,
  /**
   * Operate in connection-oriented streaming mode and do not preserve message
   * boundaries (similar to TCP).
   */
  STREAM = 1,
  /**
   * Operate in datagram mode, preserving message boundaries but not maintaining
   * client connections (similar to UDP).
   */
  DATAGRAM = 2,
  /**
   * Operate in sequenced packet mode, which is both connection-oriented and
   * preserves message boundaries.
   */
  SEQPACKET = 3,
};

/**
 * @brief Get a human-friendly string name for the specified @ref SocketType.
 * @ingroup io_interfaces
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(SocketType val) {
  switch (val) {
    case SocketType::INVALID:
      return "INVALID";
    case SocketType::STREAM:
      return "STREAM";
    case SocketType::DATAGRAM:
      return "DATAGRAM";
    case SocketType::SEQPACKET:
      return "SEQPACKET";
  }

  return "Unrecognized";
}

/**
 * @brief @ref SocketType stream operator.
 * @ingroup io_interfaces
 */
inline p1_ostream& operator<<(p1_ostream& stream, SocketType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief Identifier for an I/O interface.
 * @ingroup io_interfaces
 *
 * For example, serial port 1 or TCP server 2.
 *
 * @note
 * On most devices, serial ports (UARTs) use 1-based numbering: the first serial
 * port is typically index 1 (UART1).
 */
struct P1_ALIGNAS(4) InterfaceID {
  /** The interface's transport type. **/
  TransportType type = TransportType::INVALID;
  /** An identifier for the instance of this transport. */
  uint8_t index = 0;
  uint8_t reserved[2] = {0};

  P1_CONSTEXPR_FUNC InterfaceID() = default;

  P1_CONSTEXPR_FUNC explicit InterfaceID(TransportType type, uint8_t index = 0)
      : type(type), index(index) {}

  P1_CONSTEXPR_FUNC bool operator==(const InterfaceID& other) const {
    return type == other.type && index == other.index;
  }

  P1_CONSTEXPR_FUNC bool operator!=(const InterfaceID& other) const {
    return !(*this == other);
  }

  P1_CONSTEXPR_FUNC bool operator<(const InterfaceID& other) const {
    if (type == other.type) {
      return index < other.index;
    } else {
      return type < other.type;
    }
  }

  P1_CONSTEXPR_FUNC bool operator>(const InterfaceID& other) const {
    return other < *this;
  }

  P1_CONSTEXPR_FUNC bool operator>=(const InterfaceID& other) const {
    return !(*this < other);
  }

  P1_CONSTEXPR_FUNC bool operator<=(const InterfaceID& other) const {
    return !(*this > other);
  }
};

/**
 * @brief @ref InterfaceID stream operator.
 * @ingroup io_interfaces
 */
inline p1_ostream& operator<<(p1_ostream& stream, const InterfaceID& val) {
  stream << "[type=" << val.type << ", index=" << (int)val.index << "]";
  return stream;
}

/**
 * @brief Integer ID for NMEA messages.
 * @ingroup io_interfaces
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
  ZDA = 7,
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
  PQTMVERNO_SUB = 1203,
  PQTMVER_SUB = 1204,
  PQTMTXT = 1205,
  /** @} */
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        NmeaMessageType.
 * @ingroup io_interfaces
 *
 * @param value The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(NmeaMessageType value) {
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
    case NmeaMessageType::ZDA:
      return "ZDA";
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
    case NmeaMessageType::PQTMVERNO_SUB:
      return "PQTMVERNO_SUB";
    case NmeaMessageType::PQTMVER_SUB:
      return "PQTMVER_SUB";
    case NmeaMessageType::PQTMTXT:
      return "PQTMTXT";
  }

  return "Unrecognized";
}

/**
 * @brief @ref NmeaMessageType stream operator.
 * @ingroup io_interfaces
 */
inline p1_ostream& operator<<(p1_ostream& stream, NmeaMessageType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief The output rate for a message type on an interface.
 * @ingroup io_interfaces
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
   * Output this message every 10 milliseconds. Not supported for all messages
   * or platforms.
   */
  INTERVAL_10_MS = 2,
  /**
   * Output this message every 20 milliseconds. Not supported for all messages
   * or platforms.
   */
  INTERVAL_20_MS = 3,
  /**
   * Output this message every 40 milliseconds. Not supported for all messages
   * or platforms.
   */
  INTERVAL_40_MS = 4,
  /**
   * Output this message every 50 milliseconds. Not supported for all messages
   * or platforms.
   */
  INTERVAL_50_MS = 5,
  /**
   * Output this message every 100 milliseconds. Not supported for all messages
   * or platforms.
   */
  INTERVAL_100_MS = 6,
  /**
   * Output this message every 200 milliseconds. Not supported for all messages
   * or platforms.
   */
  INTERVAL_200_MS = 7,
  /**
   * Output this message every 500 milliseconds. Not supported for all messages
   * or platforms.
   */
  INTERVAL_500_MS = 8,
  /**
   * Output this message every second. Not supported for all messages or
   * platforms.
   */
  INTERVAL_1_S = 9,
  /**
   * Output this message every 2 seconds. Not supported for all messages or
   * platforms.
   */
  INTERVAL_2_S = 10,
  /**
   * Output this message every 5 seconds. Not supported for all messages or
   * platforms.
   */
  INTERVAL_5_S = 11,
  /**
   * Output this message every 10 seconds. Not supported for all messages or
   * platforms.
   */
  INTERVAL_10_S = 12,
  /**
   * Output this message every 30 seconds. Not supported for all messages or
   * platforms.
   */
  INTERVAL_30_S = 13,
  /**
   * Output this message every 60 seconds. Not supported for all messages or
   * platforms.
   */
  INTERVAL_60_S = 14,
  /**
   * Restore this message's rate back to its default value.
   */
  DEFAULT = 255
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        MessageRate.
 * @ingroup io_interfaces
 *
 * @param value The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(MessageRate value) {
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
    case MessageRate::INTERVAL_30_S:
      return "INTERVAL_30_S";
    case MessageRate::INTERVAL_60_S:
      return "INTERVAL_60_S";
    case MessageRate::DEFAULT:
      return "DEFAULT";
  }

  return "Unrecognized";
}

/**
 * @brief @ref MessageRate stream operator.
 * @ingroup io_interfaces
 */
inline p1_ostream& operator<<(p1_ostream& stream, MessageRate val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief I/O interface parameter configuration submessage (used when sending
 *        a @ref SetConfigMessage or @ref GetConfigMessage for @ref
 *        ConfigType::INTERFACE_CONFIG).
 * @ingroup io_interfaces
 *
 * In @ref SetConfigMessage, @ref GetConfigMessage, and @ref
 * ConfigResponseMessage, this struct can be used to access settings
 * associated with a a particular I/O interface. For example, to set the
 * baudrate for serial port 1:
 *
 * ```
 * {
 *   SetConfigMessage(
 *     config_type=INTERFACE_CONFIG),
 *   InterfaceConfigSubmessage(
 *     interface=InterfaceID(TransportType::SERIAL, 1),
 *     subtype=BAUD_RATE),
 *   uint32_t 115200
 * }
 * ```
 *
 * This message must be followed by the parameter value to be used:
 *
 * ```
 * {MessageHeader, SetConfigMessage, InterfaceConfigSubmessage, Parameter}
 * ```
 *
 * See @ref InterfaceConfigType for a complete list of parameters and their
 * data formats.
 */
struct P1_ALIGNAS(4) InterfaceConfigSubmessage {
  /**
   * The ID of the interface to be configured or queried.
   *
   * @note
   * TransportType::ALL is not supported.
   */
  InterfaceID interface = InterfaceID(TransportType::CURRENT, 0);

  /**
   * The interface setting to get or set.
   */
  InterfaceConfigType subtype = InterfaceConfigType::INVALID;

  uint8_t reserved[3] = {0};
};

/**
 * @brief Set the output rate for the requested message types (@ref
 *        MessageType::SET_MESSAGE_RATE, version 1.0).
 * @ingroup io_interfaces
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
 * @note
 * When specifying @ref ProtocolType::ALL, message ID @ref ALL_MESSAGES_ID must
 * also be specified. Further, the rate must be set to either
 * @ref MessageRate::OFF or @ref MessageRate::DEFAULT.
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
 * @subsection set_rate_change_nmea Change UART1 Output Rate To 1 Hz:
 *
 * To change the rate of all NMEA message types to 1 Hz on UART1, specify the
 * following:
 * - Interface transport type: @ref TransportType::SERIAL
 * - Interface index: 1
 * - Protocol: @ref ProtocolType::NMEA
 * - Message ID: @ref ALL_MESSAGES_ID
 * - Rate: @ref MessageRate::INTERVAL_1_S
 *
 * @note
 * Note that this will not affect any message types that are not rate controlled
 * (e.g., @ref MessageType::EVENT_NOTIFICATION).
 *
 * @subsection set_rate_off_all Change The Uart1 Output Rates For All Messages To Be Off:
 *
 * To change the rate of all messages to their max rate on UART1, specify the
 * following:
 * - Interface transport type: @ref TransportType::SERIAL
 * - Interface index: 1
 * - Protocol: @ref ProtocolType::ALL
 * - flags: @ref FLAG_INCLUDE_DISABLED_MESSAGES
 * - Message ID: @ref ALL_MESSAGES_ID
 * - Rate: @ref MessageRate::OFF
 *
 * @note
 * This will disable every message.
 *
 * @subsection set_and_save_rate_off_all Change And Save The UART1 Output Rates For All Messages To Be Off:
 *
 * To change the rate of all messages to their max rate on UART1, specify the
 * following:
 * - Interface transport type: @ref TransportType::SERIAL
 * - Interface index: 1
 * - Protocol: @ref ProtocolType::ALL
 * - flags: 0x03 (@ref FLAG_INCLUDE_DISABLED_MESSAGES | @ref FLAG_APPLY_AND_SAVE)
 * - Message ID: @ref ALL_MESSAGES_ID
 * - Rate: @ref MessageRate::OFF
 *
 * @note
 * Both of the bit flags are set for this message. This will cause the
 * configuration to be saved to non-volatile memory.
 *
 * # Expected Response
 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request succeeded.
 */
struct P1_ALIGNAS(4) SetMessageRate : public MessagePayload {
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
  InterfaceID output_interface{TransportType::CURRENT};

  /**
   * The message protocol being configured. If @ref ProtocolType::ALL, set rates
   * on all supported protocols.
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
 * @ingroup io_interfaces
 *
 * Multiple message rates can be requested with a single command if wild cards
 * are used for the protocol, or message ID.
 *
 * # Expected Response
 * The device will respond with a @ref MessageRateResponse containing the
 * requested values or an error @ref Response value if the request did not
 * succeed.
 */
struct P1_ALIGNAS(4) GetMessageRate : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::GET_MESSAGE_RATE;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * The output interface to be queried.
   *
   * @ref TransportType::ALL is not supported. To query for multiple transports,
   * send separate requests.
   */
  InterfaceID output_interface{TransportType::CURRENT};

  /**
   * The desired message protocol. If @ref ProtocolType::ALL, return the current
   * settings for all supported protocols.
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
 * @brief A list of transport interfaces supported by the device (@ref
 *        MessageType::SUPPORTED_IO_INTERFACES, version 1.0).
 * @ingroup io_interfaces
 */
struct P1_ALIGNAS(4) SupportedIOInterfacesMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::SUPPORTED_IO_INTERFACES;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The number of interfaces reported by this message. */
  uint8_t num_interfaces = 0;

  uint8_t reserved1[7] = {0};

  /** This is followed `num_interfaces` @ref InterfaceID elements. */
  // InterfaceID interfaces[num_interfaces]
};

/**
 * @brief An element of a @ref MessageRateResponse message.
 * @ingroup io_interfaces
 */
struct P1_ALIGNAS(4) MessageRateResponseEntry {
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
 * @ingroup io_interfaces
 *
 * This message will be followed by @ref num_rates @ref MessageRateResponseEntry
 * elements:
 *
 * ```
 * {MessageHeader, MessageRateResponse, MessageRateResponseEntry[num_rates]}
 * ```
 */
struct P1_ALIGNAS(4) MessageRateResponse : public MessagePayload {
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
};

/**************************************************************************/ /**
 * @defgroup gnss_corrections_control GNSS Corrections Control
 * @brief Messages for enabling/disabling GNSS corrections sources.
 * @ingroup config_and_ctrl_messages
 ******************************************************************************/

/**
 * @brief L-band demodulator configuration parameters.
 * @ingroup gnss_corrections_control
 */
struct P1_ALIGNAS(4) LBandConfig {
  /**
   * The center frequency of the L-band beam (Hz).
   */
  double center_frequency_hz = 1555492500.0;

  /**
   * The size of the signal acquisition search space (in Hz) around the center
   * frequency.
   *
   * For example, a value of 6000 will search +/- 3 kHz around the center
   * frequency.
   */
  float search_window_hz = 2000.0;

  /**
   * If `true`, only output data frames with the configured service ID.
   * Otherwise, output all decoded frames.
   */
  bool filter_data_by_service_id = true;

  /** Enable/disable the descrambler. */
  bool use_descrambler = true;

  /** Service ID of the provider. */
  uint16_t pmp_service_id = 0x5555;

  /** Unique word of the provider. */
  uint64_t pmp_unique_word = 0xE15AE893E15AE893ull;

  /** Data rate of the provider (bps). */
  uint16_t pmp_data_rate_bps = 4800;

  /** The initialization value for the descrambling vector. */
  uint16_t descrambler_init = 0x6969;
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
