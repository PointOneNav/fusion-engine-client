/**************************************************************************/ /**
 * @brief Sensor measurement messages.
 * @file
 ******************************************************************************/

#pragma once

#include "point_one/fusion_engine/messages/defs.h"

namespace point_one {
namespace fusion_engine {
namespace messages {

// Enforce 4-byte alignment and packing of all data structures and values so
// that floating point values are aligned on platforms that require it.
#pragma pack(push, 4)

/**
 * @brief IMU sensor measurement data (@ref MessageType::IMU_MEASUREMENT),
 *        version 1.0.
 * @ingroup messages
 *
 * @note
 * The data contained in this message has been corrected for accelerometer and
 * gyro biases and scale factors, and has been rotated into the vehicle body
 * frame from the original IMU orientation.
 */
struct IMUMeasurement {
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
