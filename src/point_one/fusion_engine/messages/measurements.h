/**************************************************************************/ /**
 * @brief Sensor measurement messages.
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

/**
 * @defgroup measurement_messages Sensor Measurement Message Definitions
 * @brief Measurement data from available sensors.
 * @ingroup messages
 *
 * See also @ref messages.
 */

/**
 * @brief The source of received sensor measurements, if known.
 * @ingroup measurement_messages
 */
enum class SensorDataSource : uint8_t {
  /** Data source not known. */
  UNKNOWN = 0,
  /**
   * Sensor data captured internal to the device (embedded IMU, GNSS receiver,
   * etc.).
   */
  INTERNAL = 1,
  /**
   * Sensor data generated via hardware voltage signal (wheel tick, external
   * event, etc.).
   */
  HARDWARE_IO = 2,
  /** Sensor data captured from a vehicle CAN bus. */
  CAN = 3,
  /** Sensor data provided over a serial connection. */
  SERIAL = 4,
  /** Sensor data provided over a network connection. */
  NETWORK = 5,
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        SensorDataSource.
 * @ingroup measurement_messages
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(SensorDataSource val) {
  switch (val) {
    case SensorDataSource::UNKNOWN:
      return "Unknown";
    case SensorDataSource::INTERNAL:
      return "Internal";
    case SensorDataSource::HARDWARE_IO:
      return "Hardware I/O";
    case SensorDataSource::CAN:
      return "CAN";
    case SensorDataSource::SERIAL:
      return "Serial";
    case SensorDataSource::NETWORK:
      return "Network";
    default:
      return "Unrecognized";
  }
}

/**
 * @brief @ref SensorDataSource stream operator.
 * @ingroup measurement_messages
 */
inline p1_ostream& operator<<(p1_ostream& stream, SensorDataSource val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief The source of a @ref point_one::fusion_engine::messages::Timestamp
 *        used to represent the time of applicability of an incoming sensor
 *        measurement.
 * @ingroup measurement_messages
 */
enum class SystemTimeSource : uint8_t {
  /** Timestamp not valid. */
  INVALID = 0,
  /** Message timestamped in P1 time. */
  P1_TIME = 1,
  /**
   * Message timestamped in system time, generated when received by the device.
   */
  TIMESTAMPED_ON_RECEPTION = 2,
  /**
   * Message timestamp was generated from a monotonic clock of an external
   * system.
   */
  SENDER_SYSTEM_TIME = 3,
  /**
   * Message timestamped in GPS time, referenced to 1980/1/6.
   */
  GPS_TIME = 4,
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        SystemTimeSource.
 * @ingroup measurement_messages
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(SystemTimeSource val) {
  switch (val) {
    case SystemTimeSource::INVALID:
      return "Invalid";
    case SystemTimeSource::P1_TIME:
      return "P1 Time";
    case SystemTimeSource::TIMESTAMPED_ON_RECEPTION:
      return "Timestamped on Reception";
    case SystemTimeSource::SENDER_SYSTEM_TIME:
      return "Sender System Time";
    case SystemTimeSource::GPS_TIME:
      return "GPS Time";
    default:
      return "Unrecognized";
  }
}

/**
 * @brief @ref SystemTimeSource stream operator.
 * @ingroup measurement_messages
 */
inline p1_ostream& operator<<(p1_ostream& stream, SystemTimeSource val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief The time of applicability and additional information for an incoming
 *        sensor measurement.
 * @ingroup measurement_messages
 *
 * By convention this will be the first member of any message containing
 * input measurements by the host to the device, as well as raw measurement
 * outputs from the device.
 *
 * The @ref measurement_time field stores time of applicability/reception for
 * the measurement data, expressed in one of the available source time bases
 * (see @ref SystemTimeSource). The timestamp will be converted to P1 time
 * automatically by FusionEngine using an internal model of P1 vs. the specified
 * source time.
 *
 * @section meas_details_on_arrival Timestamp On Arrival
 *
 * On most platforms, incoming sensor measurements are timestamped automatically
 * by FusionEngine when they arrive. To request timestamp on arrival, set @ref
 * measurement_time_source to either @ref
 * SystemTimeSource::TIMESTAMPED_ON_RECEPTION or @ref SystemTimeSource::INVALID.
 *
 * @section meas_details_external_time Timestamp Externally
 *
 * On some platforms, incoming sensor measurements may be timestamped
 * externally by the host prior to arrival, either in GPS time (@ref
 * SystemTimeSource::GPS_TIME), or using a monotonic clock controlled by the
 * host system (@ref SystemTimeSource::SENDER_SYSTEM_TIME). For those platforms,
 * the @ref measurement_time field should be specified in the incoming message.
 *
 * @note
 * Use of an external monotonic clock requires additional coordination with the
 * target FusionEngine device.
 *
 * @section meas_details_p1_time Timestamp With External P1 Time
 *
 * Measurements may only be timestamped externally using P1 time (@ref
 * SystemTimeSource::P1_TIME) if the external system supports remote
 * synchronization of the P1 time clock model. This is intended for internal
 * use only.
 */
struct P1_ALIGNAS(4) MeasurementDetails {
  /**
   * The measurement time of applicability, if available, in a user-specified
   * time base. The source of this value is specified in @ref
   * measurement_time_source. The timestamp will be converted to P1 time
   * internally by the device before use.
   */
  Timestamp measurement_time;

  /**
   * The source for @ref measurement_time.
   */
  SystemTimeSource measurement_time_source = SystemTimeSource::INVALID;

  /**
   * The source of the incoming data, if known.
   */
  SensorDataSource data_source = SensorDataSource::UNKNOWN;

  uint8_t reserved[2] = {0};

  /**
   * The P1 time corresponding with the measurement time of applicability, if
   * available.
   *
   * For inputs to the device, this field will be populated automatically by the
   * device on arrival based on @ref measurement_time. Any existing value will
   * be overwritten. To specify a known P1 time, specify the value in @ref
   * measurement_time and set @ref measurement_time_source to @ref
   * SystemTimeSource::P1_TIME.
   *
   * For outputs from the device, this field will always be populated with the
   * P1 time corresponding with the measurement.
   */
  Timestamp p1_time;
};

////////////////////////////////////////////////////////////////////////////////
// IMU Measurements
////////////////////////////////////////////////////////////////////////////////

/**
 * @brief IMU sensor measurement output with calibration and corrections applied
 *        (@ref MessageType::IMU_OUTPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message is an output from the device containing IMU acceleration and
 * rotation rate measurements. The measurements been corrected for biases and
 * scale factors, and have been rotated into the vehicle body frame from the
 * original IMU orientation, including calibrated mounting error estimates.
 *
 * See also @ref RawIMUOutput.
 */
struct P1_ALIGNAS(4) IMUOutput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::IMU_OUTPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The time of the measurement, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /**
   * Corrected vehicle x/y/z acceleration (in meters/second^2), resolved in the
   * body frame.
   */
  double accel_mps2[3] = {NAN, NAN, NAN};

  /**
   * Corrected vehicle x/y/z acceleration standard deviation (in
   * meters/second^2), resolved in the body frame.
   */
  double accel_std_mps2[3] = {NAN, NAN, NAN};

  /**
   * Corrected vehicle x/y/z rate of rotation (in radians/second), resolved in
   * the body frame.
   */
  double gyro_rps[3] = {NAN, NAN, NAN};

  /**
   * Corrected vehicle x/y/z rate of rotation standard deviation (in
   * radians/second), resolved in the body frame.
   */
  double gyro_std_rps[3] = {NAN, NAN, NAN};
};

/**
 * @brief Raw (uncorrected) IMU sensor measurement output (@ref
          MessageType::RAW_IMU_OUTPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message is an output from the device containing raw IMU acceleration and
 * rotation rate measurements. These measurements come directly from the sensor,
 * and do not have any corrections or calibration applied.
 *
 * See also @ref IMUOutput.
 */
struct P1_ALIGNAS(4) RawIMUOutput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::RAW_IMU_OUTPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  uint8_t reserved[6] = {0};

  /**
   * The IMU temperature (in deg Celcius * 2^-7). Set to 0x7FFF if invalid.
   */
  int16_t temperature = INT16_MAX;

  /**
   * Measured x/y/z acceleration (in meters/second^2 * 2^-16), resolved in the
   * sensor measurement frame. Set to 0x7FFFFFFF if invalid.
   */
  int32_t accel[3] = {INT32_MAX, INT32_MAX, INT32_MAX};

  /**
   * Measured x/y/z rate of rotation (in radians/second * 2^-20), resolved in
   * the sensor measurement frame. Set to 0x7FFFFFFF if invalid.
   */
  int32_t gyro[3] = {INT32_MAX, INT32_MAX, INT32_MAX};
};

////////////////////////////////////////////////////////////////////////////////
// Different Wheel Speed Measurements
////////////////////////////////////////////////////////////////////////////////

/**
 * @brief The current transmission gear used by the vehicle.
 * @ingroup measurement_messages
 */
enum class GearType : uint8_t {
  /**
   * The transmission gear is not known, or does not map to a supported
   * GearType.
   */
  UNKNOWN = 0,
  FORWARD = 1, ///< The vehicle is in a forward gear.
  REVERSE = 2, ///< The vehicle is in reverse.
  PARK = 3, ///< The vehicle is parked.
  NEUTRAL = 4, ///< The vehicle is in neutral.
};

/**
 * @brief Get a human-friendly string name for the specified @ref GearType.
 * @ingroup measurement_messages
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(GearType val) {
  switch (val) {
    case GearType::UNKNOWN:
      return "Unknown";
    case GearType::FORWARD:
      return "Forward";
    case GearType::REVERSE:
      return "Reverse";
    case GearType::PARK:
      return "Park";
    case GearType::NEUTRAL:
      return "Neutral";
    default:
      return "Unrecognized";
  }
}

/**
 * @brief @ref GearType stream operator.
 * @ingroup measurement_messages
 */
inline p1_ostream& operator<<(p1_ostream& stream, GearType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief Differential wheel speed measurement input (@ref
 *        MessageType::WHEEL_SPEED_INPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message is an input to the device, used to convey the speed of each
 * individual wheel on the vehicle. The number and type of wheels expected
 * varies by vehicle. For single along-track speed measurements, see @ref
 * VehicleSpeedInput.
 *
 * To use wheel speed data, you must first configure the device by issuing a
 * @ref SetConfigMessage message containing a @ref WheelConfig payload
 * describing the vehicle sensor configuration (speed data signed/unsigned,
 * etc.).
 *
 * Some platforms may have an additional voltage signal used to indicate
 * direction of motion, have direction or gear information available from a
 * vehicle CAN bus, etc. If direction/gear information is available, it may be
 * provided in the @ref gear field.
 *
 * To send wheel tick counts from software, use @ref WheelTickInput instead.
 *
 * See also @ref WheelSpeedOutput for measurement output.
 */
struct P1_ALIGNAS(4) WheelSpeedInput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::WHEEL_SPEED_INPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Set this flag if the measured wheel speeds are signed (positive forward,
   * negative reverse). Otherwise, if the values are assumed to be unsigned
   * (positive in both directions).
   */
  static constexpr uint8_t FLAG_SIGNED = 0x1;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /**
   * The front left wheel speed (in m/s * 2^-10). Set to 0x7FFFFFFF if not
   * available.
   */
  int32_t front_left_speed = INT32_MAX;

  /**
   * The front right wheel speed (in m/s * 2^-10). Set to 0x7FFFFFFF if not
   * available.
   */
  int32_t front_right_speed = INT32_MAX;

  /**
   * The rear left wheel speed (in m/s * 2^-10). Set to 0x7FFFFFFF if not
   * available.
   */
  int32_t rear_left_speed = INT32_MAX;

  /**
   * The rear right wheel speed (in m/s * 2^-10). Set to 0x7FFFFFFF if not
   * available.
   */
  int32_t rear_right_speed = INT32_MAX;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   *
   * Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle
   * direction information is available externally.
   */
  GearType gear = GearType::UNKNOWN;

  /** A bitmask of flags associated with the measurement data. */
  uint8_t flags = 0x0;

  uint8_t reserved[2] = {0};
};

/**
 * @brief Differential wheel speed measurement output with calibration and
 *        corrections applied (@ref MessageType::WHEEL_SPEED_OUTPUT, version
          1.0).
 * @ingroup measurement_messages
 *
 * This message is an output from the device that contains the speed of each
 * individual wheel on the vehicle, after applying any estimated corrections for
 * wheel scale factor, sign, etc.
 *
 * Wheel odometry data may be received via a software input from a host machine,
 * a vehicle CAN bus, or a hardware voltage signal (wheel ticks). The @ref
 * data_source field will indicate which type of data source provided the
 * measurements to the device.
 *
 * When odometry is provided using hardware wheel ticks, the speeds in this
 * message reflect the tick rate over a fixed time interval. For high accuracy
 * applications, it may be necessary to integrate tick counts over longer
 * intervals of time.
 *
 * See also @ref WheelSpeedInput and @ref RawWheelSpeedOutput.
 */
struct P1_ALIGNAS(4) WheelSpeedOutput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::WHEEL_SPEED_OUTPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Set this flag if the measured wheel speeds are signed (positive forward,
   * negative reverse). Otherwise, if the values are assumed to be unsigned
   * (positive in both directions).
   */
  static constexpr uint8_t FLAG_SIGNED = 0x1;

  /** The time of the measurement, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /**
   * The source of the incoming data, if known.
   */
  SensorDataSource data_source = SensorDataSource::UNKNOWN;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   */
  GearType gear = GearType::UNKNOWN;

  /** A bitmask of flags associated with the measurement data. */
  uint8_t flags = 0x0;

  uint8_t reserved = 0;

  /** The front left wheel speed (in m/s). Set to NAN if not available. */
  float front_left_speed_mps = NAN;

  /** The front right wheel speed (in m/s). Set to NAN if not available. */
  float front_right_speed_mps = NAN;

  /** The rear left wheel speed (in m/s). Set to NAN if not available. */
  float rear_left_speed_mps = NAN;

  /** The rear right wheel speed (in m/s). Set to NAN if not available. */
  float rear_right_speed_mps = NAN;
};

/**
 * @brief Raw (uncorrected) dfferential wheel speed measurement output (@ref
 *        MessageType::RAW_WHEEL_SPEED_OUTPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message is an output from the device that contains the speed of each
 * individual wheel on the vehicle. These measurements come directly from the
 * sensor, and do not have any corrections or calibration applied.
 *
 * See @ref WheelSpeedOutput for more details. See also @ref WheelSpeedInput.
 */
struct P1_ALIGNAS(4) RawWheelSpeedOutput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::RAW_WHEEL_SPEED_OUTPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Set this flag if the measured wheel speeds are signed (positive forward,
   * negative reverse). Otherwise, if the values are assumed to be unsigned
   * (positive in both directions).
   */
  static constexpr uint8_t FLAG_SIGNED = 0x1;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /**
   * The front left wheel speed (in m/s * 2^-10). Set to 0x7FFFFFFF if not
   * available.
   */
  int32_t front_left_speed = INT32_MAX;

  /**
   * The front right wheel speed (in m/s * 2^-10). Set to 0x7FFFFFFF if not
   * available.
   */
  int32_t front_right_speed = INT32_MAX;

  /**
   * The rear left wheel speed (in m/s * 2^-10). Set to 0x7FFFFFFF if not
   * available.
   */
  int32_t rear_left_speed = INT32_MAX;

  /**
   * The rear right wheel speed (in m/s * 2^-10). Set to 0x7FFFFFFF if not
   * available.
   */
  int32_t rear_right_speed = INT32_MAX;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   *
   * Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle
   * direction information is available externally.
   */
  GearType gear = GearType::UNKNOWN;

  /** A bitmask of flags associated with the measurement data. */
  uint8_t flags = 0x0;

  uint8_t reserved[2] = {0};
};

////////////////////////////////////////////////////////////////////////////////
// Vehicle Speed Measurements
////////////////////////////////////////////////////////////////////////////////

/**
 * @brief Vehicle body speed measurement input (@ref
 *        MessageType::VEHICLE_SPEED_INPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message is an input to the device, used to convey the along-track speed
 * of the vehicle (forward/backward). For differential speed measurements for
 * multiple wheels, see @ref WheelSpeedInput.
 *
 * To use vehicle speed data, you must first configure the device by issuing a
 * @ref SetConfigMessage message containing a @ref WheelConfig payload
 * describing the vehicle sensor configuration (speed data signed/unsigned,
 * etc.).
 *
 * Some platforms may have an additional voltage signal used to indicate
 * direction of motion, have direction or gear information available from a
 * vehicle CAN bus, etc. If direction/gear information is available, it may be
 * provided in the @ref gear field.
 *
 * To send wheel tick counts from software, use @ref VehicleTickInput instead.
 *
 * See also @ref VehicleSpeedOutput for measurement output.
 */
struct P1_ALIGNAS(4) VehicleSpeedInput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::VEHICLE_SPEED_INPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Set this flag if the measured wheel speeds are signed (positive forward,
   * negative reverse). Otherwise, if the values are assumed to be unsigned
   * (positive in both directions).
   */
  static constexpr uint8_t FLAG_SIGNED = 0x1;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /**
   * The current vehicle speed estimate (in m/s * 2^-10). Set to 0x7FFFFFFF if
   * not available.
   */
  int32_t vehicle_speed = INT32_MAX;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   *
   * Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle
   * direction information is available externally.
   */
  GearType gear = GearType::UNKNOWN;

  /** A bitmask of flags associated with the measurement data. */
  uint8_t flags = 0x0;

  uint8_t reserved[2] = {0};
};

/**
 * @brief Vehicle body speed measurement output with calibration and corrections
 *        applied (@ref MessageType::VEHICLE_SPEED_OUTPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message is an output from the device that contains the along-track speed
 * of the vehicle (forward/backward), after applying any estimated corrections
 * for scale factor, etc.
 *
 * Odometry data may be received via a software input from a host machine, a
 * vehicle CAN bus, or a hardware voltage signal (wheel ticks). The @ref
 * data_source field will indicate which type of data source provided the
 * measurements to the device.
 *
 * When odometry is provided using hardware wheel ticks, the speed in this
 * message reflects the tick rate over a fixed time interval. For high accuracy
 * applications, it may be necessary to integrate tick counts over longer
 * intervals of time.
 *
 * See also @ref VehicleSpeedInput and @ref RawVehicleSpeedOutput.
 */
struct P1_ALIGNAS(4) VehicleSpeedOutput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::VEHICLE_SPEED_OUTPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Set this flag if the measured wheel speeds are signed (positive forward,
   * negative reverse). Otherwise, if the values are assumed to be unsigned
   * (positive in both directions).
   */
  static constexpr uint8_t FLAG_SIGNED = 0x1;

  /** The time of the measurement, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /**
   * The source of the incoming data, if known.
   */
  SensorDataSource data_source = SensorDataSource::UNKNOWN;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   *
   * Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle
   * direction information is available externally.
   */
  GearType gear = GearType::UNKNOWN;

  /** A bitmask of flags associated with the measurement data. */
  uint8_t flags = 0x0;

  uint8_t reserved = 0;

  /** The current vehicle speed estimate (in m/s). */
  float vehicle_speed_mps = NAN;
};

/**
 * @brief Raw (uncorrected) vehicle body speed measurement output (@ref
 *        MessageType::RAW_VEHICLE_SPEED_OUTPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message is an output from the device that contains the along-track speed
 * of the vehicle (forward/backward). These measurements come directly from the
 * sensor, and do not have any corrections or calibration applied.
 *
 * See @ref VehicleSpeedOutput for more details. See also @ref
 * VehicleSpeedInput.
 */
struct P1_ALIGNAS(4) RawVehicleSpeedOutput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::RAW_VEHICLE_SPEED_OUTPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Set this flag if the measured wheel speeds are signed (positive forward,
   * negative reverse). Otherwise, if the values are assumed to be unsigned
   * (positive in both directions).
   */
  static constexpr uint8_t FLAG_SIGNED = 0x1;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /**
   * The current vehicle speed estimate (in m/s * 2^-10). Set to 0x7FFFFFFF if
   * not available.
   */
  int32_t vehicle_speed = INT32_MAX;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   *
   * Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle
   * direction information is available externally.
   */
  GearType gear = GearType::UNKNOWN;

  /** A bitmask of flags associated with the measurement data. */
  uint8_t flags = 0x0;

  uint8_t reserved[2] = {0};
};

////////////////////////////////////////////////////////////////////////////////
// Wheel Tick Measurements
////////////////////////////////////////////////////////////////////////////////

/**
 * @brief Differential wheel encoder tick input (@ref
 *        MessageType::WHEEL_TICK_INPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message is an input to the device, used to convey the wheel encoder tick
 * counts for one or more wheels, received through software (e.g., vehicle CAN
 * bus) or captured in hardware from external voltage pulses. The number and
 * type of wheels expected, and the interpretation of the tick count values,
 * varies by vehicle.
 *
 * To use wheel encoder data, you must first configure the device by issuing a
 * @ref SetConfigMessage message containing a @ref WheelConfig payload
 * describing the vehicle sensor configuration (tick counts signed/unsigned,
 * etc.).
 *
 * Some platforms may have an additional voltage signal used to indicate
 * direction of motion, have direction or gear information available from a
 * vehicle CAN bus, etc. If direction/gear information is available, it may be
 * provided in the @ref gear field.
 *
 * See also @ref RawWheelTickOutput for measurement output.
 */
struct P1_ALIGNAS(4) WheelTickInput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::WHEEL_TICK_INPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /**
   * The front left wheel ticks. The interpretation of these ticks is
   * defined outside of this message.
   */
  uint32_t front_left_wheel_ticks = 0;

  /**
   * The front right wheel ticks. The interpretation of these ticks is
   * defined outside of this message.
   */
  uint32_t front_right_wheel_ticks = 0;

  /**
   * The rear left wheel ticks. The interpretation of these ticks is
   * defined outside of this message.
   */
  uint32_t rear_left_wheel_ticks = 0;

  /**
   * The rear right wheel ticks. The interpretation of these ticks is
   * defined outside of this message.
   */
  uint32_t rear_right_wheel_ticks = 0;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   *
   * Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle
   * direction information is available externally.
   */
  GearType gear = GearType::UNKNOWN;

  uint8_t reserved[3] = {0};
};

/**
 * @brief Raw (uncorrected) dfferential wheel encoder tick output (@ref
 *        MessageType::RAW_WHEEL_TICK_OUTPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message is an output from the device that contains wheel encoder tick
 * counts for each individual wheel on the vehicle. These measurements come
 * directly from the sensor, and do not have any corrections or calibration
 * applied.
 *
 * See also @ref WheelTickInput.
 */
struct P1_ALIGNAS(4) RawWheelTickOutput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::RAW_WHEEL_TICK_OUTPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /**
   * The front left wheel ticks. The interpretation of these ticks is
   * defined outside of this message.
   */
  uint32_t front_left_wheel_ticks = 0;

  /**
   * The front right wheel ticks. The interpretation of these ticks is
   * defined outside of this message.
   */
  uint32_t front_right_wheel_ticks = 0;

  /**
   * The rear left wheel ticks. The interpretation of these ticks is
   * defined outside of this message.
   */
  uint32_t rear_left_wheel_ticks = 0;

  /**
   * The rear right wheel ticks. The interpretation of these ticks is
   * defined outside of this message.
   */
  uint32_t rear_right_wheel_ticks = 0;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   *
   * Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle
   * direction information is available externally.
   */
  GearType gear = GearType::UNKNOWN;

  uint8_t reserved[3] = {0};
};

////////////////////////////////////////////////////////////////////////////////
// Vehicle Tick Measurements
////////////////////////////////////////////////////////////////////////////////

/**
 * @brief Single wheel encoder tick input, representing vehicle body speed
 *        (@ref MessageType::VEHICLE_TICK_INPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message is an input to the device, used to convey a single wheel encoder
 * tick count representing the along-track speed of the vehicle
 * (forward/backward). Tick data may be received through software (e.g., vehicle
 * CAN bus) or captured in hardware from external voltage pulses.The
 * interpretation of the tick count values varies by vehicle.
 *
 * To use wheel encoder data, you must first configure the device by issuing a
 * @ref SetConfigMessage message containing either a @ref WheelConfig payload
 * (software source) or @ref HardwareTickConfig payload (hardware voltage)
 * describing the vehicle sensor configuration (tick counts signed/unsigned,
 * etc.).
 *
 * Some platforms may have an additional voltage signal used to indicate
 * direction of motion, have direction or gear information available from a
 * vehicle CAN bus, etc. If direction/gear information is available, it may be
 * provided in the @ref gear field.
 *
 * See also @ref RawVehicleTickOutput for measurement output.
 */
struct P1_ALIGNAS(4) VehicleTickInput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::VEHICLE_TICK_INPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /**
   * The current encoder tick count. The interpretation of these ticks is
   * defined outside of this message.
   */
  uint32_t tick_count = 0;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   *
   * Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle
   * direction information is available externally.
   */
  GearType gear = GearType::UNKNOWN;

  uint8_t reserved[3] = {0};
};

/**
 * @brief Raw (uncorrected) single wheel encoder tick output (@ref
 *        MessageType::RAW_VEHICLE_TICK_OUTPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message is an output from the device that contains a wheel encoder tick
 * count representing the along-track speed of the vehicle (forward/backward).
 * This value comes directly from the sensor, and does not have any corrections
 * or calibration applied.
 *
 * See also @ref VehicleTickInput.
 */
struct P1_ALIGNAS(4) RawVehicleTickOutput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::RAW_VEHICLE_TICK_OUTPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /**
   * The current encoder tick count. The interpretation of these ticks is
   * defined outside of this message.
   */
  uint32_t tick_count = 0;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   *
   * Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle
   * direction information is available externally.
   */
  GearType gear = GearType::UNKNOWN;

  uint8_t reserved[3] = {0};
};

////////////////////////////////////////////////////////////////////////////////
// Deprecated Speed Measurement Definitions
////////////////////////////////////////////////////////////////////////////////

/**
 * @brief (Deprecated) Differential wheel speed measurement (@ref
 *        MessageType::DEPRECATED_WHEEL_SPEED_MEASUREMENT, version 1.0).
 * @ingroup measurement_messages
 *
 * @deprecated
 * This message is deprecated as of version 1.18.0 and may be removed in the
 * future. It should not used for new development. See @ref WheelSpeedInput and
 * @ref WheelSpeedOutput instead.
 */
struct P1_ALIGNAS(4) DeprecatedWheelSpeedMeasurement : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::DEPRECATED_WHEEL_SPEED_MEASUREMENT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /** The front left wheel speed (in m/s). Set to NAN if not available. */
  float front_left_speed_mps = NAN;

  /** The front right wheel speed (in m/s). Set to NAN if not available. */
  float front_right_speed_mps = NAN;

  /** The rear left wheel speed (in m/s). Set to NAN if not available. */
  float rear_left_speed_mps = NAN;

  /** The rear right wheel speed (in m/s). Set to NAN if not available. */
  float rear_right_speed_mps = NAN;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   *
   * Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle
   * direction information is available externally.
   */
  GearType gear = GearType::UNKNOWN;

  /**
   * `true` if the wheel speeds are signed (positive forward, negative reverse),
   * or `false` if the values are unsigned (positive in both directions).
   */
  bool is_signed = true;

  uint8_t reserved[2] = {0};
};

/**
 * @brief (Deprecated) Vehicle body speed measurement (@ref
 *        MessageType::DEPRECATED_VEHICLE_SPEED_MEASUREMENT, version 1.0).
 * @ingroup measurement_messages
 *
 * @deprecated
 * This message is deprecated as of version 1.18.0 and may be removed in the
 * future. It should not used for new development. See @ref VehicleSpeedInput
 * and @ref VehicleSpeedOutput instead.
 */
struct P1_ALIGNAS(4) DeprecatedVehicleSpeedMeasurement : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::DEPRECATED_VEHICLE_SPEED_MEASUREMENT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /** The current vehicle speed estimate (in m/s). */
  float vehicle_speed_mps = NAN;

  /**
   * The transmission gear currently in use, or direction of motion, if
   * available.
   *
   * Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle
   * direction information is available externally.
   */
  GearType gear = GearType::UNKNOWN;

  /**
   * `true` if the wheel speeds are signed (positive forward, negative reverse),
   * or `false` if the values are unsigned (positive in both directions).
   */
  bool is_signed = true;

  uint8_t reserved[2] = {0};
};

////////////////////////////////////////////////////////////////////////////////
// Heading Sensor Definitions
////////////////////////////////////////////////////////////////////////////////

/**
 * @brief Raw (uncorrected) heading sensor measurement output (@ref
 *        MessageType::RAW_HEADING_OUTPUT, version 1.0).
 * @ingroup measurement_messages
 *
 * This message contains raw heading sensor measurements that have not been
 * corrected for mounting angle biases.
 *
 * See also @ref HeadingOutput.
 */
struct P1_ALIGNAS(4) RawHeadingOutput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::RAW_HEADING_OUTPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /**
   * Set to @ref SolutionType::RTKFixed when heading is available, or @ref
   * SolutionType::Invalid otherwise.
   */
  SolutionType solution_type = SolutionType::Invalid;

  uint8_t reserved[3] = {0};

  /** A bitmask of flags associated with the solution. */
  uint32_t flags = 0;

  /**
   * The position of the secondary GNSS antenna relative to the primary antenna
   * (in meters), resolved with respect to the local ENU tangent plane: east,
   * north, up.
   *
   * Position is measured with respect to the primary antenna as follows:
   * @f[
   * \Delta r_{ENU} = C^{ENU}_{ECEF} (r_{Secondary, ECEF} - r_{Primary, ECEF})
   * @f]
   */
  float relative_position_enu_m[3] = {NAN, NAN, NAN};

  /**
   * The position standard deviation (in meters), resolved with respect to the
   * local ENU tangent plane: east, north, up.
   */
  float position_std_enu_m[3] = {NAN, NAN, NAN};

  /**
   * The measured heading angle (in degrees) with respect to true north,
   * pointing from the primary antenna to the secondary antenna.
   *
   * @note
   * Reported in the range [0, 360).
   */
  float heading_true_north_deg = NAN;

  /**
   * The estimated distance between primary and secondary antennas (in meters).
   */
  float baseline_distance_m = NAN;
};

/**
 * @brief Heading sensor measurement output (@ref MessageType::HEADING_OUTPUT,
 *        version 1.0).
 * @ingroup measurement_messages
 *
 * The HeadingOutput message behaves similarly to the RawHeadingOutput,
 * however, if no biases have been set AND the message is enabled,
 * then the message will not be published.
 * 
 * See also @ref RawHeadingOutput and @ref SolutionType::Invalid.
 */
struct P1_ALIGNAS(4) HeadingOutput : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::HEADING_OUTPUT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * Measurement timestamp and additional information, if available. See @ref
   * MeasurementDetails for details.
   */
  MeasurementDetails details;

  /**
   * Set to @ref SolutionType::RTKFixed when heading is available, or @ref
   * SolutionType::Invalid otherwise.
   */
  SolutionType solution_type = SolutionType::Invalid;

  uint8_t reserved[3] = {0};

  /** A bitmask of flags associated with the solution. */
  uint32_t flags = 0;

  /**
   * The measured YPR vector (in degrees), resolved in the ENU frame.
   *
   * YPR is defined as an intrinsic Euler-321 rotation, i.e., yaw, pitch, then
   * roll.
   *
   * @note
   * This field contains the measured attitude information (@ref
   * RawHeadingOutput) from a secondary heading device after applying @ref
   * ConfigType::HEADING_BIAS configuration settings for yaw (horizontal) and
   * pitch (vertical) offsets between the primary and secondary GNSS antennas.
   * If either bias value is not specified, the corresponding measurement values
   * will be set to `NAN`.
   */
  float ypr_deg[3] = {NAN, NAN, NAN};

  /**
   * The corrected heading angle (in degrees) with respect to true north,
   * pointing from the primary antenna to the secondary antenna.
   *
   * @note
   * Reported in the range [0, 360).
   */
  float heading_true_north_deg = NAN;
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
