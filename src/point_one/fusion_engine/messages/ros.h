/**************************************************************************/ /**
 * @brief ROS support messages.
 * @file
 ******************************************************************************/

#pragma once

namespace point_one {
namespace fusion_engine {
namespace messages {
namespace ros {

// Enforce 4-byte alignment and packing of all data structures and values so
// that floating point values are aligned on platforms that require it.
#pragma pack(push, 4)

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
 * @brief [ROS GPSFix](http://docs.ros.org/api/gps_common/html/msg/GPSFix.html)
 *        message (MessageType::ROS_GPS_FIX).
 * @ingroup ros_messages
 */
struct GPSFixMessage {
  /**
   * @defgroup ros_covariance_type ROS Covariance Type Values
   * @{
   */
  static const uint8_t COVARIANCE_TYPE_UNKNOWN = 0;
  static const uint8_t COVARIANCE_TYPE_APPROXIMATED = 0;
  static const uint8_t COVARIANCE_TYPE_DIAGONAL_KNOWN = 0;
  static const uint8_t COVARIANCE_TYPE_KNOWN = 0;
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
   * @note
   * Specified as intrinsic Euler-231 angles (pitch, roll, dip). Note that the
   * ROS Euler angle order differs from the one used for @ref
   * PoseMessage::ypr_deg.
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

#pragma pack(pop)

} // namespace ros
} // namespace messages
} // namespace fusion_engine
} // namespace point_one
