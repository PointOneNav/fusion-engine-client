/**************************************************************************/ /**
 * @brief Platform position/attitude solution messages.
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
 * @brief Platform pose solution: position, velocity, attitude (@ref
 *        MessageType::POSE), version 1.0.
 * @ingroup messages
 *
 * @note
 * All data is timestamped using the Point One Time, which is a monotonic
 * timestamp referenced to the start of the device. Corresponding messages (@ref
 * GNSSInfoMessage, @ref GNSSSatelliteMessage, etc.) may be associated using
 * their @ref p1_time values.
 */
struct PoseMessage_1_0 {
  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /** The GPS time of the message, if available, referenced to 1980/1/6. */
  Timestamp gps_time;

  /** The type of this position solution. */
  SolutionType solution_type;

  uint8_t reserved = 0;

  /**
   * The geoid undulation at at the current location (i.e., the difference
   * between the WGS-84 ellipsoid and the geoid).
   *
   * Height above the ellipsoid can be converted to a corresponding height above
   * the geoid (orthometric height or height above mean sea level (MSL)) as
   * follows:
   *
   * @f[
   * h_{orthometric} = h_{ellipsoid} - undulation
   * @f]
   *
   * Stored in units of 0.01 meters: `undulation_m = undulation_cm * 0.01`. Set
   * to `-32768` if invalid.
   *
   * Added in @ref PoseMessage version 1.1.
   */
  int16_t undulation_cm = -INT16_MIN;

  /**
   * The geodetic latitude, longitude, and altitude (in degrees/meters),
   * expressed using the WGS-84 reference ellipsoid.
   *
   * @section p1_fe_pose_datum Datum/Epoch Considerations
   * When comparing two positions, it is very important to make sure they are
   * compared using the same geodetic datum, defined at the same time (epoch).
   * Failing to do so can cause very large unexpected differences since the
   * ground moves in various directions over time due to motion of tectonic
   * plates.
   *
   * For example, the coordinates for a point on the ground in San Francisco
   * expressed in the ITRF14 datum may differ by multiple meters from the
   * coordinates for the same point expressed the NAD83 datum. Similarly, the
   * coordinates for that location expressed in the ITRF14 2017.0 epoch
   * (January 1, 2017) may differ by 12 cm or more when expressed using the
   * ITRF14 2021.0 epoch (January 1, 2021).
   *
   * The datum and epoch to which the position reported in this message is
   * aligned depends on the current @ref solution_type.
   * - @ref SolutionType::AutonomousGPS / @ref SolutionType::DGPS /
   *   @ref SolutionType::PPP - Standalone solutions (i.e., no differential
   *   corrections) are aligned to the WGS-84 datum as broadcast live by GPS
   *   (aligns closely with the ITRF08/14 datums).
   * - @ref SolutionType::RTKFloat / @ref SolutionType::RTKFixed - When
   *   differential corrections are applied, the reference datum and epoch are
   *   defined by the corrections provider. Point One's Polaris Corrections
   *   Service produces corrections using the ITRF14 datum. See
   *   https://pointonenav.com/polaris for more details.
   * - @ref SolutionType::Integrate - When the INS is dead reckoning in the
   *   absence of GNSS, vision, or other measurements anchored in absolute world
   *   coordinates, the position solution is defined in the same datum/epoch
   *   specified by the previous solution type (e.g., WGS-84 if previously
   *   standalone GNSS, i.e., @ref SolutionType::AutonomousGPS).
   */
  double lla_deg[3] = {NAN, NAN, NAN};

  /**
   * The position standard deviation (in meters), resolved with respect to the
   * local ENU tangent plane: east, north, up.
   */
  float position_std_enu_m[3] = {NAN, NAN, NAN};

  /**
   * The platform attitude (in degrees), if known, described as intrinsic
   * Euler-321 angles (yaw, pitch, roll) with respect to the local ENU tangent
   * plane. Set to `NAN` if attitude is not available.
   *
   * @note
   * The platform body axes are defined as +x forward, +y left, and +z up. A
   * positive yaw is a left turn, positive pitch points the nose of the vehicle
   * down, and positive roll is a roll toward the right. Yaw is measured from
   * east in a counter-clockwise direction. For example, north is +90 degrees
   * (i.e., `heading = 90.0 - ypr_deg[0]`).
   */
  double ypr_deg[3] = {NAN, NAN, NAN};

  /**
   * The attitude standard deviation (in degrees): yaw, pitch, roll.
   */
  float ypr_std_deg[3] = {NAN, NAN, NAN};

  /**
   * The platform velocity (in meters/second), resolved in the body frame. Set
   * to `NAN` if attitude is not available for the body frame transformation.
   */
  double velocity_body_mps[3] = {NAN, NAN, NAN};

  /**
   * The velocity standard deviation (in meters/second), resolved in the body
   * frame.
   */
  float velocity_std_body_mps[3] = {NAN, NAN, NAN};

  /** The estimated aggregate 3D protection level (in meters). */
  float aggregate_protection_level_m = NAN;
  /** The estimated 2D horizontal protection level (in meters). */
  float horizontal_protection_level_m = NAN;
  /** The estimated vertical protection level (in meters). */
  float vertical_protection_level_m = NAN;
};

/**
 * @brief Platform pose solution: position, velocity, attitude (@ref
 *        MessageType::POSE), version 1.1.
 *
 * Extends @ref PoseMessage_1_0, adding geoid undulation.
 */
typedef PoseMessage_1_0 PoseMessage_1_1;

/** @brief Alias for the latest platform pose message, version 1.x. */
typedef PoseMessage_1_1 PoseMessage_1;

/** @brief Alias for the latest platform pose message. */
typedef PoseMessage_1 PoseMessage;

/**
 * @brief Auxiliary platform pose information (@ref MessageType::POSE_AUX),
 *        version 1.0.
 * @ingroup messages
 */
struct PoseAuxMessage_1_0 {
  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /**
   * The position standard deviation (in meters), resolved in the body frame.
   * Set to `NAN` if attitude is not available for the body frame
   * transformation.
   */
  float position_std_body_m[3] = {NAN, NAN, NAN};

  /**
   * The 3x3 position covariance matrix (in m^2), resolved in the local ENU
   * frame. Values are stored in row-major order.
   */
  double position_cov_enu_m2[9] = {NAN};

  /**
   * The platform body orientation with respect to the local ENU frame,
   * represented as a quaternion with the scalar component last (x, y, z, w).
   */
  double attitude_quaternion[4] = {NAN, NAN, NAN, NAN};

  /**
   * The platform velocity (in meters/second), resolved in the local ENU frame.
   */
  double velocity_enu_mps[3] = {NAN, NAN, NAN};

  /**
   * The velocity standard deviation (in meters/second), resolved in the local
   * ENU frame.
   */
  float velocity_std_enu_mps[3] = {NAN, NAN, NAN};
};

/** @brief Alias for the latest auxiliary pose message, version 1.x. */
typedef PoseAuxMessage_1_0 PoseAuxMessage_1;

/** @brief Alias for the latest auxiliary pose message. */
typedef PoseAuxMessage_1 PoseAuxMessage;

/**
 * @brief Information about the GNSS data used in the @ref PoseMessage with the
 *        corresponding timestamp (@ref MessageType::GNSS_INFO).
 * @ingroup messages
 */
struct GNSSInfoMessage_1_0 {
  static constexpr uint32_t INVALID_REFERENCE_STATION = 0xFFFFFFFF;

  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /** The GPS time of the message, if available, referenced to 1980/1/6. */
  Timestamp gps_time;

  /** The P1 time of the last differential GNSS update. */
  Timestamp last_differential_time;

  /** The ID of the differential base station, if used. */
  uint32_t reference_station_id = INVALID_REFERENCE_STATION;

  /** The geometric dilution of precision (GDOP). */
  float gdop = NAN;
  /** The position dilution of precision (PDOP). */
  float pdop = NAN;
  /** The horizontal dilution of precision (HDOP). */
  float hdop = NAN;
  /** The vertical dilution of precision (VDOP). */
  float vdop = NAN;

  /** GPS time alignment standard deviation (in seconds). */
  float gps_time_std_sec = NAN;
};

/** @brief Alias for the latest GNSS info message, version 1.x. */
typedef GNSSInfoMessage_1_0 GNSSInfoMessage_1;

/** @brief Alias for the latest GNSS info message. */
typedef GNSSInfoMessage_1 GNSSInfoMessage;

/**
 * @brief Information about the individual satellites used in the @ref
 *        PoseMessage and @ref GNSSInfoMessage with the corresponding timestamp
 *        (@ref MessageType::GNSS_SATELLITE), version 1.0.
 * @ingroup messages
 *
 * This message is followed by `N` @ref SatelliteInfo_1_0 objects, where `N` is
 * equal to @ref num_satellites. For example, a message with two satellites
 * would be serialized as:
 *
 * ```
 * {MessageHeader, GNSSSatelliteMessage, SatelliteInfo, SatelliteInfo, ...}
 * ```
 */
struct GNSSSatelliteMessage_1_0 {
  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /** The GPS time of the message, if available, referenced to 1980/1/6. */
  Timestamp gps_time;

  /** The number of known satellites. */
  uint16_t num_satellites = 0;

  uint8_t reserved[2] = {0};
};

/** @brief Alias for the latest GNSS satellite message, version 1.x. */
typedef GNSSSatelliteMessage_1_0 GNSSSatelliteMessage_1;

/** @brief Alias for the latest GNSS satellite message. */
typedef GNSSSatelliteMessage_1 GNSSSatelliteMessage;

/**
 * @brief Information about an individual satellite (see @ref
 *        GNSSSatelliteMessage).
 *
 * For satellites where @ref usage is 0, the satellite may either be currently
 * tracked by the receiver but not used for navigation, or may just be expected
 * according to available ephemeris data.
 */
struct SatelliteInfo_1_0 {
  /**
   * @defgroup satellite_usage Bit definitions for the satellite usage bitmask
   *           (@ref SatelliteInfo::usage).
   * @{
   */
  static constexpr uint8_t SATELLITE_USED = 0x01;
  /** @} */

  /** The GNSS system to which this satellite belongs. */
  SatelliteType system = SatelliteType::UNKNOWN;

  /** The satellite's PRN (or slot number for GLONASS). */
  uint8_t prn = 0;

  /**
   * A bitmask specifying how this satellite was used in the position solution.
   * Set to 0 if the satellite was not used. See @ref satellite_usage.
   */
  uint8_t usage = 0;

  uint8_t reserved = 0;

  /** The azimuth of the satellite (in degrees). */
  float azimuth_deg = NAN;

  /** The elevation of the satellite (in degrees). */
  float elevation_deg = NAN;
};

/** @brief Alias for the latest satellite info entry, version 1.x. */
typedef SatelliteInfo_1_0 SatelliteInfo_1;

/** @brief Alias for the latest satellite info entry. */
typedef SatelliteInfo_1 SatelliteInfo;

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
