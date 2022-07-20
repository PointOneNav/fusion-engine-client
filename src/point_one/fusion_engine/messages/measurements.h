/**************************************************************************/ /**
 * @brief Sensor measurement messages.
 * @file
 ******************************************************************************/

#pragma once

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
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(SystemTimeSource val) {
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
 */
inline std::ostream& operator<<(std::ostream& stream, SystemTimeSource val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief The time of applicability for an incoming sensor measurement.
 *
 * By convention this will be the first member of any measurement definition
 * intended to be externally sent by the user to the device.
 *
 * The @ref measurement_time field stores time of applicability/reception for
 * the measurement data, expressed in one of the available source time bases
 * (see @ref SystemTimeSource). The timestamp will be converted to P1 time
 * automatically by FusionEngine using an internal model of P1 vs source time.
 * The converted value will be assigned to @ref p1_time for usage and logging
 * purposes.
 *
 * On most platforms, incoming sensor measurements are timestamped automatically
 * by FusionEngine when they arrive. To request timestamp on arrival, set @ref
 * measurement_time to invalid, and set the @ref measurement_time_source to
 * @ref SystemTimeSource::INVALID.
 *
 * On some platforms, incoming sensor measurements may be timestamped
 * externally by the user prior to arrival, either in GPS time (@ref
 * SystemTimeSource::GPS_TIME), or using a monotonic clock controlled by the
 * user system (@ref SystemTimeSource::SENDER_SYSTEM_TIME).
 *
 * @note
 * Use of an external monotonic clock requires additional coordination with the
 * target FusionEngine device.
 *
 * Measurements may only be timestamped externally using P1 time (@ref
 * SystemTimeSource::P1_TIME) if the external system supports remote
 * synchronization of the P1 time clock model.
 */
struct alignas(4) MeasurementTimestamps {
  /**
   * The measurement time of applicability, if available, in a user-specified
   * time base. The source of this value is specified in @ref
   * measurement_time_source. The timestamp will be converted to P1 time
   * automatically before use.
   */
  Timestamp measurement_time;

  /**
   * The source for @ref measurement_time.
   */
  SystemTimeSource measurement_time_source = SystemTimeSource::INVALID;

  uint8_t reserved[3] = {0};

  /**
   * The P1 time corresponding with the measurement time of applicability, if
   * available.
   *
   * @note
   * Do not modify this field when sending measurements to FusionEngine. It will
   * be populated automatically on arrival. Any previously specified value will
   * be overwritten. To specify a known P1 time, specify the value in @ref
   * measurement_time and set @ref measurement_time_source to @ref
   * SystemTimeSource::P1_TIME.
   */
  Timestamp p1_time;
};

/**
 * @brief IMU sensor measurement data (@ref MessageType::IMU_MEASUREMENT,
 *        version 1.0).
 * @ingroup measurement_messages
 *
 * @note
 * The data contained in this message has been corrected for accelerometer and
 * gyro biases and scale factors, and has been rotated into the vehicle body
 * frame from the original IMU orientation.
 */
struct alignas(4) IMUMeasurement : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::IMU_MEASUREMENT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The time of the message, in P1 time (beginning at power-on). */
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
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
inline const char* to_string(GearType val) {
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
 */
inline std::ostream& operator<<(std::ostream& stream, GearType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief Differential wheel speed measurement (@ref
 *        MessageType::WHEEL_SPEED_MEASUREMENT, version 1.0).
 * @ingroup measurement_messages
 */
struct alignas(4) WheelSpeedMeasurement : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::WHEEL_SPEED_MEASUREMENT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** Measurement timestamps, if available. See @ref measurement_messages. */
  MeasurementTimestamps timestamps;

  /** The front left wheel speed (in m/s). Set to NAN if not available. */
  float front_left_speed_mps = NAN;

  /** The front right wheel speed (in m/s). Set to NAN if not available. */
  float front_right_speed_mps = NAN;

  /** The rear left wheel speed (in m/s). Set to NAN if not available. */
  float rear_left_speed_mps = NAN;

  /** The rear right wheel speed (in m/s). Set to NAN if not available. */
  float rear_right_speed_mps = NAN;

  /** The transmission gear currently in use (if available). */
  GearType gear = GearType::UNKNOWN;

  uint8_t reserved[3] = {0};
};

/**
 * @brief Vehicle body speed measurement (@ref
 *        MessageType::VEHICLE_SPEED_MEASUREMENT, version 1.0).
 * @ingroup measurement_messages
 */
struct alignas(4) VehicleSpeedMeasurement : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::VEHICLE_SPEED_MEASUREMENT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** Measurement timestamps, if available. See @ref measurement_messages. */
  MeasurementTimestamps timestamps;

  /** The current vehicle speed estimate (in m/s). */
  float vehicle_speed_mps = NAN;

  /** The transmission gear currently in use (if available). */
  GearType gear = GearType::UNKNOWN;

  uint8_t reserved[3] = {0};
};

/**
 * @brief Differential wheel encoder tick measurement (@ref
 *        MessageType::WHEEL_TICK_MEASUREMENT, version 1.0).
 * @ingroup measurement_messages
 */
struct alignas(4) WheelTickMeasurement : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::WHEEL_TICK_MEASUREMENT;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** Measurement timestamps, if available. See @ref measurement_messages. */
  MeasurementTimestamps timestamps;

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

  /** The transmission gear currently in use (if available). */
  GearType gear = GearType::UNKNOWN;

  uint8_t reserved[3] = {0};
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
