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
 * @brief The source of a @ref TimeStamp used to represent the time of
 *        applicability of an incoming sensor measurement.
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
      return "P1Time";
    case SystemTimeSource::TIMESTAMPED_ON_RECEPTION:
      return "Timestamped on Reception";
    case SystemTimeSource::SENDER_SYSTEM_TIME:
      return "Sender System Time";
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
 * intended to be externally sent by the user to the device. On most platforms,
 * incoming sensor measurements are timestamped by the device when they arrive.
 * On some platforms, incoming sensor measurements may be timestamped externally
 * by the user prior to arrival.
 */
struct alignas(4) MeasurementTimestamps {
  /**
   * The time of the message, if available. The source of this value is
   * specified in @ref measurement_time_source.
   */
  Timestamp measurement_time;

  /**
   * The source for @ref measurement_time.
   */
  SystemTimeSource measurement_time_source = SystemTimeSource::INVALID;

  uint8_t reserved[3] = {0};

  /** The GPS time of the message, if available, referenced to 1980/1/6. */
  Timestamp gps_time;
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

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
