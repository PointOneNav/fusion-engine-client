/**************************************************************************/ /**
 * @brief ROS support messages.
 * @file
 ******************************************************************************/

#pragma once

#include "point_one/fusion_engine/messages/defs.h"

namespace point_one {
namespace fusion_engine {
namespace messages {
namespace ros {

// Enforce 4-byte alignment and packing of all data structures and values.
// Floating point values are aligned on platforms that require it. This is done
// with a combination of setting struct attributes, and manual alignment
// within the definitions. See the "Message Packing" section of the README.
#pragma pack(push, 1)

/**
 * @defgroup ros_messages ROS Support Message Definitions
 * @brief Messages designed for direct translation to ROS.
 * @ingroup messages
 *
 * The messages defined in this file are intended to be translated into their
 * corresponding ROS message structures where ROS integration is needed.
 *
 * @note
 * The messages defined here are _not_ guaranteed to be byte-compatible with ROS
 * messages. They are designed to have the same or similar content, which can be
 * easily copied into a ROS message.
 *
 * See also @ref messages.
 */

/**
 * @brief ROS `Pose` message (MessageType::ROS_POSE, version 1.0).
 * @ingroup ros_messages
 *
 * See http://docs.ros.org/api/geometry_msgs/html/msg/Pose.html.
 */
struct alignas(4) PoseMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::ROS_POSE;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /**
   * The relative change in ENU position since the time of the first @ref
   * PoseMessage, resolved in the local ENU frame at the time of the first @ref
   * PoseMessage.
   *
   * @warning
   * The [ROS Pose message API documentation](
   * http://docs.ros.org/api/geometry_msgs/html/msg/Pose.html)
   * does not currently define the origin or reference frame of its position
   * field. Using the Novatel SPAN driver as a reference
   * (http://docs.ros.org/api/novatel_span_driver/html/publisher_8py_source.html),
   * we have chosen to report a relative ENU position. Absolute world position
   * is available in the @ref GPSFixMessage and @ref messages::PoseMessage
   * classes.
   */
  double position_rel_m[3] = {NAN, NAN, NAN};

  /**
   * The platform body orientation with respect to the local ENU frame,
   * represented as a quaternion with the scalar component last (x, y, z, w).
   */
  double orientation[4] = {NAN, NAN, NAN, NAN};
};

/**
 * @brief ROS `GPSFix` message (MessageType::ROS_GPS_FIX, version 1.0).
 * @ingroup ros_messages
 *
 * See http://docs.ros.org/api/gps_common/html/msg/GPSFix.html.
 */
struct alignas(4) GPSFixMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::ROS_GPS_FIX;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * @defgroup ros_covariance_type ROS Covariance Type Values
   * @{
   */
  static const uint8_t COVARIANCE_TYPE_UNKNOWN = 0;
  static const uint8_t COVARIANCE_TYPE_APPROXIMATED = 1;
  static const uint8_t COVARIANCE_TYPE_DIAGONAL_KNOWN = 2;
  static const uint8_t COVARIANCE_TYPE_KNOWN = 3;
  /** @} */

  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /**
   * @name WGS-84 Geodetic Position
   * @{
   */

  /**
   * The WGS-84 geodetic latitude (in degrees).
   */
  double latitude_deg = NAN;

  /**
   * The WGS-84 geodetic longitude (in degrees).
   */
  double longitude_deg = NAN;

  /**
   * The WGS-84 altitude above the ellipsoid (in meters).
   */
  double altitude_m = NAN;

  /** @} */

  /**
   * @name Velocity
   * @{
   */

  /**
   * The vehicle direction from north (in degrees).
   */
  double track_deg = NAN;

  /**
   * The vehicle ground speed (in meters/second).
   */
  double speed_mps = NAN;

  /**
   * The vehicle vertical speed (in meters/second).
   */
  double climb_mps = NAN;

  /** @} */

  /**
   * @name Vehicle Orientation
   *
   * @warning
   * The pitch/roll/dip field definition listed in the
   * [ROS GPSFix message definition](http://docs.ros.org/api/gps_common/html/msg/GPSFix.html)
   * uses non-standard terminology, and the order of the Euler angles is not
   * explicitly defined. We do not currently support this field. See @ref
   * PoseMessage::orientation or @ref messages::PoseMessage::ypr_deg instead.
   *
   * @{
   */

  /**
   * The platform pitch angle (in degrees).
   */
  double pitch_deg = NAN;

  /**
   * The platform roll angle (in degrees).
   */
  double roll_deg = NAN;

  /**
   * The platform dip angle (in degrees).
   */
  double dip_deg = NAN;

  /** @} */

  /** The GPS time of the message (in seconds), referenced to 1980/1/6. */
  double gps_time = NAN;

  /**
   * @name Dilution Of Precision
   * @{
   */

  double gdop = NAN; ///< Geometric (position + time) DOP.
  double pdop = NAN; ///< Positional (3D) DOP.
  double hdop = NAN; ///< Horizontal DOP.
  double vdop = NAN; ///< Vertical DOP.
  double tdop = NAN; ///< Time DOP.

  /** @} */

  /**
   * @name Measurement Uncertainty (95% Confidence)
   * @{
   */

  /** Spherical position uncertainty (in meters) [epe] */
  double err_3d_m = NAN;

  /** Horizontal position uncertainty (in meters) [eph] */
  double err_horiz_m = NAN;

  /** Vertical position uncertainty (in meters) [epv] */
  double err_vert_m = NAN;

  /** Track uncertainty (in degrees) [epd] */
  double err_track_deg = NAN;

  /** Ground speed uncertainty (in meters/second) [eps] */
  double err_speed_mps = NAN;

  /** Vertical speed uncertainty (in meters/second) [epc] */
  double err_climb_mps = NAN;

  /** Time uncertainty (in seconds) [ept] */
  double err_time_sec = NAN;

  /** Pitch uncertainty (in degrees) */
  double err_pitch_deg = NAN;

  /** Roll uncertainty (in degrees) */
  double err_roll_deg = NAN;

  /** Dip uncertainty (in degrees) */
  double err_dip_deg = NAN;

  /** @} */

  /**
   * @name Position Covariance
   * @{
   */

  /**
   * The 3x3 position covariance matrix (in m^2), resolved in the local ENU
   * frame. Values are stored in row-major order.
   */
  double position_covariance_m2[9] = {NAN};

  /**
   * The method in which @ref position_covariance_m2 was populated. See @ref
   * ros_covariance_type.
   */
  uint8_t position_covariance_type = COVARIANCE_TYPE_UNKNOWN;

  /** @} */

  uint8_t reserved[3] = {0};
};

/**
 * @brief ROS `Imu` message (MessageType::ROS_IMU, version 1.0).
 * @ingroup ros_messages
 *
 * If any of the data elements are not available (e.g., IMU doesn't produce an
 * orientation estimate), they will be set to 0 and their associated covariance
 * matrices will be set to -1.
 *
 * See http://docs.ros.org/api/sensor_msgs/html/msg/Imu.html.
 *
 * @note
 * The data contained in this message has been corrected for accelerometer and
 * gyro biases and scale factors, and has been rotated into the vehicle body
 * frame from the original IMU orientation using the FusionEngine sensor
 * calibration data.
 */
struct alignas(4) IMUMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::ROS_IMU;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /**
   * The platform body orientation with respect to the local ENU frame,
   * represented as a quaternion with the scalar component last (x, y, z, w).
   */
  double orientation[4] = {NAN, NAN, NAN, NAN};

  /**
   * Orientation covariance matrix. Set to -1 if not available.
   */
  double orientation_covariance[9] = {-1};

  /**
   * Vehicle x/y/z rate of rotation (in radians/second), resolved in the body
   * frame.
   */
  double angular_velocity_rps[3] = {NAN, NAN, NAN};

  /**
   * Vehicle rate of rotation covariance matrix. Set to -1 if not available.
   */
  double angular_velocity_covariance[9] = {-1};

  /**
   * Vehicle x/y/z linear acceleration (in meters/second^2), resolved in the
   * body frame.
   */
  double acceleration_mps2[3] = {NAN, NAN, NAN};

  /**
   * Vehicle x/y/z acceleration covariance matrix. Set to -1 if not available.
   */
  double acceleration_covariance[9] = {-1};
};

#pragma pack(pop)

} // namespace ros
} // namespace messages
} // namespace fusion_engine
} // namespace point_one
